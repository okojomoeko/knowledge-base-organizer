"""
Ask Command Implementation (RAG)

This module implements the `ask` CLI command for question-answering using
Retrieval-Augmented Generation (RAG) with the vault's vector index.

Supports:
- Requirement 18.1, 18.2, 21.1: RAG-based question answering
- Vector similarity search for relevant context
- LLM-powered answer generation with source attribution
"""

import json
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from knowledge_base_organizer.domain.services.ai_services import (
    AIServiceError,
    EmbeddingService,
    LLMService,
    VectorStore,
)
from knowledge_base_organizer.infrastructure.config import ProcessingConfig
from knowledge_base_organizer.infrastructure.di_container import (
    AIServiceConfig,
    create_di_container,
)

logger = logging.getLogger(__name__)
console = Console()


def ask_command(
    question: str = typer.Argument(
        ..., help="Question to ask about your vault content"
    ),
    vault_path: Path = typer.Option(
        Path.cwd(), "--vault", "-v", help="Path to Obsidian vault"
    ),
    max_context_docs: int = typer.Option(
        5, "--max-docs", help="Maximum number of documents to use as context"
    ),
    similarity_threshold: float = typer.Option(
        0.3, "--threshold", help="Minimum similarity threshold for relevant documents"
    ),
    output_format: str = typer.Option("console", help="Output format (json, console)"),
    output_file: Path | None = typer.Option(
        None, "--output", "-o", help="Output file for results"
    ),
    show_sources: bool = typer.Option(
        True, "--sources/--no-sources", help="Show source documents used for context"
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output"),
) -> None:
    """
    Ask questions about your vault content using RAG.

    This command uses Retrieval-Augmented Generation to answer questions about
    your vault content. It searches for relevant documents using vector similarity,
    then uses an LLM to generate answers based on the retrieved context.

    The command requires a vector index created with the 'index' command.

    Examples:
        # Ask a question about your vault
        ask "What are the main concepts in machine learning?"

        # Ask with custom vault path
        ask "How does authentication work?" --vault /path/to/vault

        # Get more context documents
        ask "Explain the architecture" --max-docs 10

        # Lower threshold for broader context
        ask "What is mentioned about APIs?" --threshold 0.2
    """
    if verbose:
        console.print(f"[bold blue]Asking question:[/bold blue] {question}")
        console.print(f"[dim]Vault: {vault_path}[/dim]")

    # Validate vault path
    if not vault_path.exists():
        console.print(f"[red]✗[/red] Vault path does not exist: {vault_path}")
        raise typer.Exit(1)

    # Check for vector index
    index_path = vault_path / ".kbo_index" / "vault.index"
    if not index_path.with_suffix(".faiss").exists():
        console.print(f"[red]✗[/red] No vector index found at {index_path}")
        console.print("Run the 'index' command first to create a vector index")
        raise typer.Exit(1)

    try:
        # Initialize AI services
        config = ProcessingConfig.get_default_config()
        ai_config = AIServiceConfig.get_default_config()
        di_container = create_di_container(vault_path, config, ai_config)

        embedding_service = di_container.get_embedding_service()
        vector_store = di_container.get_vector_store()
        llm_service = di_container.get_llm_service()

        # Load the vector index
        if verbose:
            console.print("[dim]Loading vector index...[/dim]")
        vector_store.load_index(index_path)

        # Execute RAG query
        result = _execute_rag_query(
            question=question,
            embedding_service=embedding_service,
            vector_store=vector_store,
            llm_service=llm_service,
            max_context_docs=max_context_docs,
            similarity_threshold=similarity_threshold,
            verbose=verbose,
        )

        # Output results
        _output_ask_results(result, output_format, output_file, show_sources, verbose)

        if verbose:
            console.print("[green]✓[/green] Question answered successfully")

    except AIServiceError as e:
        console.print(f"[red]✗[/red] AI service error: {e}")
        console.print(
            "[dim]Make sure Ollama is running and the required models are "
            "available[/dim]"
        )
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to answer question: {e}")
        if verbose:
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1) from e


def _execute_rag_query(
    question: str,
    embedding_service: EmbeddingService,
    vector_store: VectorStore,
    llm_service: LLMService,
    max_context_docs: int,
    similarity_threshold: float,
    verbose: bool,
) -> dict[str, Any]:
    """
    Execute a RAG query to answer a question.

    Args:
        question: The question to answer
        embedding_service: Service for generating embeddings
        vector_store: Service for searching vectors
        llm_service: Service for generating answers
        max_context_docs: Maximum number of context documents
        similarity_threshold: Minimum similarity threshold
        verbose: Whether to show verbose output

    Returns:
        Dictionary with query results
    """
    if verbose:
        console.print("[dim]Generating question embedding...[/dim]")

    # Generate embedding for the question
    question_embedding = embedding_service.create_embedding(question)

    if verbose:
        console.print("[dim]Searching for relevant documents...[/dim]")

    # Search for relevant documents
    search_results = vector_store.search(
        query_vector=question_embedding.vector,
        k=max_context_docs,
        threshold=similarity_threshold,
    )

    if not search_results:
        return {
            "question": question,
            "answer": (
                "I couldn't find any relevant documents in your vault to "
                "answer this question."
            ),
            "context_documents": [],
            "search_results": [],
            "timestamp": datetime.now().isoformat(),
            "error": "No relevant documents found",
        }

    if verbose:
        console.print(f"[dim]Found {len(search_results)} relevant documents[/dim]")

    # Prepare context from search results
    context_documents = []
    context_text_parts = []

    for i, result in enumerate(search_results, 1):
        doc_info = {
            "rank": i,
            "document_id": result.document_id,
            "similarity_score": result.similarity_score,
            "metadata": result.metadata,
        }
        context_documents.append(doc_info)

        # Build context text
        title = result.metadata.get("title", "Untitled")
        file_path = result.metadata.get("file_path", "Unknown")

        context_part = f"Document {i} (Similarity: {result.similarity_score:.3f}):\n"
        context_part += f"Title: {title}\n"
        context_part += f"File: {file_path}\n"

        # Add tags if available
        tags = result.metadata.get("tags", [])
        if tags:
            context_part += f"Tags: {', '.join(tags)}\n"

        context_part += "---\n"
        context_text_parts.append(context_part)

    # Combine context
    context_text = "\n".join(context_text_parts)

    if verbose:
        console.print("[dim]Generating answer with LLM...[/dim]")

    # Generate answer using LLM
    answer = _generate_rag_answer(
        question=question,
        context=context_text,
        llm_service=llm_service,
    )

    return {
        "question": question,
        "answer": answer,
        "context_documents": context_documents,
        "search_results": [
            {
                "document_id": r.document_id,
                "similarity_score": r.similarity_score,
                "metadata": r.metadata,
            }
            for r in search_results
        ],
        "timestamp": datetime.now().isoformat(),
        "query_params": {
            "max_context_docs": max_context_docs,
            "similarity_threshold": similarity_threshold,
        },
    }


def _generate_rag_answer(
    question: str,
    context: str,
    llm_service: LLMService,
) -> str:
    """
    Generate an answer using the LLM with retrieved context.

    Args:
        question: The question to answer
        context: Retrieved context documents
        llm_service: LLM service for generation

    Returns:
        Generated answer
    """
    system_prompt = (
        "You are a helpful assistant that answers questions based on the provided "
        "context from a knowledge base. Use only the information provided in the "
        "context to answer questions. If the context doesn't contain enough "
        "information to answer the question, say so clearly. "
        "Be concise but comprehensive in your answers. "
        "When referencing information, mention which document it comes from."
    )

    user_prompt = (
        f"Context from knowledge base:\n\n{context}\n\n"
        f"Question: {question}\n\n"
        f"Answer based on the provided context:"
    )

    try:
        # Use the LLM's generate completion method
        # This is a simplified approach - in a full implementation,
        # you might want to use a more sophisticated prompt template
        answer = llm_service.summarize_content(
            f"{system_prompt}\n\n{user_prompt}", max_length=1000
        )

        if not answer.strip():
            return "I couldn't generate an answer based on the provided context."

        return answer

    except Exception as e:
        logger.error(f"Error generating RAG answer: {e}")
        return f"Error generating answer: {e}"


def _output_ask_results(
    result: dict[str, Any],
    output_format: str,
    output_file: Path | None,
    show_sources: bool,
    verbose: bool,
) -> None:
    """Output ask command results in the specified format."""

    if output_format.lower() == "json":
        json_data = result

        if output_file:
            with output_file.open("w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            console.print(f"[green]✓[/green] JSON results saved to: {output_file}")
        else:
            console.print(json.dumps(json_data, indent=2, ensure_ascii=False))

    else:
        # Console format (default)
        _display_ask_console(result, show_sources, verbose)


def _display_ask_console(
    result: dict[str, Any], show_sources: bool, verbose: bool
) -> None:
    """Display ask results in console format."""

    # Display the question
    console.print(f"\n[bold blue]❓ Question:[/bold blue] {result['question']}")

    # Check for errors
    if result.get("error"):
        console.print(f"\n[red]❌ {result['error']}[/red]")
        return

    # Display the answer in a nice panel
    answer_panel = Panel(
        Markdown(result["answer"]),
        title="🤖 Answer",
        title_align="left",
        border_style="green",
        padding=(1, 2),
    )
    console.print(answer_panel)

    # Display source information if requested
    if show_sources and result.get("context_documents"):
        console.print("\n[bold cyan]📚 Sources Used:[/bold cyan]")

        for doc in result["context_documents"]:
            title = doc["metadata"].get("title", "Untitled")
            file_path = doc["metadata"].get("file_path", "Unknown")
            similarity = doc["similarity_score"]

            console.print(f"  {doc['rank']}. [blue]{title}[/blue]")
            console.print(f"     File: [dim]{file_path}[/dim]")
            console.print(f"     Similarity: [green]{similarity:.3f}[/green]")

            if verbose:
                tags = doc["metadata"].get("tags", [])
                if tags:
                    console.print(f"     Tags: [yellow]{', '.join(tags)}[/yellow]")

            console.print()

    # Display query info if verbose
    if verbose:
        console.print("[dim]Query completed at: " + result["timestamp"] + "[/dim]")
        params = result.get("query_params", {})
        console.print(
            f"[dim]Max docs: {params.get('max_context_docs', 'N/A')}, "
            f"Threshold: {params.get('similarity_threshold', 'N/A')}[/dim]"
        )

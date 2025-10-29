"""
Index Command Implementation

This module implements the `index` CLI command for creating vector embeddings
of vault content and storing them in a searchable index.

Supports:
- Requirement 13.1, 18.1: Vector-based semantic search infrastructure
- Full vault scanning and embedding generation
- Persistent index storage for efficient retrieval
"""

import json
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from knowledge_base_organizer.domain.services.ai_services import (
    AIServiceError,
    EmbeddingService,
    VectorStore,
)
from knowledge_base_organizer.infrastructure.config import ProcessingConfig
from knowledge_base_organizer.infrastructure.di_container import (
    AIServiceConfig,
    create_di_container,
)
from knowledge_base_organizer.infrastructure.file_repository import FileRepository

logger = logging.getLogger(__name__)
console = Console()


def index_command(
    vault_path: Path = typer.Argument(..., help="Path to Obsidian vault"),
    force_rebuild: bool = typer.Option(
        False, "--force", help="Force rebuild of existing index"
    ),
    batch_size: int = typer.Option(
        10, "--batch-size", help="Number of files to process in each batch"
    ),
    include_patterns: list[str] | None = typer.Option(
        None, "--include", help="Include file patterns"
    ),
    exclude_patterns: list[str] | None = typer.Option(
        None, "--exclude", help="Exclude file patterns"
    ),
    output_format: str = typer.Option("console", help="Output format (json, console)"),
    output_file: Path | None = typer.Option(
        None, "--output", "-o", help="Output file for indexing results"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """
    Create vector embeddings index for semantic search.

    This command scans all markdown files in the vault, generates vector embeddings
    for their content using the configured embedding service, and stores them in
    a searchable vector index for semantic similarity operations.

    The index is saved to .kbo_index/vault.index in the vault directory and can
    be used by other commands for semantic search and content discovery.

    Examples:
        # Create index for entire vault
        index /path/to/vault

        # Force rebuild existing index
        index /path/to/vault --force

        # Index with custom patterns
        index /path/to/vault --include "*.md" --exclude "templates/*"
    """
    if verbose:
        console.print(f"[bold blue]Creating vector index for:[/bold blue] {vault_path}")

    # Validate vault path
    if not vault_path.exists():
        console.print(f"[red]✗[/red] Vault path does not exist: {vault_path}")
        raise typer.Exit(1)

    # Check for existing index
    index_path = vault_path / ".kbo_index" / "vault.index"
    if index_path.with_suffix(".faiss").exists() and not force_rebuild:
        console.print(f"[yellow]⚠[/yellow] Index already exists at {index_path}")
        console.print("Use --force to rebuild the existing index")
        if not typer.confirm("Continue with existing index?"):
            raise typer.Exit(0)

    try:
        # Initialize services
        config = _setup_indexing_config(include_patterns, exclude_patterns)
        ai_config = AIServiceConfig.get_default_config()
        di_container = create_di_container(vault_path, config, ai_config)

        embedding_service = di_container.get_embedding_service()
        vector_store = di_container.get_vector_store()
        file_repository = FileRepository(config)

        # Execute indexing
        result = _execute_indexing(
            vault_path=vault_path,
            embedding_service=embedding_service,
            vector_store=vector_store,
            file_repository=file_repository,
            batch_size=batch_size,
            force_rebuild=force_rebuild,
            verbose=verbose,
        )

        # Output results
        _output_indexing_results(result, output_format, output_file, verbose)

        if verbose:
            console.print("[green]✓[/green] Vector indexing completed successfully")

    except AIServiceError as e:
        console.print(f"[red]✗[/red] AI service error: {e}")
        console.print(
            "[dim]Make sure Ollama is running and the required models are "
            "available[/dim]"
        )
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]✗[/red] Indexing failed: {e}")
        if verbose:
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1) from e


def _setup_indexing_config(
    include_patterns: list[str] | None,
    exclude_patterns: list[str] | None,
) -> ProcessingConfig:
    """Set up configuration for indexing."""
    config = ProcessingConfig.get_default_config()
    if include_patterns:
        config.include_patterns = include_patterns
    if exclude_patterns:
        config.exclude_patterns.extend(exclude_patterns)
    return config


def _execute_indexing(
    vault_path: Path,
    embedding_service: EmbeddingService,
    vector_store: VectorStore,
    file_repository: FileRepository,
    batch_size: int,
    force_rebuild: bool,
    verbose: bool,
) -> dict[str, Any]:
    """
    Execute the indexing process.

    Args:
        vault_path: Path to the vault
        embedding_service: Service for generating embeddings
        vector_store: Service for storing vectors
        file_repository: Repository for loading files
        batch_size: Number of files to process per batch
        force_rebuild: Whether to force rebuild existing index
        verbose: Whether to show verbose output

    Returns:
        Dictionary with indexing results
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        # Load files
        load_task = progress.add_task("Loading vault files...", total=None)
        files = file_repository.load_vault(vault_path)
        file_count = len(files)
        progress.update(
            load_task, description=f"Loaded {file_count} files", completed=True
        )

        if file_count == 0:
            console.print("[yellow]⚠[/yellow] No markdown files found in vault")
            return {
                "vault_path": str(vault_path),
                "total_files": 0,
                "indexed_files": 0,
                "skipped_files": 0,
                "errors": [],
                "index_stats": {},
            }

        # Initialize or load existing index
        index_path = vault_path / ".kbo_index" / "vault.index"
        if force_rebuild or not index_path.with_suffix(".faiss").exists():
            progress.add_task("Initializing new index...", total=None, completed=True)
        else:
            load_index_task = progress.add_task("Loading existing index...", total=None)
            try:
                vector_store.load_index(index_path)
                progress.update(
                    load_index_task, description="Index loaded", completed=True
                )
            except Exception as e:
                progress.update(
                    load_index_task,
                    description=f"Failed to load index: {e}",
                    completed=True,
                )
                if verbose:
                    console.print(
                        f"[yellow]⚠[/yellow] Could not load existing index: {e}"
                    )
                    console.print("[dim]Creating new index...[/dim]")

        # Process files in batches
        embed_task = progress.add_task("Generating embeddings...", total=file_count)

        indexed_files = 0
        skipped_files = 0
        errors = []

        for i in range(0, file_count, batch_size):
            batch_files = files[i : i + batch_size]
            batch_results = _process_file_batch(
                batch_files, embedding_service, vector_store, verbose
            )

            indexed_files += batch_results["indexed"]
            skipped_files += batch_results["skipped"]
            errors.extend(batch_results["errors"])

            progress.update(embed_task, advance=len(batch_files))

            if verbose and batch_results["errors"]:
                for error in batch_results["errors"]:
                    console.print(f"[yellow]⚠[/yellow] {error}")

        # Save index
        save_task = progress.add_task("Saving index to disk...", total=None)
        try:
            # Ensure index directory exists
            index_path.parent.mkdir(parents=True, exist_ok=True)
            vector_store.save_index(index_path)
            progress.update(
                save_task, description="Index saved successfully", completed=True
            )
        except Exception as e:
            progress.update(
                save_task, description=f"Failed to save index: {e}", completed=True
            )
            raise

        # Get final index statistics
        index_stats = vector_store.get_index_stats()

    return {
        "vault_path": str(vault_path),
        "index_path": str(index_path),
        "total_files": file_count,
        "indexed_files": indexed_files,
        "skipped_files": skipped_files,
        "errors": errors,
        "index_stats": index_stats,
        "timestamp": datetime.now().isoformat(),
    }


def _process_file_batch(
    files: list,
    embedding_service: EmbeddingService,
    vector_store: VectorStore,
    verbose: bool,
) -> dict[str, Any]:
    """
    Process a batch of files for indexing.

    Args:
        files: List of MarkdownFile objects to process
        embedding_service: Service for generating embeddings
        vector_store: Service for storing vectors
        verbose: Whether to show verbose output

    Returns:
        Dictionary with batch processing results
    """
    indexed = 0
    skipped = 0
    errors = []

    for file in files:
        try:
            # Skip files without content
            if not file.content.strip():
                skipped += 1
                if verbose:
                    logger.debug(f"Skipping empty file: {file.path}")
                continue

            # Prepare content for embedding (combine title and content)
            content_for_embedding = _prepare_content_for_embedding(file)

            # Generate embedding
            embedding_result = embedding_service.create_embedding(content_for_embedding)

            # Prepare metadata
            metadata = {
                "file_path": str(file.path),
                "title": file.frontmatter.get("title", file.path.stem),
                "tags": file.frontmatter.get("tags", []),
                "content_length": len(file.content),
                "has_frontmatter": bool(file.frontmatter),
            }

            # Index the document
            document_id = file.file_id or str(file.path)
            vector_store.index_document(
                document_id=document_id,
                vector=embedding_result.vector,
                metadata=metadata,
            )

            indexed += 1

        except Exception as e:
            error_msg = f"Error processing {file.path}: {e}"
            errors.append(error_msg)
            logger.error(error_msg)

    return {
        "indexed": indexed,
        "skipped": skipped,
        "errors": errors,
    }


def _prepare_content_for_embedding(file) -> str:
    """
    Prepare file content for embedding generation.

    Combines title, tags, and content in a way that maximizes
    semantic search effectiveness.

    Args:
        file: MarkdownFile object

    Returns:
        Prepared content string for embedding
    """
    parts = []

    # Add title if available
    title = file.frontmatter.get("title")
    if title:
        parts.append(f"Title: {title}")

    # Add tags if available
    tags = file.frontmatter.get("tags", [])
    if tags:
        parts.append(f"Tags: {', '.join(tags)}")

    # Add main content (limit to first 3000 characters for efficiency)
    content = file.content.strip()
    if content:
        # Remove frontmatter from content if present
        if content.startswith("---"):
            lines = content.split("\n")
            frontmatter_end = -1
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == "---":
                    frontmatter_end = i
                    break
            if frontmatter_end > 0:
                content = "\n".join(lines[frontmatter_end + 1 :]).strip()

        # Limit content length
        if len(content) > 3000:
            content = content[:3000] + "..."

        parts.append(content)

    return "\n\n".join(parts)


def _output_indexing_results(
    result: dict[str, Any],
    output_format: str,
    output_file: Path | None,
    verbose: bool,
) -> None:
    """Output indexing results in the specified format."""

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
        _display_indexing_console(result, verbose)


def _display_indexing_console(result: dict[str, Any], verbose: bool) -> None:
    """Display indexing results in console format."""
    console.print("\n[bold blue]📊 Vector Indexing Results[/bold blue]")
    console.print(f"[dim]Vault: {result['vault_path']}[/dim]")
    console.print(f"[dim]Index: {result.get('index_path', 'N/A')}[/dim]")
    console.print(f"[dim]Completed: {result['timestamp']}[/dim]\n")

    # Summary statistics
    console.print("[bold green]📈 Summary[/bold green]")
    console.print(f"  Total files: {result['total_files']}")
    console.print(f"  Successfully indexed: [green]{result['indexed_files']}[/green]")
    console.print(f"  Skipped files: [yellow]{result['skipped_files']}[/yellow]")
    console.print(f"  Errors: [red]{len(result['errors'])}[/red]")

    # Index statistics
    if result.get("index_stats"):
        stats = result["index_stats"]
        console.print("\n[bold cyan]🗂️ Index Statistics[/bold cyan]")
        console.print(f"  Documents in index: {stats.get('total_documents', 0)}")
        console.print(f"  Vector dimension: {stats.get('dimension', 'N/A')}")
        console.print(f"  Index type: {stats.get('index_type', 'N/A')}")

        memory_mb = stats.get("memory_usage_bytes", 0) / (1024 * 1024)
        console.print(f"  Memory usage: {memory_mb:.1f} MB")

    # Show errors if any
    if result["errors"] and (verbose or len(result["errors"]) <= 5):
        console.print("\n[bold red]❌ Errors[/bold red]")
        for error in result["errors"][:10]:  # Show first 10 errors
            console.print(f"  • {error}")

        if len(result["errors"]) > 10:
            console.print(
                f"  [dim]... and {len(result['errors']) - 10} more errors[/dim]"
            )

    elif result["errors"]:
        console.print(f"\n[yellow]⚠[/yellow] {len(result['errors'])} errors occurred")
        console.print("[dim]Use --verbose to see error details[/dim]")

    # Success rate
    if result["total_files"] > 0:
        success_rate = (result["indexed_files"] / result["total_files"]) * 100
        console.print(
            f"\n[bold magenta]✨ Success Rate: {success_rate:.1f}%[/bold magenta]"
        )

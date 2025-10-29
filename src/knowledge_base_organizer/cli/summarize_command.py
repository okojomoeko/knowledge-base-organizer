"""CLI command for content summarization using LLM."""

from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..infrastructure.config import ProcessingConfig
from ..infrastructure.file_repository import FileRepository
from ..infrastructure.ollama_llm import OllamaLLMService

console = Console()


def summarize_command(
    file_path: Path,
    max_length: int = 200,
    output_file: Path | None = None,
    verbose: bool = False,
) -> None:
    """Generate a concise summary of the specified file using AI.

    This command uses an LLM to analyze the content of a markdown file
    and generate a concise summary that captures the main points and
    key information.

    Args:
        file_path: Path to the markdown file to summarize
        max_length: Maximum length of summary in characters (default: 200)
        output_file: Optional output file to save the summary
        verbose: Enable verbose output
    """
    try:
        console.print(f"📝 Summarizing file: {file_path}")

        # Validate file path
        if not file_path.exists():
            console.print(f"❌ File does not exist: {file_path}")
            raise typer.Exit(1)

        if file_path.suffix.lower() != ".md":
            console.print(f"❌ File must be a markdown file (.md): {file_path}")
            raise typer.Exit(1)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Initializing AI service...", total=None)

            # Initialize LLM service
            try:
                llm_service = OllamaLLMService()
                progress.update(task, description="AI service initialized")
            except Exception as e:
                progress.update(task, description="Failed to initialize AI service")
                console.print(f"❌ Failed to initialize AI service: {e}")
                if verbose:
                    console.print(f"[dim]Error details: {e}[/dim]")
                raise typer.Exit(1) from e

            # Load file
            progress.update(task, description="Loading file...")
            try:
                config = ProcessingConfig.get_default_config()
                file_repo = FileRepository(config)

                # Load the specific file
                markdown_file = file_repo.load_file(file_path)
                progress.update(task, description="File loaded")

                if verbose:
                    content_length = len(markdown_file.content)
                    console.print(
                        f"[dim]File content length: {content_length} characters[/dim]"
                    )

            except Exception as e:
                progress.update(task, description="Failed to load file")
                console.print(f"❌ Failed to load file: {e}")
                if verbose:
                    console.print(f"[dim]Error details: {e}[/dim]")
                raise typer.Exit(1) from e

            # Generate summary
            progress.update(task, description="Generating summary...")
            try:
                summary = llm_service.summarize_content(
                    markdown_file.content, max_length=max_length
                )
                progress.update(task, description="Summary generated!")

                if not summary:
                    console.print("⚠️ No summary could be generated for this content")
                    return

            except Exception as e:
                progress.update(task, description="Failed to generate summary")
                console.print(f"❌ Failed to generate summary: {e}")
                if verbose:
                    console.print(f"[dim]Error details: {e}[/dim]")
                raise typer.Exit(1) from e

        # Display results
        _display_summary_results(
            file_path=file_path,
            summary=summary,
            max_length=max_length,
            output_file=output_file,
            verbose=verbose,
        )

    except Exception as e:
        console.print(f"❌ Error during summarization: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1) from e


def _display_summary_results(
    file_path: Path,
    summary: str,
    max_length: int,
    output_file: Path | None,
    verbose: bool,
) -> None:
    """Display summarization results."""
    console.print("\n📋 Summary Results")
    console.print(f"[dim]File: {file_path}[/dim]")
    console.print(
        f"[dim]Summary length: {len(summary)} characters (max: {max_length})[/dim]"
    )

    # Display the summary
    console.print("\n[bold blue]📝 Generated Summary[/bold blue]")
    console.print(f"[green]{summary}[/green]")

    # Save to file if requested
    if output_file:
        try:
            with output_file.open("w", encoding="utf-8") as f:
                f.write(f"# Summary of {file_path.name}\n\n")
                f.write(f"**Source:** {file_path}\n")
                f.write("**Generated:** knowledge-base-organizer summarize command\n")
                f.write(f"**Max Length:** {max_length} characters\n\n")
                f.write(f"## Summary\n\n{summary}\n")

            console.print(f"\n💾 Summary saved to: {output_file}")

        except Exception as e:
            console.print(f"⚠️ Failed to save summary to file: {e}")
            if verbose:
                console.print(f"[dim]Error details: {e}[/dim]")

    if verbose:
        console.print("\n[dim]Summary generation completed successfully[/dim]")

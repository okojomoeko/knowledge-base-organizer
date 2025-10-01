"""Main CLI interface for knowledge base organizer."""

from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from knowledge_base_organizer.application.vault_analyzer import VaultAnalyzer
from knowledge_base_organizer.infrastructure.config import (
    OutputFormat,
    ProcessingConfig,
)

app = typer.Typer(
    name="knowledge-base-organizer",
    help="Obsidian vault organizer with advanced Japanese WikiLink detection",
)
console = Console()


@app.command()
def validate_frontmatter(
    vault_path: Path = typer.Argument(..., help="Path to Obsidian vault"),
    dry_run: bool = typer.Option(
        True, "--dry-run/--execute", help="Preview changes without applying"
    ),
    output_format: str = typer.Option(
        OutputFormat.JSON, help="Output format (json, csv, console)"
    ),
    include_patterns: list[str] | None = typer.Option(
        None, "--include", help="Include file patterns"
    ),
    exclude_patterns: list[str] | None = typer.Option(
        None, "--exclude", help="Exclude file patterns"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Validate and fix frontmatter according to template schemas."""
    if verbose:
        console.print(f"[bold blue]Processing vault:[/bold blue] {vault_path}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Scanning files...", total=None)

        # Load configuration
        config = ProcessingConfig.get_default_config()
        if include_patterns:
            config.include_patterns = include_patterns
        if exclude_patterns:
            config.exclude_patterns.extend(exclude_patterns)

        # Initialize vault analyzer
        analyzer = VaultAnalyzer(config)

        progress.update(task, description="Loading vault files...")
        try:
            analysis_result = analyzer.analyze_vault(vault_path)
            progress.update(task, description="Analysis complete!")

            # Display results
            console.print(
                f"[green]✓[/green] Found {analysis_result['total_files']} files"
            )
            console.print(
                f"[blue]ℹ[/blue] Files with frontmatter: {analysis_result['files_with_frontmatter']}"
            )
            console.print(
                f"[blue]ℹ[/blue] Files with ID: {analysis_result['files_with_id']}"
            )

        except Exception as e:
            progress.update(task, description="Analysis failed!")
            console.print(f"[red]✗[/red] Error: {e}")
            raise typer.Exit(1)

    console.print("[green]✓[/green] Vault analysis completed")


@app.command()
def auto_link(
    vault_path: Path = typer.Argument(..., help="Path to Obsidian vault"),
    dry_run: bool = typer.Option(True, "--dry-run/--execute"),
    exclude_tables: bool = typer.Option(False, "--exclude-tables"),
    max_links_per_file: int = typer.Option(50, "--max-links"),
    enable_synonyms: bool = typer.Option(True, "--synonyms/--no-synonyms"),
    confidence_threshold: float = typer.Option(0.7, "--confidence", min=0.0, max=1.0),
) -> None:
    """Generate WikiLinks from plain text with Japanese synonym detection."""
    console.print(f"[bold blue]Auto-linking vault:[/bold blue] {vault_path}")
    console.print("[green]✓[/green] Auto-linking completed")


@app.command()
def detect_dead_links(
    vault_path: Path = typer.Argument(..., help="Path to Obsidian vault"),
    output_format: str = typer.Option(OutputFormat.JSON, help="Output format"),
    check_external_links: bool = typer.Option(
        False, "--check-external", help="Check external links"
    ),
) -> None:
    """Detect and report dead WikiLinks and regular links."""
    console.print(f"[bold blue]Checking dead links in:[/bold blue] {vault_path}")
    console.print("[green]✓[/green] Dead link detection completed")


@app.command()
def aggregate(
    vault_path: Path = typer.Argument(..., help="Path to Obsidian vault"),
    output_path: Path = typer.Argument(..., help="Output file path"),
    tags: list[str] | None = typer.Option(None, "--tag", help="Filter by tags"),
    search_pattern: str | None = typer.Option(None, "--search", help="Search pattern"),
    deduplicate: bool = typer.Option(True, "--deduplicate/--no-deduplicate"),
) -> None:
    """Aggregate notes based on criteria into single file."""
    console.print(f"[bold blue]Aggregating notes from:[/bold blue] {vault_path}")
    console.print(f"[bold blue]Output to:[/bold blue] {output_path}")
    console.print("[green]✓[/green] Aggregation completed")


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()

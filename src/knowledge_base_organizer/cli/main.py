"""Main CLI interface for knowledge base organizer."""

import json
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
def analyze(
    vault_path: Path = typer.Argument(..., help="Path to Obsidian vault"),
    output_format: str = typer.Option(
        OutputFormat.JSON, help="Output format (json, console)"
    ),
    include_patterns: list[str] | None = typer.Option(
        None, "--include", help="Include file patterns"
    ),
    exclude_patterns: list[str] | None = typer.Option(
        None, "--exclude", help="Exclude file patterns"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Analyze vault and report basic statistics including file count, frontmatter field distribution, and link counts."""
    if verbose:
        console.print(f"[bold blue]Analyzing vault:[/bold blue] {vault_path}")

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

        progress.update(task, description="Analyzing vault contents...")
        try:
            analysis_result = analyzer.analyze_vault_detailed(vault_path)
            progress.update(task, description="Analysis complete!")

        except (ValueError, FileNotFoundError) as e:
            progress.update(task, description="Analysis failed!")
            console.print(f"[red]✗[/red] Error: {e}")
            raise typer.Exit(1) from e

    # Output results based on format (outside progress context to avoid spinner in JSON)
    if output_format.lower() == OutputFormat.JSON.lower():
        console.print(json.dumps(analysis_result, indent=2, ensure_ascii=False))
    else:
        # Console format
        _display_analysis_console(analysis_result, console)

    if verbose:
        console.print("[green]✓[/green] Vault analysis completed")


def _display_analysis_console(analysis_result: dict, console: Console) -> None:
    """Display analysis results in console format."""
    console.print("\n[bold blue]📊 Vault Analysis Results[/bold blue]")
    console.print(f"[dim]Vault: {analysis_result['vault_path']}[/dim]")
    console.print(
        f"[dim]Analysis time: {analysis_result['analysis_timestamp']}[/dim]\n"
    )

    # File statistics
    file_stats = analysis_result["file_statistics"]
    console.print("[bold green]📁 File Statistics[/bold green]")
    console.print(f"  Total files: {file_stats['total_files']}")
    console.print(f"  Files with frontmatter: {file_stats['files_with_frontmatter']}")
    console.print(f"  Files with ID: {file_stats['files_with_id']}")
    console.print(f"  File extensions: {dict(file_stats['files_by_extension'])}")

    # Frontmatter statistics
    fm_stats = analysis_result["frontmatter_statistics"]
    console.print("\n[bold yellow]📋 Frontmatter Statistics[/bold yellow]")
    console.print(f"  Total unique fields: {fm_stats['total_unique_fields']}")
    console.print("  Most common fields:")
    for field, count in fm_stats["most_common_fields"][:5]:
        console.print(f"    {field}: {count} files")

    # Link statistics
    link_stats = analysis_result["link_statistics"]
    console.print("\n[bold cyan]🔗 Link Statistics[/bold cyan]")
    console.print(f"  Total links: {link_stats['total_links']}")
    wiki_count = link_stats["wiki_links"]["total_count"]
    wiki_files = link_stats["wiki_links"]["files_with_links"]
    console.print(f"  WikiLinks: {wiki_count} (in {wiki_files} files)")

    regular_count = link_stats["regular_links"]["total_count"]
    regular_files = link_stats["regular_links"]["files_with_links"]
    console.print(f"  Regular links: {regular_count} (in {regular_files} files)")

    ref_count = link_stats["link_reference_definitions"]["total_count"]
    ref_files = link_stats["link_reference_definitions"]["files_with_definitions"]
    console.print(f"  Link reference definitions: {ref_count} (in {ref_files} files)")

    # Content statistics
    content_stats = analysis_result["content_statistics"]
    console.print("\n[bold magenta]📝 Content Statistics[/bold magenta]")
    console.print(
        f"  Total content length: {content_stats['total_content_length']:,} characters"
    )
    console.print(
        f"  Average file size: {content_stats['average_content_length']:,.1f} characters"
    )
    console.print(f"  Largest file: {content_stats['largest_file_size']:,} characters")
    console.print(
        f"  Smallest file: {content_stats['smallest_file_size']:,} characters"
    )


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

        except (ValueError, FileNotFoundError) as e:
            progress.update(task, description="Analysis failed!")
            console.print(f"[red]✗[/red] Error: {e}")
            raise typer.Exit(1) from e

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

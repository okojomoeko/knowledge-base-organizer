"""Main CLI interface for knowledge base organizer."""

import csv
import io
import json
import traceback
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from knowledge_base_organizer.application.frontmatter_validation_use_case import (
    FrontmatterValidationRequest,
    FrontmatterValidationUseCase,
)
from knowledge_base_organizer.application.vault_analyzer import VaultAnalyzer
from knowledge_base_organizer.domain.services.frontmatter_validation_service import (
    FrontmatterValidationService,
)
from knowledge_base_organizer.infrastructure.config import (
    OutputFormat,
    ProcessingConfig,
)
from knowledge_base_organizer.infrastructure.file_repository import FileRepository
from knowledge_base_organizer.infrastructure.template_schema_repository import (
    TemplateSchemaRepository,
)

app = typer.Typer(
    name="knowledge-base-organizer",
    help="Obsidian vault organizer with advanced Japanese WikiLink detection",
)
console = Console()

# Import and add tag management subcommand (conditional to avoid circular imports)
try:
    from .tag_management import app as tag_management_app

    app.add_typer(tag_management_app, name="tags")
except ImportError:
    pass  # Tag management not available


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
    """Analyze vault and report basic statistics.

    Reports file count, frontmatter field distribution, and link counts.
    """
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
        f"  Average file size: "
        f"{content_stats['average_content_length']:,.1f} characters"
    )
    console.print(f"  Largest file: {content_stats['largest_file_size']:,} characters")
    console.print(
        f"  Smallest file: {content_stats['smallest_file_size']:,} characters"
    )


@app.command()
def validate_frontmatter(
    vault_path: Path = typer.Argument(..., help="Path to Obsidian vault"),
    dry_run: bool = typer.Option(
        True, "--dry-run/--execute", help="Preview changes without applying them"
    ),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Interactive mode for reviewing fixes"
    ),
    output_format: str = typer.Option(
        OutputFormat.CONSOLE, help="Output format (json, csv, console)"
    ),
    include_patterns: list[str] | None = typer.Option(
        None, "--include", help="Include file patterns"
    ),
    exclude_patterns: list[str] | None = typer.Option(
        None, "--exclude", help="Exclude file patterns"
    ),
    template_name: str | None = typer.Option(
        None, "--template", help="Validate against specific template only"
    ),
    output_file: Path | None = typer.Option(
        None, "--output", "-o", help="Output file for CSV/JSON results"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Validate and fix frontmatter according to template schemas.

    This command validates frontmatter in markdown files against template schemas
    extracted from template directories. It can run in dry-run mode to preview
    changes, or in execute mode to apply fixes automatically.

    Interactive mode allows reviewing each fix before applying it.
    """

    if verbose:
        console.print(f"[bold blue]Validating frontmatter in:[/bold blue] {vault_path}")
        console.print(f"[dim]Mode: {'dry-run' if dry_run else 'execute'}[/dim]")
        if interactive:
            console.print("[dim]Interactive mode enabled[/dim]")

    # Validate vault path
    if not vault_path.exists():
        console.print(f"[red]✗[/red] Vault path does not exist: {vault_path}")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Loading configuration...", total=None)

        # Load configuration
        config = ProcessingConfig.get_default_config()
        if include_patterns:
            config.include_patterns = include_patterns
        if exclude_patterns:
            config.exclude_patterns.extend(exclude_patterns)

        # Initialize components
        file_repository = FileRepository(config)
        template_schema_repository = TemplateSchemaRepository(vault_path, config)
        validation_service = FrontmatterValidationService()

        use_case = FrontmatterValidationUseCase(
            file_repository=file_repository,
            template_schema_repository=template_schema_repository,
            validation_service=validation_service,
            config=config,
        )

        progress.update(task, description="Extracting template schemas...")

        # Create request
        request = FrontmatterValidationRequest(
            vault_path=vault_path,
            dry_run=dry_run,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            template_name=template_name,
        )

        progress.update(task, description="Validating frontmatter...")

        try:
            result = use_case.execute(request)
            progress.update(task, description="Validation complete!")

        except Exception as e:
            progress.update(task, description="Validation failed!")
            console.print(f"[red]✗[/red] Error during validation: {e}")
            if verbose:
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
            raise typer.Exit(1) from e

    # Handle interactive mode
    if interactive and not dry_run:
        _handle_interactive_fixes(result, console)

    # Output results
    _output_validation_results(result, output_format, output_file, console, verbose)

    # Final summary
    if verbose:
        console.print("[green]✓[/green] Validation completed")
        console.print(f"[dim]Files processed: {result.total_files}[/dim]")
        console.print(f"[dim]Valid files: {result.valid_files}[/dim]")
        console.print(f"[dim]Invalid files: {result.invalid_files}[/dim]")


# NOTE: Additional commands will be implemented in future versions
# @app.command()
# def auto_link(...) -> None:
#     """Generate WikiLinks from plain text with Japanese synonym detection."""
#     pass

# @app.command()
# def detect_dead_links(...) -> None:
#     """Detect and report dead WikiLinks and regular links."""
#     pass

# @app.command()
# def aggregate(...) -> None:
#     """Aggregate notes based on criteria into single file."""
#     pass


def _handle_interactive_fixes(result, console: Console) -> None:
    """Handle interactive mode for reviewing and applying fixes."""

    console.print("\n[bold yellow]🔧 Interactive Fix Mode[/bold yellow]")
    console.print("Review each suggested fix and choose whether to apply it.\n")

    invalid_results = [r for r in result.results if not r.is_valid]

    if not invalid_results:
        console.print("[green]✓[/green] No fixes needed - all files are valid!")
        return

    for validation_result in invalid_results:
        console.print(
            f"\n[bold blue]📄 File:[/bold blue] {validation_result.file_path}"
        )
        console.print(
            f"[dim]Template: {validation_result.template_type or 'None detected'}[/dim]"
        )

        # Show missing fields
        if validation_result.missing_fields:
            console.print("\n[yellow]Missing required fields:[/yellow]")
            for field in validation_result.missing_fields:
                suggested_value = validation_result.suggested_fixes.get(field, "")
                console.print(
                    f"  • {field}: [dim]suggested value: {suggested_value}[/dim]"
                )

        # Show invalid fields
        if validation_result.invalid_fields:
            console.print("\n[red]Invalid fields:[/red]")
            for field, error in validation_result.invalid_fields.items():
                console.print(f"  • {field}: {error}")

        # Show warnings
        if validation_result.warnings:
            console.print("\n[orange3]Warnings:[/orange3]")
            for warning in validation_result.warnings:
                console.print(f"  • {warning}")

        # Ask user if they want to apply fixes
        if validation_result.suggested_fixes:
            apply_fixes = typer.confirm(
                f"\nApply suggested fixes to {validation_result.file_path.name}?"
            )
            if apply_fixes:
                console.print("[green]✓[/green] Fixes would be applied (placeholder)")
                # TODO: Implement actual fix application
            else:
                console.print("[yellow]⚠[/yellow] Skipping fixes for this file")


def _output_validation_results(
    result,
    output_format: str,
    output_file: Path | None,
    console: Console,
    verbose: bool,
) -> None:
    """Output validation results in the specified format."""

    if output_format.lower() == OutputFormat.JSON.lower():
        # Prepare JSON output
        json_data = {
            "validation_timestamp": datetime.now().isoformat(),
            "summary": result.summary,
            "schemas_used": result.schemas_used,
            "total_files": result.total_files,
            "valid_files": result.valid_files,
            "invalid_files": result.invalid_files,
            "files_with_warnings": result.files_with_warnings,
            "results": [
                {
                    "file_path": str(r.file_path),
                    "template_type": r.template_type,
                    "is_valid": r.is_valid,
                    "missing_fields": r.missing_fields,
                    "invalid_fields": r.invalid_fields,
                    "suggested_fixes": r.suggested_fixes,
                    "warnings": r.warnings,
                }
                for r in result.results
            ],
        }

        if output_file:
            with output_file.open("w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            console.print(f"[green]✓[/green] JSON results saved to: {output_file}")
        else:
            console.print(json.dumps(json_data, indent=2, ensure_ascii=False))

    elif output_format.lower() == OutputFormat.CSV.lower():
        # Prepare CSV output
        csv_data = []
        for r in result.results:
            csv_data.append({
                "file_path": str(r.file_path),
                "template_type": r.template_type or "",
                "is_valid": r.is_valid,
                "missing_fields": "; ".join(r.missing_fields),
                "invalid_fields": "; ".join([
                    f"{k}: {v}" for k, v in r.invalid_fields.items()
                ]),
                "warnings": "; ".join(r.warnings),
                "suggested_fixes_count": len(r.suggested_fixes),
            })

        if output_file:
            with output_file.open("w", newline="", encoding="utf-8") as f:
                if csv_data:
                    writer = csv.DictWriter(f, fieldnames=csv_data[0].keys())
                    writer.writeheader()
                    writer.writerows(csv_data)
            console.print(f"[green]✓[/green] CSV results saved to: {output_file}")
        # Output CSV to console
        elif csv_data:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=csv_data[0].keys())
            writer.writeheader()
            writer.writerows(csv_data)
            console.print(output.getvalue())

    else:
        # Console format (default)
        _display_validation_console(result, console, verbose)


def _display_validation_console(result, console: Console, verbose: bool) -> None:
    """Display validation results in console format."""
    console.print("\n[bold blue]📋 Frontmatter Validation Results[/bold blue]")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console.print(f"[dim]Validation completed at: {timestamp}[/dim]\n")

    _display_summary_stats(result, console)
    _display_template_usage(result, console)
    _display_schemas_found(result, console, verbose)
    _display_common_issues(result, console)
    _display_detailed_results(result, console, verbose)


def _display_summary_stats(result, console: Console) -> None:
    """Display summary statistics."""
    console.print("[bold green]📊 Summary[/bold green]")
    console.print(f"  Total files: {result.total_files}")
    console.print(f"  Valid files: [green]{result.valid_files}[/green]")
    console.print(f"  Invalid files: [red]{result.invalid_files}[/red]")
    console.print(
        f"  Files with warnings: [yellow]{result.files_with_warnings}[/yellow]"
    )
    console.print(f"  Validation rate: {result.summary.get('validation_rate', 'N/A')}")


def _display_template_usage(result, console: Console) -> None:
    """Display template usage statistics."""
    if result.summary.get("template_usage"):
        console.print("\n[bold cyan]📝 Template Usage[/bold cyan]")
        for template, count in result.summary["template_usage"].items():
            console.print(f"  {template}: {count} files")


def _display_schemas_found(result, console: Console, verbose: bool) -> None:
    """Display schemas found."""
    console.print(
        f"\n[bold magenta]🔧 Schemas Found:[/bold magenta] {len(result.schemas_used)}"
    )
    if verbose:
        for name, path in result.schemas_used.items():
            console.print(f"  {name}: [dim]{path}[/dim]")


def _display_common_issues(result, console: Console) -> None:
    """Display common issues."""
    if result.summary.get("most_common_missing_fields"):
        console.print("\n[bold red]❌ Most Common Missing Fields[/bold red]")
        for field, count in result.summary["most_common_missing_fields"].items():
            console.print(f"  {field}: {count} files")

    if result.summary.get("most_common_invalid_fields"):
        console.print("\n[bold orange3]⚠️  Most Common Invalid Fields[/bold orange3]")
        for field, count in result.summary["most_common_invalid_fields"].items():
            console.print(f"  {field}: {count} files")


def _display_detailed_results(result, console: Console, verbose: bool) -> None:
    """Display detailed results."""
    if verbose or result.total_files <= 10:
        console.print("\n[bold yellow]📄 Detailed Results[/bold yellow]")
        for validation_result in result.results:
            if not validation_result.is_valid or validation_result.warnings:
                _display_single_file_result(validation_result, console)


def _display_single_file_result(validation_result, console: Console) -> None:
    """Display result for a single file."""
    console.print(f"\n  [blue]{validation_result.file_path.name}[/blue]")
    console.print(f"    Template: {validation_result.template_type or 'None'}")
    console.print(f"    Valid: {'✓' if validation_result.is_valid else '✗'}")

    if validation_result.missing_fields:
        console.print(f"    Missing: {', '.join(validation_result.missing_fields)}")

    if validation_result.invalid_fields:
        console.print("    Invalid fields:")
        for field, error in validation_result.invalid_fields.items():
            console.print(f"      {field}: {error}")

    if validation_result.warnings:
        console.print("    Warnings:")
        for warning in validation_result.warnings:
            console.print(f"      {warning}")


@app.command()
def organize(
    vault_path: Path = typer.Argument(..., help="Path to Obsidian vault"),
    dry_run: bool = typer.Option(
        True, "--dry-run/--execute", help="Preview changes without applying them"
    ),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Interactive mode for reviewing improvements"
    ),
    output_format: str = typer.Option(
        "console", "--format", help="Output format (console, json)"
    ),
    include_patterns: list[str] | None = typer.Option(
        None, "--include", help="Include file patterns"
    ),
    exclude_patterns: list[str] | None = typer.Option(
        None, "--exclude", help="Exclude file patterns"
    ),
    output_file: Path | None = typer.Option(
        None, "--output", "-o", help="Output file for results"
    ),
    max_improvements: int = typer.Option(
        50, "--max-improvements", help="Maximum improvements per file"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Automatically organize and improve knowledge base quality.

    This command analyzes your vault and applies intelligent improvements including:
    - Automatic frontmatter field completion
    - Intelligent tag suggestions based on content
    - Metadata extraction and population
    - Consistency fixes and normalization

    Use --dry-run to preview changes before applying them.
    Use --interactive to review each improvement before applying.
    """
    from .organize_command import organize_command

    organize_command(
        vault_path=vault_path,
        dry_run=dry_run,
        interactive=interactive,
        output_format=output_format,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        output_file=output_file,
        max_improvements=max_improvements,
        verbose=verbose,
    )


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()

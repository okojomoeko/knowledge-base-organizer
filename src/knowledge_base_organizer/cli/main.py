"""Main CLI interface for knowledge base organizer."""

import copy
import csv
import io
import json
import traceback
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from knowledge_base_organizer.application.auto_link_generation_use_case import (
    AutoLinkGenerationRequest,
    AutoLinkGenerationUseCase,
)
from knowledge_base_organizer.application.dead_link_detection_use_case import (
    DeadLinkDetectionRequest,
    DeadLinkDetectionUseCase,
)
from knowledge_base_organizer.application.frontmatter_validation_use_case import (
    FrontmatterValidationRequest,
    FrontmatterValidationUseCase,
)
from knowledge_base_organizer.application.vault_analyzer import VaultAnalyzer
from knowledge_base_organizer.domain.services.content_processing_service import (
    ContentProcessingService,
)
from knowledge_base_organizer.domain.services.frontmatter_validation_service import (
    FrontmatterValidationService,
)
from knowledge_base_organizer.domain.services.link_analysis_service import (
    LinkAnalysisService,
)
from knowledge_base_organizer.domain.services.yaml_type_converter import (
    YAMLTypeConverter,
)
from knowledge_base_organizer.infrastructure.config import (
    OutputFormat,
    ProcessingConfig,
)
from knowledge_base_organizer.infrastructure.file_repository import FileRepository
from knowledge_base_organizer.infrastructure.template_schema_repository import (
    TemplateSchemaRepository,
)

from .organize_command import organize_command

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

# Import and add AI services subcommand
try:
    from .ai_command import app as ai_command_app

    app.add_typer(ai_command_app, name="ai")
except ImportError:
    pass  # AI services not available

# Import and add index command
try:
    from .index_command import index_command

    app.command()(index_command)
except ImportError:
    pass  # Index command not available

# Import and add ask command (RAG)
try:
    from .ask_command import ask_command

    app.command()(ask_command)
except ImportError:
    pass  # Ask command not available


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
    template_path: Path | None = typer.Option(
        None, "--template", help="Path to template file to use as schema reference"
    ),
    output_file: Path | None = typer.Option(
        None, "--output", "-o", help="Output file for CSV/JSON results"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Validate and fix frontmatter according to template schemas.

    This command validates frontmatter in markdown files against template schemas.
    When --template is specified, uses that template file's frontmatter as the schema.
    When --template is not specified, uses automatic template detection from
    template directories.

    The command can run in dry-run mode to preview changes, or in execute mode to
    apply fixes automatically. Interactive mode allows reviewing each fix before
    applying it.

    Examples:
        # Validate using specific template
        validate-frontmatter /path/to/vault \\
            --template ~/vault/900_TemplaterNotes/new-fleeing-note.md

        # Apply fixes using template
        validate-frontmatter /path/to/vault \\
            --template ~/vault/900_TemplaterNotes/new-fleeing-note.md --execute

        # Legacy mode (auto-detect templates)
        validate-frontmatter /path/to/vault
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
        type_converter = YAMLTypeConverter()

        use_case = FrontmatterValidationUseCase(
            file_repository=file_repository,
            template_schema_repository=template_schema_repository,
            validation_service=validation_service,
            config=config,
            type_converter=type_converter,
        )

        progress.update(task, description="Extracting template schemas...")

        # Create request
        request = FrontmatterValidationRequest(
            vault_path=vault_path,
            dry_run=dry_run,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            template_path=template_path,
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


@app.command()
def detect_dead_links(
    vault_path: Path = typer.Argument(..., help="Path to Obsidian vault"),
    output_format: str = typer.Option(
        OutputFormat.CONSOLE, help="Output format (json, csv, console)"
    ),
    include_patterns: list[str] | None = typer.Option(
        None, "--include", help="Include file patterns"
    ),
    exclude_patterns: list[str] | None = typer.Option(
        None, "--exclude", help="Exclude file patterns"
    ),
    link_types: list[str] | None = typer.Option(
        None,
        "--link-type",
        help="Filter by link type (wikilink, regular_link, link_ref_def)",
    ),
    sort_by: str = typer.Option(
        "file", "--sort-by", help="Sort results by: file, line, type, target"
    ),
    limit: int | None = typer.Option(
        None, "--limit", help="Limit number of dead links shown"
    ),
    only_with_suggestions: bool = typer.Option(
        False,
        "--only-with-suggestions",
        help="Show only dead links that have fix suggestions",
    ),
    check_external_links: bool = typer.Option(
        False, "--check-external", help="Check external links (not implemented yet)"
    ),
    output_file: Path | None = typer.Option(
        None, "--output", "-o", help="Output file for CSV/JSON results"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Detect and report dead WikiLinks and regular links.

    This command scans all markdown files in the vault and identifies:
    - WikiLinks pointing to non-existent files
    - Regular markdown links with empty or invalid targets
    - Link Reference Definitions with empty paths

    Results can be output in JSON, CSV, or console format for further processing.
    """
    if verbose:
        console.print(f"[bold blue]Detecting dead links in:[/bold blue] {vault_path}")

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
        link_analysis_service = LinkAnalysisService(config_dir=vault_path / ".kiro")

        use_case = DeadLinkDetectionUseCase(
            file_repository=file_repository,
            link_analysis_service=link_analysis_service,
            config=config,
        )

        progress.update(task, description="Scanning files for dead links...")

        # Create request
        request = DeadLinkDetectionRequest(
            vault_path=vault_path,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            check_external_links=check_external_links,
        )

        try:
            result = use_case.execute(request)
            progress.update(task, description="Dead link detection complete!")

        except Exception as e:
            progress.update(task, description="Dead link detection failed!")
            console.print(f"[red]✗[/red] Error during dead link detection: {e}")
            if verbose:
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
            raise typer.Exit(1) from e

    # Apply filtering and sorting
    filtered_result = _filter_and_sort_dead_links(
        result, link_types, sort_by, limit, only_with_suggestions
    )

    # Output results
    _output_dead_link_results(
        filtered_result, output_format, output_file, console, verbose
    )

    # Final summary
    if verbose:
        console.print("[green]✓[/green] Dead link detection completed")
        console.print(f"[dim]Files scanned: {result.total_files_scanned}[/dim]")
        console.print(f"[dim]Dead links found: {result.total_dead_links}[/dim]")


@app.command()
def auto_link(
    vault_path: Path = typer.Argument(..., help="Path to Obsidian vault"),
    dry_run: bool = typer.Option(
        True, "--dry-run/--execute", help="Preview changes without applying them"
    ),
    exclude_tables: bool = typer.Option(
        False, "--exclude-tables", help="Exclude table content from link processing"
    ),
    max_links_per_file: int = typer.Option(
        50, "--max-links", help="Maximum number of links to create per file"
    ),
    max_files_to_process: int | None = typer.Option(
        None,
        "--max-files",
        help="Maximum number of files to process (useful for testing large vaults)",
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
    exclude_content_patterns: list[str] | None = typer.Option(
        None,
        "--exclude-content",
        help="Exclude content patterns from auto-linking (regex patterns)",
    ),
    target_files: list[str] | None = typer.Option(
        None, "--target", help="Specific files to process"
    ),
    output_file: Path | None = typer.Option(
        None, "--output", "-o", help="Output file for CSV/JSON results"
    ),
    semantic: bool = typer.Option(
        False, "--semantic", help="Enable semantic similarity-based linking"
    ),
    semantic_threshold: float = typer.Option(
        0.7,
        "--semantic-threshold",
        help="Minimum similarity threshold for semantic links (0.0-1.0)",
    ),
    semantic_max_candidates: int = typer.Option(
        5, "--semantic-max", help="Maximum semantic candidates per file"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Generate WikiLinks from plain text mentions.

    This command automatically detects text that matches other notes' titles or aliases
    and converts them to WikiLinks. It excludes existing links, frontmatter, and other
    protected areas from processing.

    The command supports bidirectional updates: it adds WikiLinks to source files and
    adds corresponding aliases to target files to maintain consistency.

    With --semantic enabled, the command also uses vector similarity search to find
    semantically related content for linking, even when exact text matches don't exist.
    This requires a vector index created with the 'index' command.

    Examples:
        # Basic auto-linking
        auto-link /path/to/vault --execute

        # Enable semantic linking
        auto-link /path/to/vault --semantic --execute

        # Semantic linking with custom threshold
        auto-link /path/to/vault --semantic --semantic-threshold 0.8 --execute
    """
    if verbose:
        console.print(f"[bold blue]Generating auto-links in:[/bold blue] {vault_path}")
        console.print(f"[dim]Mode: {'dry-run' if dry_run else 'execute'}[/dim]")

    # Validate vault path
    if not vault_path.exists():
        console.print(f"[red]✗[/red] Vault path does not exist: {vault_path}")
        raise typer.Exit(1)

    # Load configuration first to get file count for progress reporting
    config = _setup_auto_link_config(include_patterns, exclude_patterns)

    # Initialize file repository to get file count
    file_repository = FileRepository(config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Loading vault files...", total=None)

        # Load files to determine vault size for progress reporting
        try:
            files = file_repository.load_vault(vault_path)
            file_count = len(files)

            # Determine if this is a large vault (>100 files)
            is_large_vault = file_count > 100

            if verbose or is_large_vault:
                console.print(f"[dim]Found {file_count} markdown files in vault[/dim]")

        except Exception as e:
            progress.update(task, description="Failed to load vault!")
            console.print(f"[red]✗[/red] Error loading vault: {e}")
            if verbose:
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
            raise typer.Exit(1) from e

        progress.update(task, description="Initializing components...")

        # Initialize components
        link_analysis_service = LinkAnalysisService(
            exclude_tables=exclude_tables, config_dir=vault_path / ".kiro"
        )
        content_processing_service = ContentProcessingService(
            max_links_per_file=max_links_per_file
        )

        # Initialize AI services if semantic linking is enabled
        embedding_service = None
        vector_store = None
        if semantic:
            try:
                from knowledge_base_organizer.infrastructure.di_container import (
                    AIServiceConfig,
                    create_di_container,
                )

                ai_config = AIServiceConfig.get_default_config()
                di_container = create_di_container(vault_path, config, ai_config)
                embedding_service = di_container.get_embedding_service()
                vector_store = di_container.get_vector_store()

                # Try to load existing index
                index_path = vault_path / ".kbo_index" / "vault.index"
                if index_path.with_suffix(".faiss").exists():
                    vector_store.load_index(index_path)
                elif verbose:
                    console.print(
                        "[yellow]⚠[/yellow] No vector index found. "
                        "Run 'index' command first for better semantic results."
                    )

            except Exception as e:
                if verbose:
                    console.print(
                        f"[yellow]⚠[/yellow] Could not initialize AI services: {e}"
                    )
                    console.print("[dim]Semantic linking will be disabled[/dim]")
                semantic = False

        use_case = AutoLinkGenerationUseCase(
            file_repository=file_repository,
            link_analysis_service=link_analysis_service,
            content_processing_service=content_processing_service,
            config=config,
            embedding_service=embedding_service,
            vector_store=vector_store,
        )

        progress.update(task, description="Building file registry...")

        # Create request
        request = _create_auto_link_request(
            vault_path,
            dry_run,
            exclude_tables,
            max_links_per_file,
            max_files_to_process,
            include_patterns,
            exclude_patterns,
            exclude_content_patterns,
            target_files,
            semantic,
            semantic_threshold,
            semantic_max_candidates,
        )

        # Enhanced progress reporting for large vaults
        if is_large_vault:
            progress.update(
                task, description=f"Processing {file_count} files for auto-linking..."
            )
            if verbose:
                console.print(
                    "[dim]Large vault detected - processing may take several "
                    "minutes[/dim]"
                )
        else:
            progress.update(task, description="Generating WikiLinks...")

        try:
            result = use_case.execute(request)

            # Enhanced completion message for large vaults
            if is_large_vault:
                progress.update(
                    task,
                    description=f"Auto-link generation complete! "
                    f"Processed {result.total_files_processed} files",
                )
            else:
                progress.update(task, description="Auto-link generation complete!")

        except Exception as e:
            progress.update(task, description="Auto-link generation failed!")
            console.print(f"[red]✗[/red] Error during auto-link generation: {e}")
            if verbose:
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
            raise typer.Exit(1) from e

    # Output results
    _output_auto_link_results(result, output_format, output_file, console, verbose)

    # Enhanced final summary with performance metrics for large vaults
    _display_auto_link_summary(result, file_count, is_large_vault, verbose, console)


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
        OutputFormat.CONSOLE, help="Output format (json, console)"
    ),
    include_patterns: list[str] | None = typer.Option(
        None, "--include", help="Include file patterns"
    ),
    exclude_patterns: list[str] | None = typer.Option(
        None, "--exclude", help="Exclude file patterns"
    ),
    output_file: Path | None = typer.Option(
        None, "--output", "-o", help="Output file for JSON results"
    ),
    max_improvements: int = typer.Option(
        50, "--max-improvements", help="Maximum improvements per file"
    ),
    create_backup: bool = typer.Option(
        True, "--backup/--no-backup", help="Create backup before applying changes"
    ),
    detect_duplicates: bool = typer.Option(
        False, "--detect-duplicates", help="Detect potential duplicate files"
    ),
    duplicate_threshold: float = typer.Option(
        0.7,
        "--duplicate-threshold",
        help="Similarity threshold for duplicate detection (0.0-1.0)",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Automatically organize and improve knowledge base quality.

    This command analyzes your vault and automatically improves frontmatter,
    fixes inconsistencies, and enhances content organization. It can run in
    dry-run mode to preview changes or execute mode to apply improvements.

    Interactive mode allows reviewing each improvement before applying it.

    Use --detect-duplicates to also scan for potential duplicate files based on
    title, content, and filename similarity. The --duplicate-threshold option
    controls how similar files need to be to be considered duplicates (0.7 = 70% similar).
    """

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
        create_backup=create_backup,
        detect_duplicates=detect_duplicates,
        duplicate_threshold=duplicate_threshold,
    )


@app.command()
def maintain(
    vault_path: Path = typer.Argument(..., help="Path to Obsidian vault"),
    dry_run: bool = typer.Option(
        True, "--dry-run/--execute", help="Preview changes without applying them"
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Interactive mode for reviewing maintenance tasks",
    ),
    output_format: str = typer.Option(
        OutputFormat.CONSOLE, help="Output format (json, console)"
    ),
    include_patterns: list[str] | None = typer.Option(
        None, "--include", help="Include file patterns"
    ),
    exclude_patterns: list[str] | None = typer.Option(
        None, "--exclude", help="Exclude file patterns"
    ),
    output_file: Path | None = typer.Option(
        None, "--output", "-o", help="Output file for maintenance report"
    ),
    create_backup: bool = typer.Option(
        True, "--backup/--no-backup", help="Create backup before applying changes"
    ),
    schedule: str | None = typer.Option(
        None, "--schedule", help="Schedule maintenance (daily, weekly, monthly)"
    ),
    maintenance_tasks: list[str] | None = typer.Option(
        None,
        "--task",
        help="Specific maintenance tasks to run (organize, duplicates, orphans, dead-links)",
    ),
    duplicate_threshold: float = typer.Option(
        0.7,
        "--duplicate-threshold",
        help="Similarity threshold for duplicate detection (0.0-1.0)",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Comprehensive vault maintenance with scheduling support.

    This command performs comprehensive maintenance on your knowledge base including:
    - Frontmatter organization and improvements
    - Duplicate file detection and merge suggestions
    - Orphaned note detection and connection suggestions
    - Dead link detection and fix suggestions
    - Comprehensive maintenance reporting

    The command can be scheduled for regular execution and provides detailed
    maintenance reports for tracking vault health over time.

    Examples:
        # Run full maintenance in dry-run mode
        maintain /path/to/vault

        # Execute specific maintenance tasks
        maintain /path/to/vault --task organize --task duplicates --execute

        # Schedule daily maintenance (placeholder for future implementation)
        maintain /path/to/vault --schedule daily --execute
    """
    from .maintain_command import maintain_command

    maintain_command(
        vault_path=vault_path,
        dry_run=dry_run,
        interactive=interactive,
        output_format=output_format,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        output_file=output_file,
        create_backup=create_backup,
        schedule=schedule,
        maintenance_tasks=maintenance_tasks,
        duplicate_threshold=duplicate_threshold,
        verbose=verbose,
    )


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
            csv_data.append(
                {
                    "file_path": str(r.file_path),
                    "template_type": r.template_type or "",
                    "is_valid": r.is_valid,
                    "missing_fields": "; ".join(r.missing_fields),
                    "invalid_fields": "; ".join(
                        [f"{k}: {v}" for k, v in r.invalid_fields.items()]
                    ),
                    "warnings": "; ".join(r.warnings),
                    "suggested_fixes_count": len(r.suggested_fixes),
                }
            )

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


def _setup_auto_link_config(
    include_patterns: list[str] | None,
    exclude_patterns: list[str] | None,
) -> ProcessingConfig:
    """Set up configuration for auto-link generation."""
    config = ProcessingConfig.get_default_config()
    if include_patterns:
        config.include_patterns = include_patterns
    if exclude_patterns:
        config.exclude_patterns.extend(exclude_patterns)
    return config


def _create_auto_link_request(
    vault_path: Path,
    dry_run: bool,
    exclude_tables: bool,
    max_links_per_file: int,
    max_files_to_process: int | None,
    include_patterns: list[str] | None,
    exclude_patterns: list[str] | None,
    exclude_content_patterns: list[str] | None,
    target_files: list[str] | None,
    enable_semantic: bool = False,
    semantic_threshold: float = 0.7,
    semantic_max_candidates: int = 5,
) -> AutoLinkGenerationRequest:
    """Create auto-link generation request."""
    return AutoLinkGenerationRequest(
        vault_path=vault_path,
        dry_run=dry_run,
        exclude_tables=exclude_tables,
        max_links_per_file=max_links_per_file,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        target_files=target_files,
        max_files_to_process=max_files_to_process,
        exclude_content_patterns=exclude_content_patterns,
        preserve_frontmatter=True,  # Always preserve frontmatter format by default
        enable_semantic=enable_semantic,
        semantic_threshold=semantic_threshold,
        semantic_max_candidates=semantic_max_candidates,
    )


def _display_auto_link_summary(
    result, file_count: int, is_large_vault: bool, verbose: bool, console: Console
) -> None:
    """Display final summary for auto-link generation."""
    if verbose or is_large_vault:
        console.print("[green]✓[/green] Auto-link generation completed")
        console.print(f"[dim]Files processed: {result.total_files_processed}[/dim]")
        console.print(f"[dim]Links created: {result.total_links_created}[/dim]")
        console.print(f"[dim]Aliases added: {result.total_aliases_added}[/dim]")

        # Additional metrics for large vaults
        if is_large_vault:
            success_rate = (
                (result.total_files_processed / file_count) * 100
                if file_count > 0
                else 0
            )
            console.print(f"[dim]Success rate: {success_rate:.1f}%[/dim]")

            if result.errors:
                console.print(f"[dim]Errors encountered: {len(result.errors)}[/dim]")
            if result.skipped_files:
                console.print(f"[dim]Files skipped: {len(result.skipped_files)}[/dim]")

            # Performance tip for large vaults
            if result.total_links_created > 0:
                avg_links_per_file = (
                    result.total_links_created / result.total_files_processed
                )
                console.print(
                    f"[dim]Average links per file: {avg_links_per_file:.1f}[/dim]"
                )
    elif verbose:
        console.print("[green]✓[/green] Auto-link generation completed")
        console.print(f"[dim]Files processed: {result.total_files_processed}[/dim]")
        console.print(f"[dim]Links created: {result.total_links_created}[/dim]")
        console.print(f"[dim]Aliases added: {result.total_aliases_added}[/dim]")


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


def _filter_and_sort_dead_links(
    result,
    link_types: list[str] | None,
    sort_by: str,
    limit: int | None,
    only_with_suggestions: bool,
):
    """Filter and sort dead link results based on user criteria."""

    # Create a copy to avoid modifying the original result
    filtered_result = copy.deepcopy(result)
    dead_links = list(filtered_result.dead_links)

    # Filter by link types
    if link_types:
        valid_types = {"wikilink", "regular_link", "link_ref_def"}
        invalid_types = set(link_types) - valid_types
        if invalid_types:
            raise typer.BadParameter(
                f"Invalid link types: {', '.join(invalid_types)}. "
                f"Valid types are: {', '.join(valid_types)}"
            )
        dead_links = [dl for dl in dead_links if dl.link_type in link_types]

    # Filter by suggestions
    if only_with_suggestions:
        dead_links = [dl for dl in dead_links if dl.suggested_fixes]

    # Sort results
    if sort_by in {"file", "line"}:
        dead_links.sort(key=lambda dl: (dl.source_file, dl.line_number))
    elif sort_by == "type":
        dead_links.sort(key=lambda dl: (dl.link_type, dl.source_file, dl.line_number))
    elif sort_by == "target":
        dead_links.sort(key=lambda dl: (dl.target, dl.source_file, dl.line_number))
    else:
        raise typer.BadParameter(
            f"Invalid sort option: {sort_by}. "
            "Valid options are: file, line, type, target"
        )

    # Apply limit
    if limit is not None and limit > 0:
        dead_links = dead_links[:limit]

    # Update the result with filtered and sorted data
    filtered_result.dead_links = dead_links
    filtered_result.total_dead_links = len(dead_links)

    # Recalculate statistics
    dead_links_by_type = {}
    for dead_link in dead_links:
        link_type = dead_link.link_type
        dead_links_by_type[link_type] = dead_links_by_type.get(link_type, 0) + 1

    filtered_result.dead_links_by_type = dead_links_by_type
    filtered_result.files_with_dead_links = len({dl.source_file for dl in dead_links})

    # Update summary
    filtered_result.summary.update(
        {
            "total_dead_links": len(dead_links),
            "files_with_dead_links": filtered_result.files_with_dead_links,
            "wikilink_dead_links": dead_links_by_type.get("wikilink", 0),
            "regular_link_dead_links": dead_links_by_type.get("regular_link", 0),
            "link_ref_def_dead_links": dead_links_by_type.get("link_ref_def", 0),
        }
    )

    return filtered_result


def _output_dead_link_results(
    result,
    output_format: str,
    output_file: Path | None,
    console: Console,
    verbose: bool,
) -> None:
    """Output dead link detection results in the specified format."""

    if output_format.lower() == OutputFormat.JSON.lower():
        # Prepare JSON output
        json_data = {
            "detection_timestamp": datetime.now().isoformat(),
            "vault_path": result.vault_path,
            "summary": result.summary,
            "total_files_scanned": result.total_files_scanned,
            "files_with_dead_links": result.files_with_dead_links,
            "total_dead_links": result.total_dead_links,
            "dead_links_by_type": result.dead_links_by_type,
            "dead_links": [
                {
                    "source_file": dl.source_file,
                    "link_text": dl.link_text,
                    "link_type": dl.link_type,
                    "line_number": dl.line_number,
                    "target": dl.target,
                    "suggested_fixes": dl.suggested_fixes,
                }
                for dl in result.dead_links
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
        for dl in result.dead_links:
            csv_data.append(
                {
                    "source_file": dl.source_file,
                    "link_text": dl.link_text,
                    "link_type": dl.link_type,
                    "line_number": dl.line_number,
                    "target": dl.target,
                    "suggested_fixes": "; ".join(dl.suggested_fixes),
                }
            )

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
        _display_dead_link_console(result, console, verbose)


def _display_dead_link_console(result, console: Console, verbose: bool) -> None:
    """Display dead link detection results in console format."""
    console.print("\n[bold blue]🔗 Dead Link Detection Results[/bold blue]")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console.print(f"[dim]Detection completed at: {timestamp}[/dim]")
    console.print(f"[dim]Vault: {result.vault_path}[/dim]\n")

    # Summary statistics
    console.print("[bold green]📊 Summary[/bold green]")
    console.print(f"  Files scanned: {result.total_files_scanned}")
    console.print(f"  Files with dead links: [red]{result.files_with_dead_links}[/red]")
    console.print(f"  Total dead links: [red]{result.total_dead_links}[/red]")

    # Dead links by type
    if result.dead_links_by_type:
        console.print("\n[bold yellow]🔗 Dead Links by Type[/bold yellow]")
        for link_type, count in result.dead_links_by_type.items():
            console.print(f"  {link_type}: {count}")

    # Show individual dead links (limited for console output)
    if result.dead_links and (verbose or len(result.dead_links) <= 20):
        console.print("\n[bold red]💔 Dead Links Found[/bold red]")
        for dead_link in result.dead_links[:20]:  # Limit to first 20
            console.print(
                f"\n  [blue]{Path(dead_link.source_file).name}[/blue]:"
                f"{dead_link.line_number}"
            )
            console.print(f"    Link: {dead_link.link_text}")
            console.print(f"    Type: {dead_link.link_type}")
            console.print(f"    Target: {dead_link.target}")

            if dead_link.suggested_fixes:
                console.print("    Suggestions:")
                for suggestion in dead_link.suggested_fixes:
                    console.print(f"      • {suggestion}")

        if len(result.dead_links) > 20:
            remaining = len(result.dead_links) - 20
            console.print(f"\n  [dim]... and {remaining} more dead links[/dim]")
            console.print(
                "  [dim]Use --output to save full results or --verbose for "
                "complete list[/dim]"
            )

    elif result.dead_links:
        console.print(f"\n[yellow]Found {len(result.dead_links)} dead links[/yellow]")
        console.print(
            "[dim]Use --verbose to see details or --output to save results[/dim]"
        )


def _output_auto_link_results(
    result,
    output_format: str,
    output_file: Path | None,
    console: Console,
    verbose: bool,
) -> None:
    """Output auto-link generation results in the specified format."""

    if output_format.lower() == OutputFormat.JSON.lower():
        # Prepare JSON output
        json_data = {
            "generation_timestamp": datetime.now().isoformat(),
            "vault_path": result.vault_path,
            "summary": result.summary,
            "total_files_processed": result.total_files_processed,
            "total_links_created": result.total_links_created,
            "total_aliases_added": result.total_aliases_added,
            "file_updates": [
                {
                    "file_path": str(update.file_path),
                    "update_type": update.update_type,
                    "applied_replacements": len(update.applied_replacements)
                    if update.applied_replacements
                    else 0,
                    "frontmatter_changes": update.frontmatter_changes,
                }
                for update in result.file_updates
            ],
            "skipped_files": result.skipped_files,
            "errors": result.errors,
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
        for update in result.file_updates:
            csv_data.append(
                {
                    "file_path": str(update.file_path),
                    "update_type": update.update_type,
                    "links_added": len(update.applied_replacements)
                    if update.applied_replacements
                    else 0,
                    "aliases_added": len(update.frontmatter_changes.get("aliases", []))
                    if update.frontmatter_changes
                    else 0,
                }
            )

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
        _display_auto_link_console(result, console, verbose)


def _display_auto_link_console(result, console: Console, verbose: bool) -> None:  # noqa: PLR0912
    """Display auto-link generation results in console format."""
    console.print("\n[bold blue]🔗 Auto-Link Generation Results[/bold blue]")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console.print(f"[dim]Generation completed at: {timestamp}[/dim]")
    console.print(f"[dim]Vault: {result.vault_path}[/dim]\n")

    # Summary statistics
    console.print("[bold green]📊 Summary[/bold green]")
    console.print(f"  Files processed: {result.total_files_processed}")
    console.print(f"  Links created: [green]{result.total_links_created}[/green]")
    console.print(f"  Aliases added: [cyan]{result.total_aliases_added}[/cyan]")
    console.print(f"  Success rate: {result.summary.get('success_rate', 'N/A')}")

    # Update statistics
    if result.summary:
        console.print("\n[bold yellow]📝 Update Statistics[/bold yellow]")
        console.print(
            f"  Files with links added: "
            f"{result.summary.get('files_with_links_added', 0)}"
        )
        console.print(
            f"  Files with aliases added: "
            f"{result.summary.get('files_with_aliases_added', 0)}"
        )
        console.print(
            f"  Conflicts resolved: {result.summary.get('conflicts_resolved', 0)}"
        )
        console.print(
            f"  Candidates skipped: {result.summary.get('candidates_skipped', 0)}"
        )

    # Show errors if any
    if result.errors:
        console.print(f"\n[bold red]❌ Errors ({len(result.errors)})[/bold red]")
        for error in result.errors[:5]:  # Show first 5 errors
            console.print(f"  • {error}")
        if len(result.errors) > 5:
            console.print(f"  [dim]... and {len(result.errors) - 5} more errors[/dim]")

    # Show skipped files if any
    if result.skipped_files:
        console.print(
            f"\n[bold orange3]⚠️  Skipped Files "
            f"({len(result.skipped_files)})[/bold orange3]"
        )
        if verbose:
            for skipped in result.skipped_files:
                console.print(f"  • {skipped}")
        else:
            console.print(
                f"  {len(result.skipped_files)} files skipped "
                f"(use --verbose for details)"
            )

    # Show detailed file updates
    if verbose and result.file_updates:
        console.print("\n[bold cyan]📄 File Updates[/bold cyan]")
        wikilink_updates = [
            u for u in result.file_updates if u.update_type == "add_wikilink"
        ]
        alias_updates = [u for u in result.file_updates if u.update_type == "add_alias"]

        if wikilink_updates:
            console.print("\n  [green]WikiLink Updates:[/green]")
            for update in wikilink_updates[:10]:  # Show first 10
                links_count = (
                    len(update.applied_replacements)
                    if update.applied_replacements
                    else 0
                )
                console.print(
                    f"    {Path(update.file_path).name}: {links_count} links added"
                )

        if alias_updates:
            console.print("\n  [cyan]Alias Updates:[/cyan]")
            for update in alias_updates[:10]:  # Show first 10
                if (
                    update.frontmatter_changes
                    and "aliases" in update.frontmatter_changes
                ):
                    aliases = update.frontmatter_changes["aliases"]
                    console.print(
                        f"    {Path(update.file_path).name}: "
                        f"{len(aliases)} total aliases"
                    )


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()

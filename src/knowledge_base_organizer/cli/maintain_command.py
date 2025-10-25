"""CLI command for comprehensive vault maintenance."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..application.dead_link_detection_use_case import (
    DeadLinkDetectionRequest,
    DeadLinkDetectionUseCase,
)
from ..domain.services.content_analysis_service import ContentAnalysisService
from ..domain.services.frontmatter_enhancement_service import (
    FrontmatterEnhancementService,
)
from ..domain.services.link_analysis_service import LinkAnalysisService
from ..infrastructure.config import ProcessingConfig
from ..infrastructure.file_repository import FileRepository

console = Console()


def maintain_command(  # noqa: PLR0912, PLR0915
    vault_path: Path,
    dry_run: bool = True,
    interactive: bool = False,
    output_format: str = "console",
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    output_file: Path | None = None,
    create_backup: bool = True,
    schedule: str | None = None,
    maintenance_tasks: list[str] | None = None,
    duplicate_threshold: float = 0.7,
    verbose: bool = False,
) -> None:
    """Comprehensive vault maintenance with scheduling support."""
    try:
        # Skip header output for JSON format to keep output clean
        if output_format != "json":
            console.print("🔧 [bold blue]Knowledge Base Maintenance[/bold blue]")
            console.print(f"Vault: {vault_path}")
            console.print(f"Mode: {'dry-run' if dry_run else 'execute'}")

            if schedule:
                console.print(f"Schedule: {schedule}")
                console.print(
                    "[yellow]Note: Scheduling functionality is planned for "
                    "future release[/yellow]"
                )

            if interactive:
                console.print("Interactive mode enabled")

        # Validate vault path
        if not vault_path.exists():
            console.print(f"❌ Vault path does not exist: {vault_path}")
            raise typer.Exit(1)

        # Create configuration
        config = ProcessingConfig(
            include_patterns=include_patterns or ["**/*.md"],
            exclude_patterns=exclude_patterns or [],
        )

        # Determine which maintenance tasks to run
        tasks_to_run = _determine_maintenance_tasks(maintenance_tasks)

        # Initialize maintenance report
        maintenance_report = _initialize_maintenance_report(vault_path, tasks_to_run)

        # Run maintenance tasks
        if output_format == "json":
            # For JSON output, run tasks without progress display
            if "organize" in tasks_to_run:
                organize_results = _run_organize_maintenance(
                    vault_path, config, dry_run
                )
                maintenance_report["tasks"]["organize"] = organize_results

            if "duplicates" in tasks_to_run:
                duplicate_results = _run_duplicate_detection(
                    vault_path, config, duplicate_threshold
                )
                maintenance_report["tasks"]["duplicates"] = duplicate_results

            if "orphans" in tasks_to_run:
                orphan_results = _run_orphan_detection(vault_path, config)
                maintenance_report["tasks"]["orphans"] = orphan_results

            if "dead-links" in tasks_to_run:
                dead_link_results = _run_dead_link_detection(vault_path, config)
                maintenance_report["tasks"]["dead-links"] = dead_link_results
        else:
            # For console output, show progress
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Starting maintenance...", total=None)

                if "organize" in tasks_to_run:
                    progress.update(
                        task, description="Running frontmatter organization..."
                    )
                    organize_results = _run_organize_maintenance(
                        vault_path, config, dry_run
                    )
                    maintenance_report["tasks"]["organize"] = organize_results

                if "duplicates" in tasks_to_run:
                    progress.update(task, description="Detecting duplicate files...")
                    duplicate_results = _run_duplicate_detection(
                        vault_path, config, duplicate_threshold
                    )
                    maintenance_report["tasks"]["duplicates"] = duplicate_results

                if "orphans" in tasks_to_run:
                    progress.update(task, description="Detecting orphaned notes...")
                    orphan_results = _run_orphan_detection(vault_path, config)
                    maintenance_report["tasks"]["orphans"] = orphan_results

                if "dead-links" in tasks_to_run:
                    progress.update(task, description="Detecting dead links...")
                    dead_link_results = _run_dead_link_detection(vault_path, config)
                    maintenance_report["tasks"]["dead-links"] = dead_link_results

                progress.update(task, description="Generating maintenance report...")

        # Finalize maintenance report
        maintenance_report["completion_time"] = datetime.now().isoformat()
        maintenance_report["summary"] = _generate_maintenance_summary(
            maintenance_report
        )

        # Display results
        if output_format == "console":
            _display_maintenance_console(maintenance_report, verbose)
        elif output_format == "json":
            _output_maintenance_json(maintenance_report, output_file)

        # Apply changes if not dry-run and user confirms
        if not dry_run:
            if interactive:
                _apply_interactive_maintenance(
                    maintenance_report, vault_path, config, create_backup
                )
            else:
                _apply_automatic_maintenance(
                    maintenance_report, vault_path, config, create_backup
                )

        if output_format != "json":
            console.print("✅ [green]Maintenance completed successfully[/green]")

    except Exception as e:
        console.print(f"❌ Error during maintenance: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1) from e


def _determine_maintenance_tasks(maintenance_tasks: list[str] | None) -> list[str]:
    """Determine which maintenance tasks to run."""
    available_tasks = ["organize", "duplicates", "orphans", "dead-links"]

    if maintenance_tasks:
        # Validate requested tasks
        invalid_tasks = set(maintenance_tasks) - set(available_tasks)
        if invalid_tasks:
            console.print(f"❌ Invalid maintenance tasks: {', '.join(invalid_tasks)}")
            console.print(f"Available tasks: {', '.join(available_tasks)}")
            raise typer.Exit(1)
        return maintenance_tasks

    # Run all tasks by default
    return available_tasks


def _initialize_maintenance_report(
    vault_path: Path, tasks_to_run: list[str]
) -> dict[str, Any]:
    """Initialize the maintenance report structure."""
    return {
        "vault_path": str(vault_path),
        "start_time": datetime.now().isoformat(),
        "completion_time": None,
        "tasks_requested": tasks_to_run,
        "tasks": {},
        "summary": {},
    }


def _run_organize_maintenance(
    vault_path: Path, config: ProcessingConfig, dry_run: bool
) -> dict[str, Any]:
    """Run frontmatter organization maintenance."""
    try:
        file_repo = FileRepository(config)
        files = file_repo.load_vault(vault_path)

        enhancement_service = FrontmatterEnhancementService()
        results = enhancement_service.enhance_vault_frontmatter(
            files, apply_changes=not dry_run
        )

        # Filter to only results with improvements
        improvement_results = [
            r for r in results if r.success and r.improvements_made > 0
        ]

        return {
            "status": "completed",
            "files_analyzed": len(files),
            "files_with_improvements": len(improvement_results),
            "total_improvements": sum(r.improvements_made for r in improvement_results),
            "improvements_applied": not dry_run,
            "details": [
                {
                    "file_path": str(r.file_path),
                    "improvements_made": r.improvements_made,
                    "changes_applied": r.changes_applied[:5],  # Limit for report size
                }
                for r in improvement_results[:10]  # Top 10 files
            ],
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
        }


def _run_duplicate_detection(
    vault_path: Path, config: ProcessingConfig, threshold: float
) -> dict[str, Any]:
    """Run duplicate file detection."""
    try:
        file_repo = FileRepository(config)
        files = file_repo.load_vault(vault_path)

        analysis_service = ContentAnalysisService()
        duplicate_results = analysis_service.detect_duplicates(files, threshold)

        # Filter to only results with potential duplicates
        files_with_duplicates = [r for r in duplicate_results if r.potential_duplicates]

        return {
            "status": "completed",
            "files_analyzed": len(files),
            "files_with_duplicates": len(files_with_duplicates),
            "total_duplicate_pairs": sum(
                len(r.potential_duplicates) for r in files_with_duplicates
            ),
            "high_confidence_duplicates": sum(
                1 for r in files_with_duplicates if r.is_likely_duplicate
            ),
            "threshold_used": threshold,
            "details": [
                {
                    "file_path": str(r.file_path),
                    "is_likely_duplicate": r.is_likely_duplicate,
                    "duplicate_count": len(r.potential_duplicates),
                    "top_matches": [
                        {
                            "file_path": str(dup.file_path),
                            "similarity_score": dup.similarity_score,
                            "match_type": dup.match_type,
                        }
                        for dup in r.potential_duplicates[:3]  # Top 3 matches
                    ],
                }
                for r in files_with_duplicates[:10]  # Top 10 files
            ],
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
        }


def _run_orphan_detection(vault_path: Path, config: ProcessingConfig) -> dict[str, Any]:
    """Run orphaned note detection."""
    try:
        file_repo = FileRepository(config)
        files = file_repo.load_vault(vault_path)

        link_analysis_service = LinkAnalysisService(config_dir=vault_path / ".kiro")

        # Build file registry for link analysis (not used in current implementation)

        # Detect orphaned files (files with no incoming or outgoing links)
        orphaned_files = []
        for file in files:
            # Extract links from file
            file.extract_links()

            # Check if file has outgoing links
            has_outgoing_links = bool(file.wiki_links or file.regular_links)

            # Check if file has incoming links (referenced by other files)
            has_incoming_links = any(
                file.file_id in [link.target_id for link in other_file.wiki_links]
                for other_file in files
                if other_file != file and other_file.wiki_links
            )

            if not has_outgoing_links and not has_incoming_links:
                # Suggest potential connections based on content similarity
                connection_suggestions = (
                    link_analysis_service.suggest_connections_for_orphan(
                        file,
                        files[:50],  # Limit for performance
                    )
                )

                orphaned_files.append(
                    {
                        "file_path": str(file.path),
                        "file_id": file.file_id,
                        "title": file.frontmatter.title or file.path.stem,
                        "content_length": len(file.content),
                        "suggested_connections": connection_suggestions[
                            :5
                        ],  # Top 5 suggestions
                    }
                )

        return {
            "status": "completed",
            "files_analyzed": len(files),
            "orphaned_files_count": len(orphaned_files),
            "orphaned_files": orphaned_files[:20],  # Limit for report size
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
        }


def _run_dead_link_detection(
    vault_path: Path, config: ProcessingConfig
) -> dict[str, Any]:
    """Run dead link detection."""
    try:
        file_repository = FileRepository(config)
        link_analysis_service = LinkAnalysisService(config_dir=vault_path / ".kiro")

        use_case = DeadLinkDetectionUseCase(
            file_repository=file_repository,
            link_analysis_service=link_analysis_service,
            config=config,
        )

        request = DeadLinkDetectionRequest(
            vault_path=vault_path,
            include_patterns=config.include_patterns,
            exclude_patterns=config.exclude_patterns,
            check_external_links=False,
        )

        result = use_case.execute(request)

        return {
            "status": "completed",
            "files_scanned": result.total_files_scanned,
            "files_with_dead_links": result.files_with_dead_links,
            "total_dead_links": result.total_dead_links,
            "dead_links_by_type": result.dead_links_by_type,
            "dead_links_with_suggestions": len(
                [dl for dl in result.dead_links if dl.suggested_fixes]
            ),
            "sample_dead_links": [
                {
                    "source_file": dl.source_file,
                    "link_text": dl.link_text,
                    "link_type": dl.link_type,
                    "target": dl.target,
                    "has_suggestions": bool(dl.suggested_fixes),
                }
                for dl in result.dead_links[:10]  # Sample of dead links
            ],
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
        }


def _generate_maintenance_summary(maintenance_report: dict[str, Any]) -> dict[str, Any]:
    """Generate summary statistics for the maintenance report."""
    summary = {
        "tasks_completed": 0,
        "tasks_failed": 0,
        "total_issues_found": 0,
        "vault_health_score": 0.0,
    }

    for task_name, task_result in maintenance_report["tasks"].items():
        if task_result["status"] == "completed":
            summary["tasks_completed"] += 1

            # Count issues found per task
            if task_name == "organize":
                summary["total_issues_found"] += task_result.get(
                    "files_with_improvements", 0
                )
            elif task_name == "duplicates":
                summary["total_issues_found"] += task_result.get(
                    "files_with_duplicates", 0
                )
            elif task_name == "orphans":
                summary["total_issues_found"] += task_result.get(
                    "orphaned_files_count", 0
                )
            elif task_name == "dead-links":
                summary["total_issues_found"] += task_result.get("total_dead_links", 0)
        else:
            summary["tasks_failed"] += 1

    # Calculate vault health score (0-100)
    total_tasks = len(maintenance_report["tasks"])
    if total_tasks > 0:
        completion_rate = summary["tasks_completed"] / total_tasks
        # Simple health score based on completion rate and issues found
        # Lower issues = higher health score
        issue_penalty = min(
            summary["total_issues_found"] * 0.01, 0.5
        )  # Max 50% penalty
        summary["vault_health_score"] = max(0, (completion_rate - issue_penalty) * 100)

    return summary


def _display_maintenance_console(
    maintenance_report: dict[str, Any], verbose: bool
) -> None:
    """Display maintenance results in console format."""
    console.print("\n📊 [bold blue]Maintenance Report[/bold blue]")
    console.print(f"[dim]Vault: {maintenance_report['vault_path']}[/dim]")
    console.print(f"[dim]Completed: {maintenance_report['completion_time']}[/dim]\n")

    # Summary table
    summary = maintenance_report["summary"]
    summary_table = Table(title="Maintenance Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    summary_table.add_row("Tasks Completed", str(summary["tasks_completed"]))
    summary_table.add_row("Tasks Failed", str(summary["tasks_failed"]))
    summary_table.add_row("Total Issues Found", str(summary["total_issues_found"]))
    summary_table.add_row("Vault Health Score", f"{summary['vault_health_score']:.1f}%")

    console.print(summary_table)

    # Task details
    console.print("\n🔍 [bold yellow]Task Details[/bold yellow]")

    for task_name, task_result in maintenance_report["tasks"].items():
        if task_result["status"] == "completed":
            console.print(f"\n✅ [green]{task_name.title()}[/green]")
            _display_task_details(task_name, task_result, verbose)
        else:
            console.print(f"\n❌ [red]{task_name.title()}[/red]")
            console.print(f"  Error: {task_result.get('error', 'Unknown error')}")


def _display_task_details(
    task_name: str, task_result: dict[str, Any], verbose: bool
) -> None:
    """Display details for a specific maintenance task."""
    if task_name == "organize":
        console.print(f"  Files analyzed: {task_result['files_analyzed']}")
        console.print(
            f"  Files with improvements: {task_result['files_with_improvements']}"
        )
        console.print(f"  Total improvements: {task_result['total_improvements']}")

        if verbose and task_result.get("details"):
            console.print("  Top files improved:")
            for detail in task_result["details"][:5]:
                console.print(
                    f"    • {Path(detail['file_path']).name}: "
                    f"{detail['improvements_made']} improvements"
                )

    elif task_name == "duplicates":
        console.print(f"  Files analyzed: {task_result['files_analyzed']}")
        console.print(
            f"  Files with duplicates: {task_result['files_with_duplicates']}"
        )
        console.print(
            f"  High confidence duplicates: {task_result['high_confidence_duplicates']}"
        )

        if verbose and task_result.get("details"):
            console.print("  Files with potential duplicates:")
            for detail in task_result["details"][:5]:
                console.print(
                    f"    • {Path(detail['file_path']).name}: "
                    f"{detail['duplicate_count']} potential matches"
                )

    elif task_name == "orphans":
        console.print(f"  Files analyzed: {task_result['files_analyzed']}")
        console.print(f"  Orphaned files: {task_result['orphaned_files_count']}")

        if verbose and task_result.get("orphaned_files"):
            console.print("  Orphaned files found:")
            for orphan in task_result["orphaned_files"][:5]:
                console.print(f"    • {Path(orphan['file_path']).name}")

    elif task_name == "dead-links":
        console.print(f"  Files scanned: {task_result['files_scanned']}")
        console.print(f"  Dead links found: {task_result['total_dead_links']}")
        console.print(
            f"  Files with dead links: {task_result['files_with_dead_links']}"
        )
        console.print(
            f"  Dead links with fix suggestions: "
            f"{task_result['dead_links_with_suggestions']}"
        )


def _output_maintenance_json(
    maintenance_report: dict[str, Any], output_file: Path | None
) -> None:
    """Output maintenance report in JSON format."""
    if output_file:
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(maintenance_report, f, indent=2, ensure_ascii=False)
        console.print(f"📄 Maintenance report saved to: {output_file}")
    else:
        # For JSON output to stdout, print only the JSON without other messages
        print(json.dumps(maintenance_report, indent=2, ensure_ascii=False))


def _apply_interactive_maintenance(
    maintenance_report: dict[str, Any],
    vault_path: Path,
    config: ProcessingConfig,
    create_backup: bool,
) -> None:
    """Apply maintenance changes interactively."""
    console.print("\n🔧 [bold yellow]Interactive Maintenance Mode[/bold yellow]")
    console.print("Review maintenance tasks and choose which to apply.\n")

    # This is a placeholder for interactive maintenance application
    # In a full implementation, this would allow users to selectively apply fixes
    console.print(
        "[yellow]Interactive maintenance application is planned for "
        "future release[/yellow]"
    )
    console.print("Currently, maintenance runs in analysis mode only.")


def _apply_automatic_maintenance(
    maintenance_report: dict[str, Any],
    vault_path: Path,
    config: ProcessingConfig,
    create_backup: bool,
) -> None:
    """Apply maintenance changes automatically."""
    console.print("\n🔧 [bold green]Applying Maintenance Changes[/bold green]")

    # This is a placeholder for automatic maintenance application
    # In a full implementation, this would apply the maintenance fixes
    console.print(
        "[yellow]Automatic maintenance application is planned for "
        "future release[/yellow]"
    )
    console.print("Currently, maintenance runs in analysis mode only.")
    console.print(
        "Use the organize command with --execute to apply frontmatter improvements."
    )

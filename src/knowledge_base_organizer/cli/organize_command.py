"""CLI command for automatic vault organization."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..domain.services.frontmatter_enhancement_service import (
    FrontmatterEnhancementService,
)
from ..infrastructure.config import ProcessingConfig
from ..infrastructure.file_repository import FileRepository

console = Console()


def organize_command(
    vault_path: Path,
    dry_run: bool = True,
    interactive: bool = False,
    output_format: str = "console",
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    output_file: Path | None = None,
    max_improvements: int = 50,
    verbose: bool = False,
) -> None:
    """Automatically organize and improve knowledge base quality."""
    try:
        console.print(f"🔧 Organizing vault: {vault_path}")
        console.print(f"Mode: {'dry-run' if dry_run else 'execute'}")
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

        # Load files and analyze
        results = _analyze_vault_improvements(vault_path, config)

        if not results:
            console.print("✅ No improvements needed - your vault is well organized!")
            return

        # Limit improvements per file
        for result in results:
            if len(result.changes_applied) > max_improvements:
                result.changes_applied = result.changes_applied[:max_improvements]
                result.improvements_made = len(result.changes_applied)

        # Display summary
        _display_summary(results)

        # Display results based on format
        if output_format == "console":
            _display_console_results(results, verbose)
        elif output_format == "json":
            _output_json_results(results, output_file)

        # Apply changes if not dry-run
        if not dry_run:
            if interactive:
                _apply_interactive_changes(results, vault_path, config)
            else:
                _apply_all_changes(results, vault_path, config)

    except Exception as e:
        console.print(f"❌ Error during organization: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1) from e


def _analyze_vault_improvements(
    vault_path: Path, config: ProcessingConfig
) -> list[Any]:
    """Analyze vault for improvement opportunities."""
    file_repo = FileRepository(config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Loading files...", total=None)
        files = file_repo.load_vault(vault_path)
        progress.update(task, description=f"Loaded {len(files)} files")

        if not files:
            console.print("❌ No markdown files found in vault")
            raise typer.Exit(1)

        # Initialize enhancement service
        progress.update(task, description="Analyzing improvements...")
        enhancement_service = FrontmatterEnhancementService()

        # Analyze improvements
        results = enhancement_service.enhance_vault_frontmatter(
            files, apply_changes=False
        )

        progress.update(task, description="Analysis complete!")

    # Filter to only results with improvements
    return [r for r in results if r.success and r.improvements_made > 0]


def _display_summary(results: list[Any]) -> None:
    """Display summary of improvements found."""
    total_improvements = sum(r.improvements_made for r in results)

    console.print("\n📊 Organization Analysis Complete")
    console.print(f"Files with improvements: {len(results)}")
    console.print(f"Total improvements found: {total_improvements}")


def _display_console_results(results: list[Any], verbose: bool = False) -> None:
    """Display organization results in console format."""
    console.print("\n🔍 Improvement Details:")

    for result in results[:10]:  # Show top 10 files
        console.print(f"\n📄 {result.file_path.name}")
        console.print(f"  Improvements: {result.improvements_made}")

        if verbose:
            for change in result.changes_applied[:5]:  # Show top 5 changes
                console.print(f"  • {change}")
            if len(result.changes_applied) > 5:
                remaining = len(result.changes_applied) - 5
                console.print(f"  • ... and {remaining} more")

    if len(results) > 10:
        console.print(f"\n... and {len(results) - 10} more files with improvements")


def _output_json_results(results: list[Any], output_file: Path | None) -> None:
    """Output organization results in JSON format."""
    output_data = {
        "summary": {
            "total_files": len(results),
            "total_improvements": sum(r.improvements_made for r in results),
            "timestamp": datetime.now().isoformat(),
        },
        "improvements": [
            {
                "file_path": str(result.file_path),
                "improvements_made": result.improvements_made,
                "changes_applied": result.changes_applied,
                "success": result.success,
            }
            for result in results
        ],
    }

    if output_file:
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        console.print(f"📄 Results saved to: {output_file}")
    else:
        console.print(json.dumps(output_data, indent=2, ensure_ascii=False))


def _apply_all_changes(
    results: list[Any], vault_path: Path, config: ProcessingConfig
) -> None:
    """Apply all improvements automatically."""
    file_repo = FileRepository(config)
    files = file_repo.load_vault(vault_path)
    enhancement_service = FrontmatterEnhancementService()

    total_improvements = sum(r.improvements_made for r in results)
    console.print(f"\n🔧 Applying {total_improvements} improvements...")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Applying improvements...", total=len(results))

        applied_count = 0
        for result in results:
            # Find the corresponding file and apply changes
            target_file = next((f for f in files if f.path == result.file_path), None)
            if target_file:
                # Re-run enhancement with apply_changes=True
                enhancement_result = enhancement_service.enhance_file_frontmatter(
                    target_file, apply_changes=True
                )
                if enhancement_result.success:
                    # Save the file
                    file_repo.save_file(target_file)
                    applied_count += 1

            progress.advance(task)

        progress.update(task, description=f"Applied {applied_count} improvements")

    console.print(f"✅ Successfully applied improvements to {applied_count} files")


def _apply_interactive_changes(
    results: list[Any], vault_path: Path, config: ProcessingConfig
) -> None:
    """Apply improvements interactively."""
    file_repo = FileRepository(config)
    files = file_repo.load_vault(vault_path)
    enhancement_service = FrontmatterEnhancementService()

    console.print("\n🔧 Interactive Organization Mode")
    console.print("Review each improvement and choose whether to apply it.\n")

    applied_count = 0

    for result in results:
        console.print(f"📄 File: {result.file_path}")
        console.print(f"Improvements available: {result.improvements_made}")

        for i, change in enumerate(result.changes_applied, 1):
            console.print(f"  {i}. {change}")

        apply = typer.confirm(f"\nApply improvements to {result.file_path.name}?")

        if apply:
            # Find the corresponding file and apply changes
            target_file = next((f for f in files if f.path == result.file_path), None)
            if target_file:
                enhancement_result = enhancement_service.enhance_file_frontmatter(
                    target_file, apply_changes=True
                )
                if enhancement_result.success:
                    # Save the file
                    file_repo.save_file(target_file)
                    applied_count += 1
                    console.print("✅ Improvements applied")
                else:
                    console.print("❌ Failed to apply improvements")
            else:
                console.print("❌ File not found")
        else:
            console.print("⏭️  Skipped")

        console.print()  # Empty line for readability

    console.print(f"✅ Applied improvements to {applied_count} files")

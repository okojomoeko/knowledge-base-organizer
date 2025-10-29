"""CLI command for automatic vault organization."""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..domain.services.content_analysis_service import ContentAnalysisService
from ..domain.services.frontmatter_enhancement_service import (
    FrontmatterEnhancementService,
)
from ..infrastructure.config import ProcessingConfig
from ..infrastructure.file_repository import FileRepository
from ..infrastructure.ollama_llm import OllamaLLMService

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
    create_backup: bool = True,
    detect_duplicates: bool = False,
    duplicate_threshold: float = 0.7,
    ai_suggest_metadata: bool = False,
) -> None:
    """Automatically organize and improve knowledge base quality."""
    try:
        console.print(f"🔧 Organizing vault: {vault_path}")
        console.print(f"Mode: {'dry-run' if dry_run else 'execute'}")
        if interactive:
            console.print("Interactive mode enabled")
        if ai_suggest_metadata:
            console.print("AI metadata suggestions enabled")

        # Validate vault path
        if not vault_path.exists():
            console.print(f"❌ Vault path does not exist: {vault_path}")
            raise typer.Exit(1)

        # Create configuration
        config = ProcessingConfig(
            include_patterns=include_patterns or ["**/*.md"],
            exclude_patterns=exclude_patterns or [],
        )

        # Initialize AI service if requested
        llm_service = None
        if ai_suggest_metadata:
            try:
                llm_service = OllamaLLMService()
                console.print("✅ AI service initialized successfully")
            except Exception as e:
                console.print(f"⚠️ Failed to initialize AI service: {e}")
                console.print("Continuing without AI suggestions...")
                ai_suggest_metadata = False

        # Load files and analyze
        results = _analyze_vault_improvements(vault_path, config, llm_service)

        # Detect duplicates if requested
        duplicate_results = []
        if detect_duplicates:
            duplicate_results = _analyze_vault_duplicates(
                vault_path, config, duplicate_threshold
            )

        if not results and not duplicate_results:
            console.print("✅ No improvements needed - your vault is well organized!")
            return

        # Limit improvements per file
        for result in results:
            if len(result.changes_applied) > max_improvements:
                result.changes_applied = result.changes_applied[:max_improvements]
                result.improvements_made = len(result.changes_applied)

        # Display summary
        _display_summary(results, duplicate_results)

        # Display results based on format
        if output_format == "console":
            _display_console_results(results, verbose)
            if duplicate_results:
                _display_duplicate_results(duplicate_results, verbose)
        elif output_format == "json":
            _output_json_results(results, output_file, duplicate_results)

        # Apply changes if not dry-run
        if not dry_run:
            # Create backup before applying changes
            backup_path = None
            if create_backup:
                backup_path = _create_vault_backup(vault_path)
                console.print(f"📦 Backup created at: {backup_path}")

            try:
                if interactive:
                    applied_count = _apply_interactive_changes(
                        results, vault_path, config, llm_service
                    )
                else:
                    applied_count = _apply_all_changes(
                        results, vault_path, config, llm_service
                    )

                # Generate comprehensive improvement report
                _generate_improvement_report(
                    results, applied_count, vault_path, output_file
                )

            except Exception as e:
                if backup_path:
                    console.print(f"❌ Error occurred: {e}")
                    console.print(f"💾 Backup available at: {backup_path}")
                    console.print("Use the backup to restore your vault if needed.")
                raise

    except Exception as e:
        console.print(f"❌ Error during organization: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1) from e


def _analyze_vault_improvements(
    vault_path: Path, config: ProcessingConfig, llm_service=None
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

        # Set LLM service if available
        if llm_service:
            enhancement_service.set_llm_service(llm_service)

        # Analyze improvements
        results = enhancement_service.enhance_vault_frontmatter(
            files, apply_changes=False
        )

        progress.update(task, description="Analysis complete!")

    # Filter to only results with improvements
    return [r for r in results if r.success and r.improvements_made > 0]


def _analyze_vault_duplicates(
    vault_path: Path, config: ProcessingConfig, threshold: float = 0.7
) -> list[Any]:
    """Analyze vault for duplicate files."""
    file_repo = FileRepository(config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Loading files for duplicate detection...", total=None)
        files = file_repo.load_vault(vault_path)
        progress.update(task, description=f"Loaded {len(files)} files")

        if not files:
            return []

        # Initialize content analysis service
        progress.update(task, description="Detecting duplicates...")
        analysis_service = ContentAnalysisService()

        # Detect duplicates
        duplicate_results = analysis_service.detect_duplicates(files, threshold)

        progress.update(task, description="Duplicate detection complete!")

    # Filter to only results with potential duplicates
    return [r for r in duplicate_results if r.potential_duplicates]


def _display_summary(
    results: list[Any], duplicate_results: list[Any] | None = None
) -> None:
    """Display summary of improvements found."""
    total_improvements = sum(r.improvements_made for r in results)

    console.print("\n📊 Organization Analysis Complete")
    console.print(f"Files with improvements: {len(results)}")
    console.print(f"Total improvements found: {total_improvements}")

    if duplicate_results:
        total_duplicates = sum(len(r.potential_duplicates) for r in duplicate_results)
        likely_duplicates = sum(1 for r in duplicate_results if r.is_likely_duplicate)
        console.print(f"Files with potential duplicates: {len(duplicate_results)}")
        console.print(f"Total potential duplicate pairs: {total_duplicates}")
        console.print(f"High-confidence duplicates: {likely_duplicates}")


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


def _display_duplicate_results(results: list[Any], verbose: bool = False) -> None:
    """Display duplicate detection results in console format."""
    console.print("\n🔍 Duplicate Detection Results:")

    for result in results[:10]:  # Show top 10 files with duplicates
        console.print(f"\n📄 {result.file_path.name}")
        console.print(f"  Potential duplicates: {len(result.potential_duplicates)}")
        console.print(
            f"  Likely duplicate: {'Yes' if result.is_likely_duplicate else 'No'}"
        )

        if verbose:
            for i, duplicate in enumerate(result.potential_duplicates[:3], 1):
                console.print(f"  {i}. {duplicate.file_path.name}")
                console.print(f"     Similarity: {duplicate.similarity_score:.2f}")
                console.print(f"     Match type: {duplicate.match_type}")
                console.print(f"     Confidence: {duplicate.confidence:.2f}")
                if duplicate.match_details:
                    console.print(f"     Details: {duplicate.match_details}")

            if len(result.potential_duplicates) > 3:
                remaining = len(result.potential_duplicates) - 3
                console.print(f"     ... and {remaining} more potential duplicates")

            if result.merge_suggestions:
                console.print("  Merge suggestions:")
                for suggestion in result.merge_suggestions[:2]:
                    console.print(f"    • {suggestion}")

    if len(results) > 10:
        console.print(
            f"\n... and {len(results) - 10} more files with potential duplicates"
        )


def _output_json_results(
    results: list[Any],
    output_file: Path | None,
    duplicate_results: list[Any] | None = None,
) -> None:
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

    if duplicate_results:
        output_data["duplicate_detection"] = {
            "summary": {
                "files_with_duplicates": len(duplicate_results),
                "total_potential_duplicates": sum(
                    len(r.potential_duplicates) for r in duplicate_results
                ),
                "high_confidence_duplicates": sum(
                    1 for r in duplicate_results if r.is_likely_duplicate
                ),
            },
            "duplicates": [
                {
                    "file_path": str(result.file_path),
                    "is_likely_duplicate": result.is_likely_duplicate,
                    "potential_duplicates": [
                        {
                            "file_path": str(dup.file_path),
                            "similarity_score": dup.similarity_score,
                            "match_type": dup.match_type,
                            "confidence": dup.confidence,
                            "match_details": dup.match_details,
                        }
                        for dup in result.potential_duplicates
                    ],
                    "merge_suggestions": result.merge_suggestions,
                    "analysis_notes": result.analysis_notes,
                }
                for result in duplicate_results
            ],
        }

    if output_file:
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        console.print(f"📄 Results saved to: {output_file}")
    else:
        console.print(json.dumps(output_data, indent=2, ensure_ascii=False))


def _apply_all_changes(
    results: list[Any], vault_path: Path, config: ProcessingConfig, llm_service=None
) -> int:
    """Apply all improvements automatically."""
    file_repo = FileRepository(config)
    files = file_repo.load_vault(vault_path)
    enhancement_service = FrontmatterEnhancementService()

    # Set LLM service if available
    if llm_service:
        enhancement_service.set_llm_service(llm_service)

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
    return applied_count


def _apply_interactive_changes(
    results: list[Any], vault_path: Path, config: ProcessingConfig, llm_service=None
) -> int:
    """Apply improvements interactively."""
    file_repo = FileRepository(config)
    files = file_repo.load_vault(vault_path)
    enhancement_service = FrontmatterEnhancementService()

    # Set LLM service if available
    if llm_service:
        enhancement_service.set_llm_service(llm_service)

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
    return applied_count


def _create_vault_backup(vault_path: Path) -> Path:
    """Create a backup of the vault before applying changes."""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{vault_path.name}_backup_{timestamp}"
    backup_path = vault_path.parent / backup_name

    console.print(f"📦 Creating backup: {backup_path}")
    shutil.copytree(
        vault_path, backup_path, ignore=shutil.ignore_patterns("*.tmp", ".obsidian")
    )

    return backup_path


def _generate_improvement_report(
    results: list[Any], applied_count: int, vault_path: Path, output_file: Path | None
) -> None:
    """Generate a comprehensive improvement report."""
    report_data = {
        "vault_path": str(vault_path),
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_files_analyzed": len(results),
            "files_improved": applied_count,
            "total_improvements": sum(r.improvements_made for r in results),
            "improvement_categories": _categorize_improvements(results),
        },
        "detailed_improvements": [
            {
                "file_path": str(result.file_path),
                "improvements_made": result.improvements_made,
                "changes_applied": result.changes_applied,
                "success": result.success,
            }
            for result in results
        ],
        "metrics": {
            "files_with_frontmatter_improvements": sum(
                1
                for r in results
                if any(
                    "frontmatter" in str(change).lower() for change in r.changes_applied
                )
            ),
            "files_with_metadata_additions": sum(
                1
                for r in results
                if any(
                    "metadata" in str(change).lower() for change in r.changes_applied
                )
            ),
            "files_with_tag_improvements": sum(
                1
                for r in results
                if any("tag" in str(change).lower() for change in r.changes_applied)
            ),
        },
    }

    # Save report
    report_filename = (
        f"organization_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    report_path = output_file or (vault_path / report_filename)

    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    console.print(f"📊 Comprehensive improvement report saved to: {report_path}")

    # Display summary
    console.print("\n📈 Organization Summary:")
    console.print(f"  Files analyzed: {report_data['summary']['total_files_analyzed']}")
    console.print(f"  Files improved: {report_data['summary']['files_improved']}")
    console.print(
        f"  Total improvements: {report_data['summary']['total_improvements']}"
    )
    console.print(
        f"  Frontmatter improvements: "
        f"{report_data['metrics']['files_with_frontmatter_improvements']}"
    )
    console.print(
        f"  Metadata additions: "
        f"{report_data['metrics']['files_with_metadata_additions']}"
    )
    console.print(
        f"  Tag improvements: {report_data['metrics']['files_with_tag_improvements']}"
    )


def _categorize_improvements(results: list[Any]) -> dict[str, int]:
    """Categorize improvements by type."""
    categories = {
        "frontmatter_fixes": 0,
        "metadata_additions": 0,
        "tag_improvements": 0,
        "content_enhancements": 0,
        "consistency_fixes": 0,
    }

    for result in results:
        for change in result.changes_applied:
            change_str = str(change).lower()
            if "frontmatter" in change_str:
                categories["frontmatter_fixes"] += 1
            elif "metadata" in change_str:
                categories["metadata_additions"] += 1
            elif "tag" in change_str:
                categories["tag_improvements"] += 1
            elif "content" in change_str:
                categories["content_enhancements"] += 1
            else:
                categories["consistency_fixes"] += 1

    return categories

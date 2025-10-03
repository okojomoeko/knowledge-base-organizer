"""CLI commands for tag pattern management."""

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from ..domain.services.frontmatter_enhancement_service import (
    FrontmatterEnhancementService,
)
from ..infrastructure.file_repository import FileRepository

app = typer.Typer(name="tag-management", help="Tag pattern management commands")
console = Console()


@app.command("list-patterns")
def list_tag_patterns(
    config_dir: Path = typer.Option(
        None, "--config-dir", help="Configuration directory path"
    ),
    category: str = typer.Option(None, "--category", help="Filter by category"),
    format_output: str = typer.Option(
        "table", "--format", help="Output format: table, json, tree"
    ),
) -> None:
    """List all tag patterns."""
    service = FrontmatterEnhancementService(config_dir)
    patterns = service.tag_pattern_manager.get_all_patterns()

    if format_output == "json":
        output = {}
        for cat_name, category_obj in patterns.items():
            if category and cat_name != category:
                continue
            output[cat_name] = {
                "description": category_obj.description,
                "priority": category_obj.priority,
                "patterns": {
                    name: {
                        "tag_name": pattern.tag_name,
                        "keywords": pattern.keywords,
                        "confidence_weight": pattern.confidence_weight,
                        "usage_count": pattern.usage_count,
                        "description": pattern.description,
                    }
                    for name, pattern in category_obj.patterns.items()
                },
            }
        console.print(json.dumps(output, indent=2, ensure_ascii=False))
        return

    if format_output == "tree":
        tree = Tree("🏷️  Tag Patterns")
        for cat_name, category_obj in patterns.items():
            if category and cat_name != category:
                continue

            cat_branch = tree.add(f"📁 {cat_name} (Priority: {category_obj.priority})")
            cat_branch.add(f"📝 {category_obj.description}")

            for _name, pattern in category_obj.patterns.items():
                pattern_branch = cat_branch.add(f"🏷️  {pattern.tag_name}")
                pattern_branch.add(f"Keywords: {', '.join(pattern.keywords[:5])}...")
                pattern_branch.add(f"Usage: {pattern.usage_count} times")
                if pattern.description:
                    pattern_branch.add(f"Description: {pattern.description}")

        console.print(tree)
        return

    # Default table format
    table = Table(title="Tag Patterns")
    table.add_column("Category", style="cyan")
    table.add_column("Tag", style="green")
    table.add_column("Keywords", style="yellow")
    table.add_column("Weight", justify="right")
    table.add_column("Usage", justify="right")
    table.add_column("Description", style="dim")

    for cat_name, category_obj in patterns.items():
        if category and cat_name != category:
            continue

        for pattern in category_obj.patterns.values():
            keywords_str = ", ".join(pattern.keywords[:3])
            if len(pattern.keywords) > 3:
                keywords_str += f" (+{len(pattern.keywords) - 3} more)"

            table.add_row(
                cat_name,
                pattern.tag_name,
                keywords_str,
                f"{pattern.confidence_weight:.1f}",
                str(pattern.usage_count),
                pattern.description or "",
            )

    console.print(table)


@app.command("add-pattern")
def add_tag_pattern(
    category: str = typer.Argument(..., help="Category name"),
    pattern_name: str = typer.Argument(..., help="Pattern name"),
    tag_name: str = typer.Argument(..., help="Tag name to suggest"),
    keywords: str = typer.Argument(..., help="Comma-separated keywords"),
    config_dir: Path = typer.Option(
        None, "--config-dir", help="Configuration directory path"
    ),
    description: str = typer.Option(None, "--description", help="Pattern description"),
    confidence_weight: float = typer.Option(
        1.0, "--weight", help="Confidence weight (0.0-2.0)"
    ),
) -> None:
    """Add a new tag pattern."""
    service = FrontmatterEnhancementService(config_dir)

    keyword_list = [kw.strip() for kw in keywords.split(",")]

    service.add_custom_tag_pattern(
        category=category,
        pattern_name=pattern_name,
        tag_name=tag_name,
        keywords=keyword_list,
        description=description,
        confidence_weight=confidence_weight,
    )

    console.print(f"✅ Added pattern '{pattern_name}' to category '{category}'")


@app.command("search-patterns")
def search_tag_patterns(
    query: str = typer.Argument(..., help="Search query"),
    config_dir: Path = typer.Option(
        None, "--config-dir", help="Configuration directory path"
    ),
) -> None:
    """Search for tag patterns."""
    service = FrontmatterEnhancementService(config_dir)
    results = service.search_tag_patterns(query)

    if not results:
        console.print(f"❌ No patterns found for query: '{query}'")
        return

    table = Table(title=f"Search Results for '{query}'")
    table.add_column("Tag", style="green")
    table.add_column("Category", style="cyan")
    table.add_column("Keywords", style="yellow")
    table.add_column("Usage", justify="right")
    table.add_column("Description", style="dim")

    for result in results:
        keywords_str = ", ".join(result["keywords"][:3])
        if len(result["keywords"]) > 3:
            keywords_str += f" (+{len(result['keywords']) - 3} more)"

        table.add_row(
            result["tag_name"],
            result["category"],
            keywords_str,
            str(result["usage_count"]),
            result["description"] or "",
        )

    console.print(table)


@app.command("analyze-vault")
def analyze_vault_tags(
    vault_path: Path = typer.Argument(..., help="Path to vault directory"),
    config_dir: Path = typer.Option(
        None, "--config-dir", help="Configuration directory path"
    ),
    output_file: Path = typer.Option(
        None, "--output", help="Save analysis to JSON file"
    ),
    show_details: bool = typer.Option(
        False, "--details", help="Show detailed analysis"
    ),
) -> None:
    """Analyze existing tags in the vault."""
    console.print(f"🔍 Analyzing vault: {vault_path}")

    # Load files
    from ..infrastructure.config import ProcessingConfig

    config = ProcessingConfig()
    file_repo = FileRepository(config)
    files = file_repo.load_vault(vault_path)

    console.print(f"📁 Found {len(files)} files")

    # Analyze tags
    service = FrontmatterEnhancementService(config_dir)
    analysis = service.update_vault_tag_analysis(files)

    # Display summary
    console.print("\n📊 Vault Tag Analysis Summary")
    console.print(f"Total files: {analysis.total_files}")
    console.print(f"Total tags: {analysis.total_tags}")
    console.print(f"Unique tags: {analysis.unique_tags}")
    console.print(
        f"Average tags per file: {analysis.total_tags / analysis.total_files:.1f}"
    )

    # Most common tags
    if analysis.most_common_tags:
        console.print("\n🏆 Most Common Tags:")
        table = Table()
        table.add_column("Rank", justify="right")
        table.add_column("Tag", style="green")
        table.add_column("Count", justify="right")
        table.add_column("Percentage", justify="right")

        for i, (tag, count) in enumerate(analysis.most_common_tags[:10], 1):
            percentage = (count / analysis.total_files) * 100
            table.add_row(str(i), tag, str(count), f"{percentage:.1f}%")

        console.print(table)

    # Orphaned tags
    if analysis.orphaned_tags and show_details:
        console.print(f"\n🔍 Orphaned Tags ({len(analysis.orphaned_tags)}):")
        console.print(", ".join(analysis.orphaned_tags[:20]))
        if len(analysis.orphaned_tags) > 20:
            console.print(f"... and {len(analysis.orphaned_tags) - 20} more")

    # Save to file if requested
    if output_file:
        with Path(output_file).open("w", encoding="utf-8") as f:
            json.dump(
                analysis.model_dump(), f, indent=2, ensure_ascii=False, default=str
            )
        console.print(f"💾 Analysis saved to: {output_file}")


@app.command("suggest-tags")
def suggest_tags_for_file(
    file_path: Path = typer.Argument(..., help="Path to markdown file"),
    config_dir: Path = typer.Option(
        None, "--config-dir", help="Configuration directory path"
    ),
    min_confidence: float = typer.Option(
        0.3, "--min-confidence", help="Minimum confidence threshold"
    ),
    show_confidence: bool = typer.Option(
        True, "--show-confidence", help="Show confidence scores"
    ),
) -> None:
    """Suggest tags for a specific file."""
    if not file_path.exists():
        console.print(f"❌ File not found: {file_path}")
        raise typer.Exit(1)

    # Load file
    from ..infrastructure.config import ProcessingConfig

    config = ProcessingConfig()
    file_repo = FileRepository(config)
    try:
        markdown_file = file_repo.load_file(file_path)
    except Exception as e:
        console.print(f"❌ Error loading file: {e}")
        raise typer.Exit(1) from e

    # Get suggestions
    service = FrontmatterEnhancementService(config_dir)
    suggestions = service.get_tag_suggestions_with_confidence(markdown_file)

    # Filter by confidence
    filtered_suggestions = [
        (tag, conf) for tag, conf in suggestions if conf >= min_confidence
    ]

    if not filtered_suggestions:
        console.print(
            f"❌ No tag suggestions found with confidence >= {min_confidence}"
        )
        return

    console.print(f"🏷️  Tag Suggestions for: {file_path.name}")
    console.print(
        f"Current tags: {', '.join(markdown_file.frontmatter.tags or ['None'])}"
    )

    table = Table()
    table.add_column("Tag", style="green")
    if show_confidence:
        table.add_column("Confidence", justify="right")
    table.add_column("Status")

    current_tags = set(markdown_file.frontmatter.tags or [])

    for tag, confidence in filtered_suggestions:
        status = "✅ Current" if tag in current_tags else "🆕 New"
        if show_confidence:
            table.add_row(tag, f"{confidence:.2f}", status)
        else:
            table.add_row(tag, status)

    console.print(table)


@app.command("export-for-llm")
def export_patterns_for_llm(
    config_dir: Path = typer.Option(
        None, "--config-dir", help="Configuration directory path"
    ),
    output_file: Path = typer.Option(
        "tag_patterns_llm.json", "--output", help="Output file path"
    ),
) -> None:
    """Export tag patterns in LLM-friendly format."""
    service = FrontmatterEnhancementService(config_dir)
    llm_data = service.export_tag_patterns_for_llm()

    with Path(output_file).open("w", encoding="utf-8") as f:
        json.dump(llm_data, f, indent=2, ensure_ascii=False, default=str)

    console.print(f"📤 Tag patterns exported for LLM: {output_file}")
    console.print(f"Total categories: {llm_data['metadata']['total_categories']}")
    console.print(f"Total patterns: {llm_data['metadata']['total_patterns']}")


@app.command("related-tags")
def show_related_tags(
    tag: str = typer.Argument(..., help="Tag to find relationships for"),
    vault_path: Path = typer.Option(None, "--vault", help="Vault path for analysis"),
    config_dir: Path = typer.Option(
        None, "--config-dir", help="Configuration directory path"
    ),
    min_strength: float = typer.Option(
        0.3, "--min-strength", help="Minimum relationship strength"
    ),
) -> None:
    """Show tags related to the given tag."""
    service = FrontmatterEnhancementService(config_dir)

    # If vault path provided, update analysis first
    if vault_path:
        from ..infrastructure.config import ProcessingConfig

        config = ProcessingConfig()
        file_repo = FileRepository(config)
        files = file_repo.load_vault(vault_path)
        service.update_vault_tag_analysis(files)

    related = service.suggest_related_tags(tag, min_strength)

    if not related:
        console.print(
            f"❌ No related tags found for '{tag}' with strength >= {min_strength}"
        )
        return

    console.print(f"🔗 Tags related to '{tag}':")

    table = Table()
    table.add_column("Related Tag", style="green")
    table.add_column("Strength", justify="right")
    table.add_column("Relationship")

    for related_tag, strength in related:
        if strength >= 0.7:
            relationship = "🔥 Strong"
        elif strength >= 0.5:
            relationship = "🔶 Medium"
        else:
            relationship = "🔸 Weak"

        table.add_row(related_tag, f"{strength:.2f}", relationship)

    console.print(table)


if __name__ == "__main__":
    app()

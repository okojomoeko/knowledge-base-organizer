"""Frontmatter enhancement service for automatic field completion."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from ..models import Frontmatter, MarkdownFile
from .content_analysis_service import ContentAnalysisService


class EnhancementResult(BaseModel):
    """Result of frontmatter enhancement operation."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    file_path: Path
    original_frontmatter: dict[str, Any]
    enhanced_frontmatter: dict[str, Any]
    changes_applied: list[str]
    improvements_made: int
    success: bool
    error_message: str | None = None


class FrontmatterEnhancementService:
    """Service for automatically enhancing frontmatter with missing fields."""

    def __init__(self) -> None:
        """Initialize frontmatter enhancement service."""
        self.content_analyzer = ContentAnalysisService()

    def enhance_file_frontmatter(
        self, file: MarkdownFile, apply_changes: bool = False
    ) -> EnhancementResult:
        """Enhance frontmatter for a single file."""
        try:
            # Analyze file for improvements
            analysis_result = self.content_analyzer.analyze_file(file)

            # Get current frontmatter as dict
            original_frontmatter = file.frontmatter.model_dump(exclude_unset=True)
            enhanced_frontmatter = original_frontmatter.copy()
            changes_applied = []

            # Apply improvements with high confidence
            for improvement in analysis_result.improvements:
                if (
                    improvement.confidence >= 0.7
                ):  # Only apply high-confidence improvements
                    if improvement.improvement_type == "missing_required_field":
                        # Always apply missing required fields
                        enhanced_frontmatter[improvement.field_name] = (
                            improvement.suggested_value
                        )
                        changes_applied.append(
                            f"Added {improvement.field_name}: {improvement.suggested_value}"
                        )

                    elif improvement.improvement_type == "missing_tags":
                        # Merge with existing tags
                        current_tags = enhanced_frontmatter.get("tags", [])
                        suggested_tags = improvement.suggested_value

                        # Add only new tags
                        new_tags = []
                        for tag in suggested_tags:
                            if tag not in current_tags:
                                new_tags.append(tag)

                        if new_tags:
                            enhanced_frontmatter["tags"] = current_tags + new_tags
                            changes_applied.append(f"Added tags: {new_tags}")

                    elif improvement.improvement_type == "missing_description":
                        enhanced_frontmatter["description"] = (
                            improvement.suggested_value
                        )
                        changes_applied.append(
                            f"Added description: {improvement.suggested_value[:50]}..."
                        )

                    elif improvement.improvement_type == "missing_category":
                        enhanced_frontmatter["category"] = improvement.suggested_value
                        changes_applied.append(
                            f"Added category: {improvement.suggested_value}"
                        )

            # Apply changes to file if requested
            if apply_changes and changes_applied:
                # Create new frontmatter object
                enhanced_frontmatter_obj = Frontmatter(**enhanced_frontmatter)
                file.frontmatter = enhanced_frontmatter_obj

            return EnhancementResult(
                file_path=file.path,
                original_frontmatter=original_frontmatter,
                enhanced_frontmatter=enhanced_frontmatter,
                changes_applied=changes_applied,
                improvements_made=len(changes_applied),
                success=True,
            )

        except Exception as e:
            return EnhancementResult(
                file_path=file.path,
                original_frontmatter={},
                enhanced_frontmatter={},
                changes_applied=[],
                improvements_made=0,
                success=False,
                error_message=str(e),
            )

    def enhance_vault_frontmatter(
        self,
        files: list[MarkdownFile],
        apply_changes: bool = False,
        min_confidence: float = 0.7,
    ) -> list[EnhancementResult]:
        """Enhance frontmatter for multiple files in a vault."""
        results = []

        for file in files:
            try:
                result = self.enhance_file_frontmatter(file, apply_changes)
                results.append(result)
            except Exception as e:
                error_result = EnhancementResult(
                    file_path=file.path,
                    original_frontmatter={},
                    enhanced_frontmatter={},
                    changes_applied=[],
                    improvements_made=0,
                    success=False,
                    error_message=str(e),
                )
                results.append(error_result)

        return results

    def generate_enhancement_summary(
        self, results: list[EnhancementResult]
    ) -> dict[str, Any]:
        """Generate summary statistics for enhancement results."""
        total_files = len(results)
        successful_enhancements = sum(
            1 for r in results if r.success and r.improvements_made > 0
        )
        failed_enhancements = sum(1 for r in results if not r.success)
        total_improvements = sum(r.improvements_made for r in results)

        # Count improvement types
        improvement_types = {}
        for result in results:
            for change in result.changes_applied:
                if "Added tags:" in change:
                    improvement_types["tags_added"] = (
                        improvement_types.get("tags_added", 0) + 1
                    )
                elif "Added description:" in change:
                    improvement_types["descriptions_added"] = (
                        improvement_types.get("descriptions_added", 0) + 1
                    )
                elif "Added category:" in change:
                    improvement_types["categories_added"] = (
                        improvement_types.get("categories_added", 0) + 1
                    )
                elif "Added " in change and ":" in change:
                    field_name = change.split("Added ")[1].split(":")[0]
                    improvement_types[f"{field_name}_added"] = (
                        improvement_types.get(f"{field_name}_added", 0) + 1
                    )

        return {
            "total_files": total_files,
            "successful_enhancements": successful_enhancements,
            "failed_enhancements": failed_enhancements,
            "total_improvements": total_improvements,
            "enhancement_rate": f"{(successful_enhancements / total_files * 100):.1f}%"
            if total_files > 0
            else "0%",
            "improvement_types": improvement_types,
            "files_with_errors": [r.file_path for r in results if not r.success],
        }

    def get_high_priority_files(
        self, results: list[EnhancementResult], limit: int = 10
    ) -> list[EnhancementResult]:
        """Get files with the most critical improvements needed."""
        # Sort by number of improvements needed (descending)
        sorted_results = sorted(
            [r for r in results if r.success and r.improvements_made > 0],
            key=lambda x: x.improvements_made,
            reverse=True,
        )

        return sorted_results[:limit]

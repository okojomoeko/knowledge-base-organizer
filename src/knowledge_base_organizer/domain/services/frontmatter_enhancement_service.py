"""Frontmatter enhancement service for automatic field completion."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from ..models import Frontmatter, MarkdownFile
from .content_analysis_service import ContentAnalysisService
from .tag_pattern_manager import TagPatternManager, VaultTagAnalysis


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

    def __init__(self, config_dir: Path | None = None) -> None:
        """Initialize frontmatter enhancement service."""
        self.content_analyzer = ContentAnalysisService()
        self.tag_pattern_manager = TagPatternManager(config_dir)

        # Legacy advanced tag patterns (kept for backward compatibility)
        self.advanced_tag_patterns = {
            "programming_languages": {
                "python": ["python", "py", "django", "flask", "pandas", "numpy"],
                "javascript": ["javascript", "js", "node", "react", "vue", "angular"],
                "java": ["java", "spring", "maven", "gradle"],
                "typescript": ["typescript", "ts", "angular", "nest"],
                "rust": ["rust", "cargo", "tokio"],
                "go": ["golang", "go", "gin", "echo"],
            },
            "technologies": {
                "database": ["sql", "mysql", "postgresql", "mongodb", "redis"],
                "cloud": ["aws", "azure", "gcp", "docker", "kubernetes"],
                "frontend": ["html", "css", "sass", "webpack", "vite"],
                "backend": ["api", "rest", "graphql", "microservice"],
                "devops": ["ci/cd", "jenkins", "github actions", "terraform"],
            },
            "concepts": {
                "architecture": [
                    "design pattern",
                    "architecture",
                    "microservice",
                    "monolith",
                ],
                "algorithms": [
                    "algorithm",
                    "data structure",
                    "complexity",
                    "optimization",
                ],
                "security": [
                    "security",
                    "authentication",
                    "authorization",
                    "encryption",
                ],
                "testing": ["test", "unit test", "integration test", "tdd", "bdd"],
            },
            "japanese_content": {
                "language": [
                    "日本語",
                    "japanese",
                    "nihongo",
                    "katakana",
                    "hiragana",
                    "kanji",
                ],
                "culture": ["文化", "culture", "tradition", "festival", "ceremony"],
                "business": ["ビジネス", "business", "company", "work", "職場"],
            },
        }

        # Metadata extraction patterns
        self.metadata_patterns = {
            "author": re.compile(
                r"(?:author|著者|writer|written by)[:]\s*([^\n]+)", re.IGNORECASE
            ),
            "source": re.compile(r"(?:source|出典|from)[:]\s*([^\n]+)", re.IGNORECASE),
            "date_created": re.compile(
                r"(?:created|作成日|date)[:]\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE
            ),
            "project": re.compile(
                r"(?:project|プロジェクト)[:]\s*([^\n]+)", re.IGNORECASE
            ),
            "status": re.compile(
                r"(?:status|状態)[:]\s*(draft|complete|in-progress|todo)",
                re.IGNORECASE,
            ),
        }

    def suggest_intelligent_tags_with_patterns(
        self, file: MarkdownFile, existing_vault_tags: set[str] | None = None
    ) -> list[str]:
        """Suggest intelligent tags using the pattern manager."""
        # Use pattern manager for suggestions
        pattern_suggestions = self.tag_pattern_manager.suggest_tags_for_content(
            file.content
        )
        suggested_tags = set()

        # Add high-confidence pattern suggestions
        for tag, confidence in pattern_suggestions:
            if confidence > 0.4:  # Configurable threshold
                suggested_tags.add(tag)

        # Analyze existing vault tags for similarity (if provided)
        if existing_vault_tags:
            content_words = set(re.findall(r"\b\w+\b", file.content.lower()))
            for vault_tag in existing_vault_tags:
                tag_words = set(re.findall(r"\b\w+\b", vault_tag.lower()))

                # If content contains words similar to existing tags, suggest them
                if tag_words.intersection(content_words):
                    suggested_tags.add(vault_tag)

        # Extract hashtags from content as potential tags
        hashtag_pattern = re.compile(r"#(\w+)")
        hashtags = hashtag_pattern.findall(file.content)
        for hashtag in hashtags:
            if len(hashtag) > 2:  # Avoid very short hashtags
                suggested_tags.add(hashtag.lower())

        # Remove existing tags
        current_tags = set(file.frontmatter.tags or [])
        new_tags = suggested_tags - current_tags

        return sorted(new_tags)

    def suggest_intelligent_tags(
        self, file: MarkdownFile, existing_vault_tags: set[str] | None = None
    ) -> list[str]:
        """Suggest intelligent tags based on advanced content analysis."""
        content_lower = file.content.lower()
        suggested_tags = set()

        # Analyze content for advanced tag patterns
        for category, subcategories in self.advanced_tag_patterns.items():
            for subcategory, keywords in subcategories.items():
                keyword_matches = sum(
                    1 for keyword in keywords if keyword in content_lower
                )

                if keyword_matches > 0:
                    # Calculate confidence based on keyword density and frequency
                    confidence = min(0.95, keyword_matches * 0.2)

                    if confidence > 0.4:  # Only suggest if reasonably confident
                        suggested_tags.add(subcategory)

                        # Also suggest broader category if multiple subcategories match
                        if keyword_matches > 2:
                            suggested_tags.add(category.replace("_", "-"))

        # Analyze existing vault tags for similarity (if provided)
        if existing_vault_tags:
            content_words = set(re.findall(r"\b\w+\b", content_lower))
            for vault_tag in existing_vault_tags:
                tag_words = set(re.findall(r"\b\w+\b", vault_tag.lower()))

                # If content contains words similar to existing tags, suggest them
                if tag_words.intersection(content_words):
                    suggested_tags.add(vault_tag)

        # Extract hashtags from content as potential tags
        hashtag_pattern = re.compile(r"#(\w+)")
        hashtags = hashtag_pattern.findall(file.content)
        for hashtag in hashtags:
            if len(hashtag) > 2:  # Avoid very short hashtags
                suggested_tags.add(hashtag.lower())

        # Remove existing tags
        current_tags = set(file.frontmatter.tags or [])
        new_tags = suggested_tags - current_tags

        return sorted(new_tags)

    def analyze_tag_relationships(
        self, files: list[MarkdownFile]
    ) -> dict[str, dict[str, float]]:
        """Analyze relationships between tags across the vault."""
        tag_cooccurrence = {}
        tag_counts = {}

        # Count tag occurrences and co-occurrences
        for file in files:
            file_tags = set(file.frontmatter.tags or [])

            for tag in file_tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

                if tag not in tag_cooccurrence:
                    tag_cooccurrence[tag] = {}

                # Count co-occurrences with other tags in the same file
                for other_tag in file_tags:
                    if other_tag != tag:
                        tag_cooccurrence[tag][other_tag] = (
                            tag_cooccurrence[tag].get(other_tag, 0) + 1
                        )

        # Calculate relationship strengths (normalized by tag frequency)
        tag_relationships = {}
        for tag, cooccurrences in tag_cooccurrence.items():
            tag_relationships[tag] = {}
            tag_frequency = tag_counts[tag]

            for related_tag, count in cooccurrences.items():
                # Calculate relationship strength (0.0 to 1.0)
                strength = count / tag_frequency
                tag_relationships[tag][related_tag] = strength

        return tag_relationships

    def suggest_related_tags_for_file(
        self,
        file: MarkdownFile,
        tag_relationships: dict[str, dict[str, float]],
        min_strength: float = 0.3,
    ) -> list[str]:
        """Suggest related tags based on existing tags in the file."""
        current_tags = set(file.frontmatter.tags or [])
        suggested_tags = set()

        for current_tag in current_tags:
            if current_tag in tag_relationships:
                for related_tag, strength in tag_relationships[current_tag].items():
                    if strength >= min_strength and related_tag not in current_tags:
                        suggested_tags.add(related_tag)

        return sorted(suggested_tags)

    def extract_metadata_from_content(self, file: MarkdownFile) -> dict[str, Any]:
        """Extract metadata from content using pattern matching."""
        metadata = {}

        # Extract structured metadata using patterns
        for field_name, pattern in self.metadata_patterns.items():
            match = pattern.search(file.content)
            if match:
                metadata[field_name] = match.group(1).strip()

        # Extract dates from file system if not found in content
        if "date_created" not in metadata:
            try:
                # Use file creation time as fallback
                stat = file.path.stat()
                creation_time = datetime.fromtimestamp(stat.st_ctime)
                metadata["date_created"] = creation_time.strftime("%Y-%m-%d")
            except Exception:
                pass

        # Extract publication date from filename if it follows timestamp pattern
        filename = file.path.stem
        if re.match(r"^\d{14}$", filename):
            try:
                # Parse timestamp filename (YYYYMMDDHHmmss)
                year = int(filename[:4])
                month = int(filename[4:6])
                day = int(filename[6:8])
                hour = int(filename[8:10])
                minute = int(filename[10:12])
                second = int(filename[12:14])

                timestamp = datetime(year, month, day, hour, minute, second)
                metadata["published"] = timestamp.strftime("%Y-%m-%d")
                metadata["created_time"] = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass

        # Extract word count and reading time
        word_count = len(re.findall(r"\b\w+\b", file.content))
        metadata["word_count"] = word_count
        # Assume 200 words per minute reading speed
        metadata["reading_time"] = max(1, word_count // 200)

        # Detect content language
        japanese_chars = len(
            re.findall(r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]", file.content)
        )
        english_words = len(re.findall(r"\b[a-zA-Z]+\b", file.content))

        if japanese_chars > english_words * 2:
            metadata["language"] = "japanese"
        elif english_words > 10:
            metadata["language"] = "english"
        else:
            metadata["language"] = "mixed"

        return metadata

    def populate_automatic_dates(self, file: MarkdownFile) -> dict[str, str]:
        """Populate automatic date fields based on file metadata and content."""
        date_fields = {}

        try:
            stat = file.path.stat()

            # Creation date
            creation_time = datetime.fromtimestamp(stat.st_ctime)
            date_fields["created"] = creation_time.strftime("%Y-%m-%d")

            # Modification date
            mod_time = datetime.fromtimestamp(stat.st_mtime)
            date_fields["modified"] = mod_time.strftime("%Y-%m-%d")

            # If file has timestamp-based ID, use that as published date
            if file.frontmatter.id and re.match(r"^\d{14}$", file.frontmatter.id):
                try:
                    year = int(file.frontmatter.id[:4])
                    month = int(file.frontmatter.id[4:6])
                    day = int(file.frontmatter.id[6:8])
                    published_date = datetime(year, month, day)
                    date_fields["published"] = published_date.strftime("%Y-%m-%d")
                except ValueError:
                    pass

            # If no published date and file is recently created, use creation date
            if "published" not in date_fields:
                date_fields["published"] = date_fields["created"]

        except Exception:
            # Fallback to current date
            current_date = datetime.now().strftime("%Y-%m-%d")
            date_fields["created"] = current_date
            date_fields["published"] = current_date

        return date_fields

    def enhance_file_frontmatter(
        self,
        file: MarkdownFile,
        apply_changes: bool = False,
        existing_vault_tags: set[str] | None = None,
    ) -> EnhancementResult:
        """Enhance frontmatter for a single file with intelligent analysis."""
        try:
            # Analyze file for improvements using existing content analyzer
            analysis_result = self.content_analyzer.analyze_file(file)

            # Get current frontmatter as dict
            original_frontmatter = file.frontmatter.model_dump(exclude_unset=True)
            enhanced_frontmatter = original_frontmatter.copy()
            changes_applied = []

            # 1. Apply intelligent tag suggestions (Requirement 8.4)
            intelligent_tags = self.suggest_intelligent_tags(file, existing_vault_tags)
            if intelligent_tags:
                current_tags = enhanced_frontmatter.get("tags", [])
                # Add only new intelligent tags
                new_intelligent_tags = [
                    tag for tag in intelligent_tags if tag not in current_tags
                ]
                if new_intelligent_tags:
                    enhanced_frontmatter["tags"] = current_tags + new_intelligent_tags
                    changes_applied.append(
                        f"Added intelligent tags: {new_intelligent_tags}"
                    )

            # 2. Extract and populate metadata from content (Requirement 8.2)
            extracted_metadata = self.extract_metadata_from_content(file)
            for field_name, value in extracted_metadata.items():
                if (
                    field_name not in enhanced_frontmatter
                    or not enhanced_frontmatter[field_name]
                ):
                    enhanced_frontmatter[field_name] = value
                    changes_applied.append(f"Added metadata {field_name}: {value}")

            # 3. Populate automatic date fields (Requirement 8.2)
            date_fields = self.populate_automatic_dates(file)
            for field_name, date_value in date_fields.items():
                if (
                    field_name not in enhanced_frontmatter
                    or not enhanced_frontmatter[field_name]
                ):
                    enhanced_frontmatter[field_name] = date_value
                    changes_applied.append(f"Added date {field_name}: {date_value}")

            # 4. Apply improvements from content analysis (Requirement 8.1)
            for improvement in analysis_result.improvements:
                if (
                    improvement.confidence >= 0.7
                ):  # Only apply high-confidence improvements
                    if improvement.improvement_type == "missing_required_field":
                        # Always apply missing required fields
                        enhanced_frontmatter[improvement.field_name] = (
                            improvement.suggested_value
                        )
                        field_name = improvement.field_name
                        value = improvement.suggested_value
                        changes_applied.append(
                            f"Added required field {field_name}: {value}"
                        )

                    elif improvement.improvement_type == "missing_tags":
                        # Merge with existing tags (avoid duplicates)
                        current_tags = enhanced_frontmatter.get("tags", [])
                        suggested_tags = improvement.suggested_value

                        # Add only new tags that aren't already added
                        new_tags = [
                            tag for tag in suggested_tags if tag not in current_tags
                        ]
                        if new_tags:
                            enhanced_frontmatter["tags"] = current_tags + new_tags
                            changes_applied.append(
                                f"Added content-based tags: {new_tags}"
                            )

                    elif improvement.improvement_type == "missing_description":
                        if (
                            "description" not in enhanced_frontmatter
                            or not enhanced_frontmatter["description"]
                        ):
                            enhanced_frontmatter["description"] = (
                                improvement.suggested_value
                            )
                            desc_preview = improvement.suggested_value[:50]
                            changes_applied.append(
                                f"Added description: {desc_preview}..."
                            )

                    elif improvement.improvement_type == "missing_category":
                        if (
                            "category" not in enhanced_frontmatter
                            or not enhanced_frontmatter["category"]
                        ):
                            enhanced_frontmatter["category"] = (
                                improvement.suggested_value
                            )
                            changes_applied.append(
                                f"Added category: {improvement.suggested_value}"
                            )

            # 5. Ensure ID field is populated if missing
            if not enhanced_frontmatter.get("id"):
                # Try to extract from filename or generate timestamp-based ID
                file_id = file.extract_file_id()
                if not file_id:
                    # Generate timestamp-based ID
                    file_id = datetime.now().strftime("%Y%m%d%H%M%S")
                enhanced_frontmatter["id"] = file_id
                changes_applied.append(f"Added ID: {file_id}")

            # 6. Ensure title is populated if missing
            if not enhanced_frontmatter.get("title"):
                # Use filename as title (without extension)
                title = file.path.stem
                # Clean up timestamp-based filenames
                if re.match(r"^\d{14}$", title):
                    title = f"Note {title[:8]}"  # Use date part as title
                enhanced_frontmatter["title"] = title
                changes_applied.append(f"Added title: {title}")

            # Apply changes to file if requested
            if apply_changes and changes_applied:
                # Create new frontmatter object with enhanced data
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
    ) -> list[EnhancementResult]:
        """Enhance frontmatter for multiple files in a vault."""
        results = []

        # First pass: collect all existing tags from the vault
        existing_vault_tags = set()
        for file in files:
            if file.frontmatter.tags:
                existing_vault_tags.update(file.frontmatter.tags)

        # Second pass: enhance each file with vault context
        for file in files:
            try:
                result = self.enhance_file_frontmatter(
                    file,
                    apply_changes=apply_changes,
                    existing_vault_tags=existing_vault_tags,
                )
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

        # Count improvement types with more detailed categorization
        improvement_types = {}
        for result in results:
            for change in result.changes_applied:
                if "Added intelligent tags:" in change:
                    improvement_types["intelligent_tags_added"] = (
                        improvement_types.get("intelligent_tags_added", 0) + 1
                    )
                elif "Added content-based tags:" in change:
                    improvement_types["content_tags_added"] = (
                        improvement_types.get("content_tags_added", 0) + 1
                    )
                elif "Added metadata" in change:
                    improvement_types["metadata_extracted"] = (
                        improvement_types.get("metadata_extracted", 0) + 1
                    )
                elif "Added date" in change:
                    improvement_types["dates_populated"] = (
                        improvement_types.get("dates_populated", 0) + 1
                    )
                elif "Added required field" in change:
                    improvement_types["required_fields_added"] = (
                        improvement_types.get("required_fields_added", 0) + 1
                    )
                elif "Added description:" in change:
                    improvement_types["descriptions_added"] = (
                        improvement_types.get("descriptions_added", 0) + 1
                    )
                elif "Added category:" in change:
                    improvement_types["categories_added"] = (
                        improvement_types.get("categories_added", 0) + 1
                    )
                elif "Added ID:" in change:
                    improvement_types["ids_generated"] = (
                        improvement_types.get("ids_generated", 0) + 1
                    )
                elif "Added title:" in change:
                    improvement_types["titles_generated"] = (
                        improvement_types.get("titles_generated", 0) + 1
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

    def analyze_vault_enhancement_opportunities(
        self, files: list[MarkdownFile]
    ) -> dict[str, Any]:
        """Analyze the entire vault for enhancement opportunities."""
        analysis = {
            "total_files": len(files),
            "files_missing_required_fields": 0,
            "files_with_minimal_tags": 0,
            "files_without_descriptions": 0,
            "files_without_dates": 0,
            "potential_tag_suggestions": 0,
            "metadata_extraction_opportunities": 0,
            "tag_relationship_analysis": {},
        }

        # Analyze each file for enhancement opportunities
        for file in files:
            frontmatter_dict = file.frontmatter.model_dump(exclude_unset=True)

            # Check for missing required fields
            required_fields = ["title", "id", "tags", "published"]
            missing_required = any(
                field not in frontmatter_dict or not frontmatter_dict[field]
                for field in required_fields
            )
            if missing_required:
                analysis["files_missing_required_fields"] += 1

            # Check for minimal tags (less than 2)
            current_tags = frontmatter_dict.get("tags", [])
            if len(current_tags) < 2:
                analysis["files_with_minimal_tags"] += 1

            # Check for missing descriptions
            if not frontmatter_dict.get("description"):
                analysis["files_without_descriptions"] += 1

            # Check for missing dates
            if not frontmatter_dict.get("published") and not frontmatter_dict.get(
                "created"
            ):
                analysis["files_without_dates"] += 1

            # Count potential intelligent tag suggestions
            intelligent_tags = self.suggest_intelligent_tags(file)
            if intelligent_tags:
                analysis["potential_tag_suggestions"] += len(intelligent_tags)

            # Count metadata extraction opportunities
            extracted_metadata = self.extract_metadata_from_content(file)
            if extracted_metadata:
                analysis["metadata_extraction_opportunities"] += len(extracted_metadata)

        # Analyze tag relationships across the vault
        analysis["tag_relationship_analysis"] = self.analyze_tag_relationships(files)

        # Calculate enhancement priority scores
        analysis["enhancement_priority"] = {
            "high": analysis["files_missing_required_fields"],
            "medium": analysis["files_with_minimal_tags"]
            + analysis["files_without_descriptions"],
            "low": analysis["files_without_dates"],
        }

        return analysis

    def update_vault_tag_analysis(self, files: list[MarkdownFile]) -> VaultTagAnalysis:
        """Update vault tag analysis using the pattern manager."""
        return self.tag_pattern_manager.analyze_vault_tags(files)

    def get_tag_suggestions_with_confidence(
        self, file: MarkdownFile
    ) -> list[tuple[str, float]]:
        """Get tag suggestions with confidence scores."""
        return self.tag_pattern_manager.suggest_tags_for_content(file.content)

    def add_custom_tag_pattern(
        self,
        category: str,
        pattern_name: str,
        tag_name: str,
        keywords: list[str],
        description: str | None = None,
        confidence_weight: float = 1.0,
    ) -> None:
        """Add a custom tag pattern."""
        self.tag_pattern_manager.add_pattern(
            category, pattern_name, tag_name, keywords, description, confidence_weight
        )

    def export_tag_patterns_for_llm(self) -> dict[str, Any]:
        """Export tag patterns in LLM-friendly format."""
        return self.tag_pattern_manager.export_patterns_for_llm()

    def import_tag_patterns_from_llm(self, llm_data: dict[str, Any]) -> None:
        """Import tag patterns from LLM analysis."""
        self.tag_pattern_manager.import_patterns_from_analysis(llm_data)

    def get_vault_tag_statistics(self) -> dict[str, Any]:
        """Get comprehensive vault tag statistics."""
        if not self.tag_pattern_manager.vault_analysis:
            return {
                "error": "No vault analysis available. Run analyze_vault_tags first."
            }

        analysis = self.tag_pattern_manager.vault_analysis

        return {
            "summary": {
                "total_files": analysis.total_files,
                "total_tags": analysis.total_tags,
                "unique_tags": analysis.unique_tags,
                "average_tags_per_file": analysis.total_tags / analysis.total_files
                if analysis.total_files > 0
                else 0,
            },
            "most_common_tags": analysis.most_common_tags[:20],
            "orphaned_tags": analysis.orphaned_tags,
            "tag_coverage": {
                "files_with_tags": analysis.total_files
                - len([f for f in analysis.tag_frequency.values() if f == 0]),
                "files_without_tags": len(
                    [f for f in analysis.tag_frequency.values() if f == 0]
                ),
            },
        }

    def suggest_related_tags(
        self, tag: str, min_strength: float = 0.3
    ) -> list[tuple[str, float]]:
        """Suggest tags related to the given tag."""
        return self.tag_pattern_manager.get_related_tags(tag, min_strength)

    def search_tag_patterns(self, query: str) -> list[dict[str, Any]]:
        """Search for tag patterns by keyword."""
        patterns = self.tag_pattern_manager.search_patterns(query)
        return [
            {
                "tag_name": pattern.tag_name,
                "keywords": pattern.keywords,
                "category": pattern.category,
                "subcategory": pattern.subcategory,
                "description": pattern.description,
                "confidence_weight": pattern.confidence_weight,
                "usage_count": pattern.usage_count,
            }
            for pattern in patterns
        ]

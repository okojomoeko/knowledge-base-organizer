"""Content analysis service for detecting improvement opportunities."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from ..models import MarkdownFile


class ImprovementSuggestion(BaseModel):
    """Represents a suggested improvement to a markdown file."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    improvement_type: str  # "missing_tags", "missing_description", "filename_mismatch"
    field_name: str
    current_value: Any
    suggested_value: Any
    confidence: float  # 0.0 to 1.0
    reason: str


class DuplicateMatch(BaseModel):
    """Represents a potential duplicate file match."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    file_path: Path
    similarity_score: float  # 0.0 to 1.0
    match_type: str  # "title", "content", "filename", "combined"
    match_details: str
    confidence: float  # 0.0 to 1.0


class DuplicateDetectionResult(BaseModel):
    """Result of duplicate detection for a single file."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    file_path: Path
    potential_duplicates: list[DuplicateMatch]
    is_likely_duplicate: bool
    merge_suggestions: list[str]
    analysis_notes: list[str]


class ContentAnalysisResult(BaseModel):
    """Result of content analysis for a single file."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    file_path: Path
    improvements: list[ImprovementSuggestion]
    quality_score: float  # 0.0 to 1.0
    issues_found: int
    analysis_notes: list[str]


class ContentAnalysisService:
    """Service for analyzing content and detecting improvement opportunities."""

    def __init__(self) -> None:
        """Initialize content analysis service."""
        # Common tag patterns for different content types
        self.tag_patterns = {
            "programming": {
                "keywords": [
                    "code",
                    "programming",
                    "development",
                    "software",
                    "algorithm",
                    "function",
                    "class",
                    "method",
                ],
                "tags": ["programming", "development", "code"],
            },
            "japanese": {
                "keywords": ["日本語", "japanese", "katakana", "hiragana", "kanji"],
                "tags": ["japanese", "language"],
            },
            "architecture": {
                "keywords": [
                    "architecture",
                    "design",
                    "pattern",
                    "system",
                    "component",
                    "microservice",
                ],
                "tags": ["architecture", "design", "system"],
            },
            "book": {
                "keywords": ["book", "author", "chapter", "読書", "本"],
                "tags": ["book", "reading"],
            },
            "note": {
                "keywords": ["note", "memo", "idea", "thought"],
                "tags": ["note", "memo"],
            },
        }

    def analyze_file(self, file: MarkdownFile) -> ContentAnalysisResult:
        """Analyze a single file for improvement opportunities."""
        improvements = []
        analysis_notes = []

        # Check for missing required frontmatter fields (highest priority)
        required_field_suggestions = self._check_missing_required_fields(file)
        improvements.extend(required_field_suggestions)

        # Check for missing tags based on content
        tag_suggestions = self._analyze_content_for_tags(file)
        improvements.extend(tag_suggestions)

        # Check for missing description
        description_suggestion = self._check_missing_description(file)
        if description_suggestion:
            improvements.append(description_suggestion)

        # Check for missing category field
        category_suggestion = self._check_missing_category(file)
        if category_suggestion:
            improvements.append(category_suggestion)

        # Check filename-title consistency
        filename_suggestion = self._check_filename_title_consistency(file)
        if filename_suggestion:
            improvements.append(filename_suggestion)

        # Check for empty or minimal content
        content_suggestions = self._analyze_content_completeness(file)
        improvements.extend(content_suggestions)

        # Calculate quality score
        quality_score = self._calculate_quality_score(file, improvements)

        # Generate analysis notes
        if not improvements:
            analysis_notes.append("No improvements needed - file is well-organized")
        else:
            analysis_notes.append(f"Found {len(improvements)} potential improvements")

        return ContentAnalysisResult(
            file_path=file.path,
            improvements=improvements,
            quality_score=quality_score,
            issues_found=len(improvements),
            analysis_notes=analysis_notes,
        )

    def _analyze_content_for_tags(
        self, file: MarkdownFile
    ) -> list[ImprovementSuggestion]:
        """Analyze content to suggest missing tags."""
        suggestions = []
        content_lower = file.content.lower()
        current_tags = set(file.frontmatter.tags or [])

        # Find suggested tags based on content patterns
        suggested_tags = set()

        for category, pattern_info in self.tag_patterns.items():
            keywords = pattern_info["keywords"]
            category_tags = pattern_info["tags"]

            # Check if content contains keywords from this category
            keyword_matches = sum(1 for keyword in keywords if keyword in content_lower)

            if keyword_matches > 0:
                # Calculate confidence based on keyword density
                tag_confidence = min(0.9, keyword_matches * 0.3)

                # Suggest tags that aren't already present
                for tag in category_tags:
                    if tag not in current_tags:
                        reason = (
                            f"Content contains {keyword_matches} "
                            f"{category}-related keywords"
                        )
                        suggested_tags.add((tag, tag_confidence, reason))

        # Create improvement suggestions for missing tags
        if suggested_tags:
            new_tags = list(current_tags)
            reasons = []

            for tag, _, reason in suggested_tags:
                new_tags.append(tag)
                reasons.append(reason)

            # Remove duplicates while preserving order
            new_tags = list(dict.fromkeys(new_tags))

            max_confidence = max(conf for _, conf, _ in suggested_tags)
            suggestions.append(
                ImprovementSuggestion(
                    improvement_type="missing_tags",
                    field_name="tags",
                    current_value=list(current_tags),
                    suggested_value=new_tags,
                    confidence=max_confidence,
                    reason="; ".join(reasons),
                )
            )

        return suggestions

    def _check_missing_required_fields(
        self, file: MarkdownFile
    ) -> list[ImprovementSuggestion]:
        """Check for missing required frontmatter fields based on template."""
        suggestions = []

        # Define required fields based on new-fleeing-note template
        required_fields = {
            "title": "string",
            "aliases": "array",
            "tags": "array",
            "id": "string",
            "published": "string",
            "description": "string",
            "category": "array",
        }

        for field_name, field_type in required_fields.items():
            current_value = getattr(file.frontmatter, field_name, None)

            # Check if field is missing or empty
            is_missing = False
            suggested_value: Any = None

            if current_value is None:
                is_missing = True
            elif field_type == "array" and (
                not isinstance(current_value, list) or len(current_value) == 0
            ):
                is_missing = True
                suggested_value = []
            elif field_type == "string" and (
                not isinstance(current_value, str) or not current_value.strip()
            ):
                is_missing = True
                suggested_value = ""

            if is_missing:
                # Generate appropriate default value
                if field_name == "aliases":
                    suggested_value = (
                        [file.frontmatter.title] if file.frontmatter.title else []
                    )
                elif field_name == "tags":
                    suggested_value = []  # Will be filled by content analysis
                elif field_name == "category":
                    suggested_value = self._suggest_category_from_content(file.content)
                elif field_name == "description":
                    desc = self._generate_description_from_content(file.content)
                    suggested_value = desc if desc else ""
                elif field_name == "published":
                    # Use file modification date as fallback
                    try:
                        mod_time = file.path.stat().st_mtime
                        suggested_value = datetime.fromtimestamp(mod_time).strftime(
                            "%Y-%m-%d"
                        )
                    except Exception:
                        suggested_value = ""
                else:
                    suggested_value = "" if field_type == "string" else []

                suggestions.append(
                    ImprovementSuggestion(
                        improvement_type="missing_required_field",
                        field_name=field_name,
                        current_value=current_value,
                        suggested_value=suggested_value,
                        confidence=0.9,  # High confidence for required fields
                        reason=f"Required field '{field_name}' is missing or empty",
                    )
                )

        return suggestions

    def _check_missing_category(
        self, file: MarkdownFile
    ) -> ImprovementSuggestion | None:
        """Check if category field is missing and suggest based on content."""
        current_category = getattr(file.frontmatter, "category", None)

        if not current_category or (
            isinstance(current_category, list) and len(current_category) == 0
        ):
            # Suggest category based on content analysis
            suggested_category = self._suggest_category_from_content(file.content)

            if suggested_category:
                return ImprovementSuggestion(
                    improvement_type="missing_category",
                    field_name="category",
                    current_value=current_category,
                    suggested_value=suggested_category,
                    confidence=0.7,
                    reason=(
                        "Category field is missing, suggested based on content analysis"
                    ),
                )

        return None

    def _suggest_category_from_content(self, content: str) -> list[str]:
        """Suggest category based on content analysis."""
        content_lower = content.lower()
        suggested_categories = []

        # Category mapping based on content patterns
        category_patterns = {
            "technical": [
                "code",
                "programming",
                "development",
                "algorithm",
                "function",
                "class",
            ],
            "research": [
                "research",
                "study",
                "analysis",
                "investigation",
                "findings",
            ],
            "documentation": [
                "documentation",
                "guide",
                "tutorial",
                "how-to",
                "manual",
            ],
            "personal": ["diary", "personal", "reflection", "thought", "idea"],
            "book": ["book", "reading", "author", "chapter", "読書", "本"],
            "japanese": ["日本語", "japanese", "katakana", "hiragana", "kanji"],
        }

        for category, keywords in category_patterns.items():
            if any(keyword in content_lower for keyword in keywords):
                suggested_categories.append(category)

        return suggested_categories[:2]  # Limit to 2 categories

    def _check_missing_description(
        self, file: MarkdownFile
    ) -> ImprovementSuggestion | None:
        """Check if description field is missing or empty."""
        current_description = getattr(file.frontmatter, "description", None)

        if not current_description or (
            isinstance(current_description, str) and not current_description.strip()
        ):
            # Generate description from first paragraph
            suggested_description = self._generate_description_from_content(
                file.content
            )

            if suggested_description:
                return ImprovementSuggestion(
                    improvement_type="missing_description",
                    field_name="description",
                    current_value=current_description,
                    suggested_value=suggested_description,
                    confidence=0.7,
                    reason=(
                        "Description field is empty, generated from first paragraph"
                    ),
                )

        return None

    def _check_filename_title_consistency(
        self, file: MarkdownFile
    ) -> ImprovementSuggestion | None:
        """Check if filename and title are consistent."""
        if not file.frontmatter.title:
            return None

        filename = file.path.stem
        title = file.frontmatter.title

        # Skip files with timestamp-based names (like 20241116105142.md)
        if re.match(r"^\d{14}$", filename):
            return None

        # Check if filename and title are significantly different
        filename_normalized = self._normalize_for_comparison(filename)
        title_normalized = self._normalize_for_comparison(title)

        if filename_normalized != title_normalized:
            # Calculate similarity
            similarity = self._calculate_similarity(
                filename_normalized, title_normalized
            )

            if similarity < 0.5:  # Low similarity suggests inconsistency
                return ImprovementSuggestion(
                    improvement_type="filename_mismatch",
                    field_name="title",
                    current_value=title,
                    suggested_value=f"Consider renaming file to match title: '{title}'",
                    confidence=0.6,
                    reason=f"Filename '{filename}' doesn't match title '{title}'",
                )

        return None

    def _analyze_content_completeness(
        self, file: MarkdownFile
    ) -> list[ImprovementSuggestion]:
        """Analyze content completeness and suggest improvements."""
        suggestions = []
        content = file.content.strip()

        # Check for very short content
        if len(content) < 100:
            suggestions.append(
                ImprovementSuggestion(
                    improvement_type="incomplete_content",
                    field_name="content",
                    current_value=len(content),
                    suggested_value=(
                        f"Add more detailed content "
                        f"(current: {len(content)} characters)"
                    ),
                    confidence=0.8,
                    reason="Content is very short and may be incomplete",
                )
            )

        # Check for placeholder content
        placeholder_patterns = [
            r"TODO",
            r"FIXME",
            r"placeholder",
            r"coming soon",
            r"to be written",
            r"未完成",
            r"作成中",
        ]

        for pattern in placeholder_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                suggestions.append(
                    ImprovementSuggestion(
                        improvement_type="placeholder_content",
                        field_name="content",
                        current_value="Contains placeholder text",
                        suggested_value=(
                            "Replace placeholder content with actual information"
                        ),
                        confidence=0.9,
                        reason=f"Content contains placeholder text: '{pattern}'",
                    )
                )
                break

        return suggestions

    def _generate_description_from_content(self, content: str) -> str | None:
        """Generate a description from the first paragraph of content."""
        # Remove frontmatter and get first paragraph
        lines = content.split("\n")
        first_paragraph = ""

        for line in lines:
            stripped_line = line.strip()
            if not stripped_line:
                if first_paragraph:
                    break
                continue
            if stripped_line.startswith("#"):
                continue
            first_paragraph += stripped_line + " "
            if len(first_paragraph) > 200:
                break

        if first_paragraph:
            # Clean up and truncate
            description = first_paragraph.strip()
            if len(description) > 150:
                description = description[:147] + "..."
            return description

        return None

    def _normalize_for_comparison(self, text: str) -> str:
        """Normalize text for comparison (remove special chars, lowercase)."""
        # Remove special characters and normalize
        normalized = re.sub(r"[^\w\s]", "", text.lower())
        return re.sub(r"\s+", " ", normalized).strip()

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple similarity between two texts."""
        if not text1 or not text2:
            return 0.0

        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def _calculate_quality_score(
        self, _file: MarkdownFile, improvements: list[ImprovementSuggestion]
    ) -> float:
        """Calculate overall quality score for the file."""
        base_score = 1.0

        # Deduct points for each improvement needed
        for improvement in improvements:
            if improvement.improvement_type == "missing_required_field":
                base_score -= 0.25  # Heavy penalty for missing required fields
            elif improvement.improvement_type in (
                "missing_tags",
                "missing_description",
            ):
                base_score -= 0.15
            elif improvement.improvement_type in (
                "missing_category",
                "filename_mismatch",
            ):
                base_score -= 0.1
            elif improvement.improvement_type == "incomplete_content":
                base_score -= 0.3
            elif improvement.improvement_type == "placeholder_content":
                base_score -= 0.25

        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, base_score))

    def analyze_vault_content(
        self, files: list[MarkdownFile]
    ) -> list[ContentAnalysisResult]:
        """Analyze multiple files for improvement opportunities."""
        results = []

        for file in files:
            try:
                result = self.analyze_file(file)
                results.append(result)
            except Exception as e:
                # Create error result
                error_result = ContentAnalysisResult(
                    file_path=file.path,
                    improvements=[],
                    quality_score=0.0,
                    issues_found=1,
                    analysis_notes=[f"Analysis failed: {e!s}"],
                )
                results.append(error_result)

        return results

    def detect_duplicates(
        self, files: list[MarkdownFile], similarity_threshold: float = 0.7
    ) -> list[DuplicateDetectionResult]:
        """Detect potential duplicate files based on various similarity metrics."""
        results = []

        for i, file in enumerate(files):
            potential_duplicates = []

            # Compare with all other files
            for j, other_file in enumerate(files):
                if i >= j:  # Skip self and already compared pairs
                    continue

                duplicate_match = self._compare_files_for_duplicates(
                    file, other_file, similarity_threshold
                )

                if duplicate_match:
                    potential_duplicates.append(duplicate_match)

            # Create result for this file
            is_likely_duplicate = any(
                match.confidence > 0.8 for match in potential_duplicates
            )

            merge_suggestions = self._generate_merge_suggestions(
                file, potential_duplicates
            )

            analysis_notes = []
            if potential_duplicates:
                analysis_notes.append(
                    f"Found {len(potential_duplicates)} potential duplicate(s)"
                )
            else:
                analysis_notes.append("No duplicates detected")

            result = DuplicateDetectionResult(
                file_path=file.path,
                potential_duplicates=potential_duplicates,
                is_likely_duplicate=is_likely_duplicate,
                merge_suggestions=merge_suggestions,
                analysis_notes=analysis_notes,
            )
            results.append(result)

        return results

    def _compare_files_for_duplicates(
        self, file1: MarkdownFile, file2: MarkdownFile, threshold: float
    ) -> DuplicateMatch | None:
        """Compare files and return duplicate match if similarity is above threshold."""
        # Calculate different types of similarity
        title_similarity = self._calculate_title_similarity(file1, file2)
        content_similarity = self._calculate_content_similarity(file1, file2)
        filename_similarity = self._calculate_filename_similarity(file1, file2)

        # Determine the strongest match type and overall similarity
        similarities = {
            "title": title_similarity,
            "content": content_similarity,
            "filename": filename_similarity,
        }

        max_similarity = max(similarities.values())
        match_type = max(similarities, key=similarities.get)

        # Calculate combined similarity with weights
        combined_similarity = (
            title_similarity * 0.4
            + content_similarity * 0.4
            + filename_similarity * 0.2
        )

        # Use the higher of max individual similarity or combined similarity
        final_similarity = max(max_similarity, combined_similarity)

        if final_similarity >= threshold:
            # Generate match details
            match_details = self._generate_match_details(file1, file2, similarities)

            # Calculate confidence based on multiple factors
            confidence = self._calculate_duplicate_confidence(
                similarities, file1, file2
            )

            return DuplicateMatch(
                file_path=file2.path,
                similarity_score=final_similarity,
                match_type=match_type
                if max_similarity == final_similarity
                else "combined",
                match_details=match_details,
                confidence=confidence,
            )

        return None

    def _calculate_title_similarity(
        self, file1: MarkdownFile, file2: MarkdownFile
    ) -> float:
        """Calculate similarity between file titles."""
        title1 = getattr(file1.frontmatter, "title", "") or ""
        title2 = getattr(file2.frontmatter, "title", "") or ""

        if not title1 or not title2:
            return 0.0

        # Normalize titles for comparison
        norm_title1 = self._normalize_for_comparison(title1)
        norm_title2 = self._normalize_for_comparison(title2)

        return self._calculate_similarity(norm_title1, norm_title2)

    def _calculate_content_similarity(
        self, file1: MarkdownFile, file2: MarkdownFile
    ) -> float:
        """Calculate similarity between file contents."""
        # Extract main content (excluding frontmatter)
        content1 = self._extract_main_content(file1.content)
        content2 = self._extract_main_content(file2.content)

        if not content1 or not content2:
            return 0.0

        # For very short content, use exact matching
        if len(content1) < 100 and len(content2) < 100:
            return 1.0 if content1.strip() == content2.strip() else 0.0

        # Use word-based similarity for longer content
        return self._calculate_text_similarity(content1, content2)

    def _calculate_filename_similarity(
        self, file1: MarkdownFile, file2: MarkdownFile
    ) -> float:
        """Calculate similarity between filenames."""
        name1 = file1.path.stem
        name2 = file2.path.stem

        # Skip timestamp-based filenames
        if re.match(r"^\d{14}$", name1) or re.match(r"^\d{14}$", name2):
            return 0.0

        norm_name1 = self._normalize_for_comparison(name1)
        norm_name2 = self._normalize_for_comparison(name2)

        return self._calculate_similarity(norm_name1, norm_name2)

    def _extract_main_content(self, full_content: str) -> str:
        """Extract main content excluding frontmatter and headers."""
        lines = full_content.split("\n")
        content_lines = []

        for line in lines:
            stripped = line.strip()
            # Skip empty lines and headers
            if not stripped or stripped.startswith("#"):
                continue
            content_lines.append(stripped)

        return " ".join(content_lines)

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings using word overlap."""
        if not text1 or not text2:
            return 0.0

        # Normalize and tokenize
        words1 = set(self._normalize_for_comparison(text1).split())
        words2 = set(self._normalize_for_comparison(text2).split())

        if not words1 or not words2:
            return 0.0

        # Calculate Jaccard similarity
        intersection = words1.intersection(words2)
        union = words1.union(words2)

        jaccard_similarity = len(intersection) / len(union) if union else 0.0

        # Also calculate overlap coefficient (useful for different length texts)
        min_size = min(len(words1), len(words2))
        overlap_coefficient = len(intersection) / min_size if min_size > 0 else 0.0

        # Return the higher of the two measures
        return max(jaccard_similarity, overlap_coefficient)

    def _generate_match_details(
        self, file1: MarkdownFile, file2: MarkdownFile, similarities: dict[str, float]
    ) -> str:
        """Generate detailed description of why files are considered duplicates."""
        details = []

        if similarities["title"] > 0.7:
            title1 = getattr(file1.frontmatter, "title", "")
            title2 = getattr(file2.frontmatter, "title", "")
            details.append(f"Similar titles: '{title1}' vs '{title2}'")

        if similarities["filename"] > 0.7:
            details.append(
                f"Similar filenames: '{file1.path.stem}' vs '{file2.path.stem}'"
            )

        if similarities["content"] > 0.7:
            content_len1 = len(file1.content.strip())
            content_len2 = len(file2.content.strip())
            details.append(f"Similar content ({content_len1} vs {content_len2} chars)")

        return "; ".join(details) if details else "Multiple similarity factors"

    def _calculate_duplicate_confidence(
        self, similarities: dict[str, float], file1: MarkdownFile, file2: MarkdownFile
    ) -> float:
        """Calculate confidence that files are duplicates."""
        base_confidence = max(similarities.values())

        # Boost confidence if multiple similarity types are high
        high_similarities = sum(1 for sim in similarities.values() if sim > 0.7)
        if high_similarities >= 2:
            base_confidence = min(1.0, base_confidence + 0.1)

        # Boost confidence for very short files with high content similarity
        if similarities["content"] > 0.9:
            content1_len = len(file1.content.strip())
            content2_len = len(file2.content.strip())
            if content1_len < 200 and content2_len < 200:
                base_confidence = min(1.0, base_confidence + 0.1)

        # Reduce confidence if files are in different directories
        # (might be intentional organization)
        if file1.path.parent != file2.path.parent:
            base_confidence = max(0.0, base_confidence - 0.1)

        return base_confidence

    def _generate_merge_suggestions(
        self, file: MarkdownFile, duplicates: list[DuplicateMatch]
    ) -> list[str]:
        """Generate suggestions for merging duplicate files."""
        if not duplicates:
            return []

        suggestions = []

        # Find the highest confidence duplicate
        best_match = max(duplicates, key=lambda x: x.confidence)

        if best_match.confidence > 0.8:
            suggestions.append(
                f"Consider merging with {best_match.file_path.name} "
                f"(confidence: {best_match.confidence:.2f})"
            )

            # Suggest which file to keep based on various factors
            suggestions.extend(self._suggest_merge_strategy(file, best_match))

        if len(duplicates) > 1:
            suggestions.append(
                f"Multiple potential duplicates found - "
                f"review all {len(duplicates)} matches"
            )

        return suggestions

    def _suggest_merge_strategy(
        self, _file: MarkdownFile, duplicate_match: DuplicateMatch
    ) -> list[str]:
        """Suggest strategy for merging duplicate files."""
        suggestions = []

        # Note: We don't have access to the other file's content here
        # In a real implementation, we'd need to load it for comparison

        suggestions.append(
            "Keep the file with more complete content and better frontmatter"
        )

        if duplicate_match.match_type == "title":
            suggestions.append(
                "Files have similar titles - check if content is truly duplicate"
            )
        elif duplicate_match.match_type == "content":
            suggestions.append(
                "Files have similar content - merge unique information from both"
            )
        elif duplicate_match.match_type == "filename":
            suggestions.append(
                "Files have similar names - verify if they serve different purposes"
            )

        return suggestions

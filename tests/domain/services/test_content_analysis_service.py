"""Tests for ContentAnalysisService."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from knowledge_base_organizer.domain.models import Frontmatter, MarkdownFile
from knowledge_base_organizer.domain.services.content_analysis_service import (
    ContentAnalysisResult,
    ContentAnalysisService,
    ImprovementSuggestion,
)


class TestContentAnalysisService:
    """Test cases for ContentAnalysisService."""

    @pytest.fixture
    def service(self):
        """Create ContentAnalysisService instance."""
        return ContentAnalysisService()

    @pytest.fixture
    def sample_file(self):
        """Create a sample MarkdownFile for testing."""
        frontmatter = Frontmatter(
            title="Test File",
            aliases=["test"],
            tags=["sample"],
            id="20241116105142",
        )

        # Mock the path to avoid file system dependencies
        mock_path = Mock(spec=Path)
        mock_path.stem = "20241116105142"
        mock_path.stat.return_value.st_mtime = 1700000000.0

        return MarkdownFile(
            path=mock_path,
            frontmatter=frontmatter,
            content=(
                "# Test Content\n\nThis is a test file with some programming content."
            ),
        )

    def test_analyze_file_basic(self, service, sample_file):
        """Test basic file analysis."""
        result = service.analyze_file(sample_file)

        assert isinstance(result, ContentAnalysisResult)
        assert result.file_path == sample_file.path
        assert isinstance(result.improvements, list)
        assert isinstance(result.quality_score, float)
        assert 0.0 <= result.quality_score <= 1.0
        assert result.issues_found >= 0

    def test_analyze_content_for_tags_programming(self, service):
        """Test tag suggestion for programming content."""
        frontmatter = Frontmatter(title="Test", tags=[])
        mock_path = Mock(spec=Path)

        file = MarkdownFile(
            path=mock_path,
            frontmatter=frontmatter,
            content="This file contains code and programming algorithms.",
        )

        suggestions = service._analyze_content_for_tags(file)

        assert len(suggestions) > 0
        suggestion = suggestions[0]
        assert suggestion.improvement_type == "missing_tags"
        assert suggestion.field_name == "tags"
        assert (
            "programming" in suggestion.suggested_value
            or "development" in suggestion.suggested_value
        )

    def test_analyze_content_for_tags_japanese(self, service):
        """Test tag suggestion for Japanese content."""
        frontmatter = Frontmatter(title="Test", tags=[])
        mock_path = Mock(spec=Path)

        file = MarkdownFile(
            path=mock_path,
            frontmatter=frontmatter,
            content="This file discusses 日本語 and katakana characters.",
        )

        suggestions = service._analyze_content_for_tags(file)

        assert len(suggestions) > 0
        suggestion = suggestions[0]
        assert "japanese" in suggestion.suggested_value

    def test_check_missing_required_fields(self, service):
        """Test detection of missing required fields."""
        # Create file with minimal frontmatter
        frontmatter = Frontmatter(title="Test")
        mock_path = Mock(spec=Path)
        mock_path.stat.return_value.st_mtime = 1700000000.0

        file = MarkdownFile(
            path=mock_path,
            frontmatter=frontmatter,
            content="Test content",
        )

        suggestions = service._check_missing_required_fields(file)

        # Should suggest missing fields like aliases, tags, id, etc.
        assert len(suggestions) > 0

        # Check that we get suggestions for expected missing fields
        field_names = [s.field_name for s in suggestions]
        assert "aliases" in field_names
        assert "tags" in field_names
        assert "id" in field_names

    def test_check_missing_description(self, service):
        """Test detection of missing description field."""
        frontmatter = Frontmatter(title="Test")
        mock_path = Mock(spec=Path)

        file = MarkdownFile(
            path=mock_path,
            frontmatter=frontmatter,
            content=(
                "# Test\n\n"
                "This is a detailed description of the content "
                "that should be extracted."
            ),
        )

        suggestion = service._check_missing_description(file)

        assert suggestion is not None
        assert suggestion.improvement_type == "missing_description"
        assert suggestion.field_name == "description"
        assert "detailed description" in suggestion.suggested_value

    def test_suggest_category_from_content(self, service):
        """Test category suggestion based on content."""
        # Test technical content
        categories = service._suggest_category_from_content(
            "This is about programming and code development."
        )
        assert "technical" in categories

        # Test book content
        categories = service._suggest_category_from_content(
            "This book by the author discusses reading strategies."
        )
        assert "book" in categories

        # Test Japanese content
        categories = service._suggest_category_from_content(
            "Learning 日本語 and japanese language."
        )
        assert "japanese" in categories

    def test_filename_title_consistency(self, service):
        """Test filename-title consistency checking."""
        frontmatter = Frontmatter(title="Completely Different Title")
        mock_path = Mock(spec=Path)
        mock_path.stem = "test-file-name"

        file = MarkdownFile(
            path=mock_path,
            frontmatter=frontmatter,
            content="Test content",
        )

        suggestion = service._check_filename_title_consistency(file)

        assert suggestion is not None
        assert suggestion.improvement_type == "filename_mismatch"
        assert "test-file-name" in suggestion.reason
        assert "Completely Different Title" in suggestion.reason

    def test_filename_title_consistency_timestamp_skip(self, service):
        """Test that timestamp-based filenames are skipped."""
        frontmatter = Frontmatter(title="Some Title")
        mock_path = Mock(spec=Path)
        mock_path.stem = "20241116105142"  # 14-digit timestamp

        file = MarkdownFile(
            path=mock_path,
            frontmatter=frontmatter,
            content="Test content",
        )

        suggestion = service._check_filename_title_consistency(file)

        # Should be None because timestamp filenames are skipped
        assert suggestion is None

    def test_analyze_content_completeness_short(self, service):
        """Test detection of short content."""
        frontmatter = Frontmatter(title="Test")
        mock_path = Mock(spec=Path)

        file = MarkdownFile(
            path=mock_path,
            frontmatter=frontmatter,
            content="Short",  # Very short content
        )

        suggestions = service._analyze_content_completeness(file)

        assert len(suggestions) > 0
        suggestion = suggestions[0]
        assert suggestion.improvement_type == "incomplete_content"
        assert "short" in suggestion.reason.lower()

    def test_analyze_content_completeness_placeholder(self, service):
        """Test detection of placeholder content."""
        frontmatter = Frontmatter(title="Test")
        mock_path = Mock(spec=Path)

        # Make content long enough to avoid incomplete_content flag
        long_content = "This is TODO content that needs to be written. " * 5

        file = MarkdownFile(
            path=mock_path,
            frontmatter=frontmatter,
            content=long_content,
        )

        suggestions = service._analyze_content_completeness(file)

        assert len(suggestions) > 0
        # Find the placeholder suggestion (might not be first if there are multiple)
        placeholder_suggestion = None
        for suggestion in suggestions:
            if suggestion.improvement_type == "placeholder_content":
                placeholder_suggestion = suggestion
                break

        assert placeholder_suggestion is not None
        assert "placeholder" in placeholder_suggestion.reason.lower()

    def test_calculate_quality_score(self, service, sample_file):
        """Test quality score calculation."""
        # Test with no improvements (high score)
        score = service._calculate_quality_score(sample_file, [])
        assert score == 1.0

        # Test with some improvements (lower score)
        improvements = [
            ImprovementSuggestion(
                improvement_type="missing_required_field",
                field_name="description",
                current_value=None,
                suggested_value="Test description",
                confidence=0.9,
                reason="Missing required field",
            ),
            ImprovementSuggestion(
                improvement_type="missing_tags",
                field_name="tags",
                current_value=[],
                suggested_value=["test"],
                confidence=0.8,
                reason="Missing tags",
            ),
        ]

        score = service._calculate_quality_score(sample_file, improvements)
        assert score < 1.0
        assert score > 0.0

    def test_analyze_vault_content(self, service):
        """Test analyzing multiple files."""
        # Create multiple test files
        files = []
        for i in range(3):
            frontmatter = Frontmatter(title=f"Test {i}")
            mock_path = Mock(spec=Path)
            mock_path.stem = f"test-{i}"

            file = MarkdownFile(
                path=mock_path,
                frontmatter=frontmatter,
                content=f"Test content {i}",
            )
            files.append(file)

        results = service.analyze_vault_content(files)

        assert len(results) == 3
        for result in results:
            assert isinstance(result, ContentAnalysisResult)
            assert isinstance(result.quality_score, float)

    def test_generate_description_from_content(self, service):
        """Test description generation from content."""
        content = """# Title

This is the first paragraph that should be extracted as description.
It contains multiple sentences and should be truncated appropriately.

This is the second paragraph that should not be included.
"""

        description = service._generate_description_from_content(content)

        assert description is not None
        assert "first paragraph" in description
        assert "second paragraph" not in description
        assert len(description) <= 150  # Should be truncated

    def test_normalize_for_comparison(self, service):
        """Test text normalization for comparison."""
        text = "Test-File_Name with Special!@# Characters"
        normalized = service._normalize_for_comparison(text)

        # The regex [^\w\s] keeps word characters (including underscores) and spaces
        assert normalized == "testfile_name with special characters"
        assert " " in normalized  # Spaces should be preserved
        assert "!" not in normalized  # Special chars should be removed
        assert "_" in normalized  # Underscores are word characters, so preserved

    def test_calculate_similarity(self, service):
        """Test similarity calculation between texts."""
        # Identical texts
        similarity = service._calculate_similarity("test file", "test file")
        assert similarity == 1.0

        # Completely different texts
        similarity = service._calculate_similarity("test file", "other content")
        assert similarity == 0.0

        # Partially similar texts
        similarity = service._calculate_similarity("test file name", "test file")
        assert 0.0 < similarity < 1.0

    def test_error_handling_in_vault_analysis(self, service):
        """Test error handling when analyzing files."""
        # Create a file that will cause an error
        mock_path = Mock(spec=Path)
        mock_path.stem = "test"

        # Create file with invalid frontmatter that might cause issues
        file = MarkdownFile(
            path=mock_path,
            frontmatter=Frontmatter(),
            content="Test content",
        )

        # Mock the analyze_file method to raise an exception
        original_analyze = service.analyze_file

        def mock_analyze(f):
            if f == file:
                raise ValueError("Test error")
            return original_analyze(f)

        service.analyze_file = mock_analyze

        results = service.analyze_vault_content([file])

        assert len(results) == 1
        result = results[0]
        assert result.quality_score == 0.0
        assert result.issues_found == 1
        assert "Analysis failed" in result.analysis_notes[0]

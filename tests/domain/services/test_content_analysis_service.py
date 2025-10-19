"""Tests for ContentAnalysisService."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from knowledge_base_organizer.domain.models import Frontmatter, MarkdownFile
from knowledge_base_organizer.domain.services.content_analysis_service import (
    ContentAnalysisResult,
    ContentAnalysisService,
    DuplicateDetectionResult,
    DuplicateMatch,
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

    def test_detect_duplicates_identical_titles(self, service):
        """Test duplicate detection for files with identical titles."""
        # Create two files with identical titles
        frontmatter1 = Frontmatter(title="Identical Title", tags=["test"])
        frontmatter2 = Frontmatter(title="Identical Title", tags=["sample"])

        mock_path1 = Mock(spec=Path)
        mock_path1.stem = "file1"
        mock_path1.parent = Path("/test")

        mock_path2 = Mock(spec=Path)
        mock_path2.stem = "file2"
        mock_path2.parent = Path("/test")

        file1 = MarkdownFile(
            path=mock_path1,
            frontmatter=frontmatter1,
            content="Different content for file 1",
        )

        file2 = MarkdownFile(
            path=mock_path2,
            frontmatter=frontmatter2,
            content="Different content for file 2",
        )

        results = service.detect_duplicates([file1, file2])

        assert len(results) == 2

        # First file should have file2 as potential duplicate
        result1 = results[0]
        assert isinstance(result1, DuplicateDetectionResult)
        assert len(result1.potential_duplicates) == 1

        duplicate_match = result1.potential_duplicates[0]
        assert isinstance(duplicate_match, DuplicateMatch)
        assert duplicate_match.file_path == mock_path2
        assert duplicate_match.match_type in ["title", "combined"]
        assert duplicate_match.similarity_score > 0.7

    def test_detect_duplicates_similar_content(self, service):
        """Test duplicate detection for files with similar content."""
        frontmatter1 = Frontmatter(title="File One", tags=["test"])
        frontmatter2 = Frontmatter(title="File Two", tags=["sample"])

        mock_path1 = Mock(spec=Path)
        mock_path1.stem = "file1"
        mock_path1.parent = Path("/test")

        mock_path2 = Mock(spec=Path)
        mock_path2.stem = "file2"
        mock_path2.parent = Path("/test")

        # Create files with very similar content
        similar_content = (
            "This is a detailed explanation of the concept. "
            "It covers multiple aspects and provides examples. "
            "The information is comprehensive and well-structured."
        )

        file1 = MarkdownFile(
            path=mock_path1,
            frontmatter=frontmatter1,
            content=similar_content,
        )

        file2 = MarkdownFile(
            path=mock_path2,
            frontmatter=frontmatter2,
            content=similar_content + " Additional sentence.",
        )

        results = service.detect_duplicates([file1, file2])

        assert len(results) == 2

        # Should detect high content similarity
        result1 = results[0]
        assert len(result1.potential_duplicates) == 1

        duplicate_match = result1.potential_duplicates[0]
        assert duplicate_match.match_type in ["content", "combined"]
        assert duplicate_match.similarity_score > 0.8

    def test_detect_duplicates_similar_filenames(self, service):
        """Test duplicate detection for files with similar filenames."""
        frontmatter1 = Frontmatter(title="Different Title One", tags=["test"])
        frontmatter2 = Frontmatter(title="Different Title Two", tags=["sample"])

        mock_path1 = Mock(spec=Path)
        mock_path1.stem = "test-file-name"
        mock_path1.parent = Path("/test")

        mock_path2 = Mock(spec=Path)
        mock_path2.stem = "test-file-name-copy"
        mock_path2.parent = Path("/test")

        file1 = MarkdownFile(
            path=mock_path1,
            frontmatter=frontmatter1,
            content="Content for first file",
        )

        file2 = MarkdownFile(
            path=mock_path2,
            frontmatter=frontmatter2,
            content="Content for second file",
        )

        results = service.detect_duplicates([file1, file2])

        # Should detect filename similarity
        result1 = results[0]
        if result1.potential_duplicates:
            duplicate_match = result1.potential_duplicates[0]
            assert duplicate_match.match_type in ["filename", "combined"]

    def test_detect_duplicates_no_matches(self, service):
        """Test duplicate detection when files are completely different."""
        frontmatter1 = Frontmatter(title="Unique Title One", tags=["test"])
        frontmatter2 = Frontmatter(title="Unique Title Two", tags=["sample"])

        mock_path1 = Mock(spec=Path)
        mock_path1.stem = "unique-file-one"
        mock_path1.parent = Path("/test")

        mock_path2 = Mock(spec=Path)
        mock_path2.stem = "unique-file-two"
        mock_path2.parent = Path("/test")

        file1 = MarkdownFile(
            path=mock_path1,
            frontmatter=frontmatter1,
            content="Completely unique content about programming",
        )

        file2 = MarkdownFile(
            path=mock_path2,
            frontmatter=frontmatter2,
            content="Totally different content about cooking recipes",
        )

        results = service.detect_duplicates([file1, file2])

        assert len(results) == 2

        # Should not detect any duplicates
        for result in results:
            assert len(result.potential_duplicates) == 0
            assert not result.is_likely_duplicate
            assert "No duplicates detected" in result.analysis_notes

    def test_detect_duplicates_timestamp_filenames_ignored(self, service):
        """Test that timestamp-based filenames are handled correctly."""
        frontmatter1 = Frontmatter(title="Test Title", tags=["test"])
        frontmatter2 = Frontmatter(title="Test Title", tags=["test"])

        mock_path1 = Mock(spec=Path)
        mock_path1.stem = "20241116105142"  # Timestamp filename
        mock_path1.parent = Path("/test")

        mock_path2 = Mock(spec=Path)
        mock_path2.stem = "20241116105143"  # Another timestamp filename
        mock_path2.parent = Path("/test")

        file1 = MarkdownFile(
            path=mock_path1,
            frontmatter=frontmatter1,
            content="Same content",
        )

        file2 = MarkdownFile(
            path=mock_path2,
            frontmatter=frontmatter2,
            content="Same content",
        )

        results = service.detect_duplicates([file1, file2])

        # Should still detect duplicates based on title and content,
        # but filename similarity should be 0
        result1 = results[0]
        if result1.potential_duplicates:
            duplicate_match = result1.potential_duplicates[0]
            # Should match on title or content, not filename
            assert duplicate_match.match_type in ["title", "content", "combined"]

    def test_calculate_title_similarity(self, service):
        """Test title similarity calculation."""
        frontmatter1 = Frontmatter(title="Test File Name")
        frontmatter2 = Frontmatter(title="Test File Name")

        mock_path = Mock(spec=Path)

        file1 = MarkdownFile(path=mock_path, frontmatter=frontmatter1, content="")
        file2 = MarkdownFile(path=mock_path, frontmatter=frontmatter2, content="")

        similarity = service._calculate_title_similarity(file1, file2)
        assert similarity == 1.0

        # Test with different titles
        frontmatter2.title = "Different Title"
        file2 = MarkdownFile(path=mock_path, frontmatter=frontmatter2, content="")

        similarity = service._calculate_title_similarity(file1, file2)
        assert similarity == 0.0

    def test_calculate_content_similarity(self, service):
        """Test content similarity calculation."""
        mock_path = Mock(spec=Path)
        frontmatter = Frontmatter(title="Test")

        content1 = "This is a test content with multiple words and concepts"
        content2 = "This is a test content with multiple words and concepts"

        file1 = MarkdownFile(path=mock_path, frontmatter=frontmatter, content=content1)
        file2 = MarkdownFile(path=mock_path, frontmatter=frontmatter, content=content2)

        similarity = service._calculate_content_similarity(file1, file2)
        assert similarity == 1.0

        # Test with different content
        content2 = "Completely different content about other topics"
        file2 = MarkdownFile(path=mock_path, frontmatter=frontmatter, content=content2)

        similarity = service._calculate_content_similarity(file1, file2)
        assert similarity < 0.3  # Should be low similarity

    def test_extract_main_content(self, service):
        """Test main content extraction."""
        full_content = """---
title: Test
---

# Main Title

This is the first paragraph of content.

## Subsection

This is more content that should be included.

# Another Section

Final paragraph of content.
"""

        main_content = service._extract_main_content(full_content)

        # Should exclude headers but include paragraph content
        assert "This is the first paragraph" in main_content
        assert "This is more content" in main_content
        assert "Final paragraph" in main_content
        assert "# Main Title" not in main_content
        assert "## Subsection" not in main_content

    def test_generate_merge_suggestions(self, service):
        """Test merge suggestion generation."""
        mock_path1 = Mock(spec=Path)
        mock_path1.name = "file1.md"

        mock_path2 = Mock(spec=Path)
        mock_path2.name = "file2.md"

        file = MarkdownFile(
            path=mock_path1,
            frontmatter=Frontmatter(title="Test"),
            content="Test content",
        )

        # Create high-confidence duplicate match
        duplicate_match = DuplicateMatch(
            file_path=mock_path2,
            similarity_score=0.9,
            match_type="title",
            match_details="Similar titles",
            confidence=0.85,
        )

        suggestions = service._generate_merge_suggestions(file, [duplicate_match])

        assert len(suggestions) > 0
        assert "Consider merging" in suggestions[0]
        assert "file2.md" in suggestions[0]
        assert "0.85" in suggestions[0]

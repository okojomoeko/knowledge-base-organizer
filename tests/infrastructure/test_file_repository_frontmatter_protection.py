"""Tests for FileRepository frontmatter protection functionality."""

import tempfile
from pathlib import Path

import pytest

from knowledge_base_organizer.domain.models import Frontmatter, MarkdownFile
from knowledge_base_organizer.infrastructure.config import ProcessingConfig
from knowledge_base_organizer.infrastructure.file_repository import FileRepository


class TestFileRepositoryFrontmatterProtection:
    """Test cases for frontmatter protection in FileRepository."""

    @pytest.fixture
    def config(self):
        """Processing configuration for testing."""
        return ProcessingConfig.get_default_config()

    @pytest.fixture
    def file_repository(self, config):
        """FileRepository instance for testing."""
        return FileRepository(config)

    @pytest.fixture
    def temp_file_with_frontmatter(self):
        """Create a temporary file with specific frontmatter formatting."""
        temp_dir = tempfile.mkdtemp()
        file_path = Path(temp_dir) / "test.md"

        # Content with specific formatting that should be preserved
        content = """---
title: Test File
image: "../../assets/images/svg/undraw/undraw_scrum_board.svg"
tags: [tag1,tag2]
id: 20240913221802
publish: false
---

# Test Content

This is test content.
"""

        file_path.write_text(content, encoding="utf-8")
        return file_path

    def test_preserve_frontmatter_formatting(
        self, file_repository, temp_file_with_frontmatter
    ):
        """Test that frontmatter formatting is preserved when preserve_frontmatter=True."""
        # Load the file
        markdown_file = file_repository.load_file(temp_file_with_frontmatter)

        # Store original content
        original_content = temp_file_with_frontmatter.read_text(encoding="utf-8")
        original_frontmatter = original_content.split("---\n")[1]

        # Modify the body content
        markdown_file.content = "# Modified Content\n\nThis content was changed."

        # Save with frontmatter protection
        file_repository.save_file(
            markdown_file, backup=False, preserve_frontmatter=True
        )

        # Read the saved content
        saved_content = temp_file_with_frontmatter.read_text(encoding="utf-8")
        saved_frontmatter = saved_content.split("---\n")[1]

        # Verify frontmatter formatting is preserved
        assert original_frontmatter == saved_frontmatter, (
            f"Frontmatter formatting was changed:\n"
            f"Original:\n{original_frontmatter}\n"
            f"Saved:\n{saved_frontmatter}"
        )

        # Verify specific formatting elements are preserved
        assert (
            'image: "../../assets/images/svg/undraw/undraw_scrum_board.svg"'
            in saved_content
        )
        assert "tags: [tag1,tag2]" in saved_content
        assert "id: 20240913221802" in saved_content

        # Verify body content was updated
        assert "# Modified Content" in saved_content
        assert "This content was changed." in saved_content

    def test_normal_save_behavior(self, file_repository, temp_file_with_frontmatter):
        """Test that normal save behavior still works when preserve_frontmatter=False."""
        # Load the file
        markdown_file = file_repository.load_file(temp_file_with_frontmatter)

        # Modify the body content
        markdown_file.content = "# Modified Content\n\nThis content was changed."

        # Save without frontmatter protection (default behavior)
        file_repository.save_file(
            markdown_file, backup=False, preserve_frontmatter=False
        )

        # Read the saved content
        saved_content = temp_file_with_frontmatter.read_text(encoding="utf-8")

        # Verify content was saved (formatting may change)
        assert "# Modified Content" in saved_content
        assert "This content was changed." in saved_content
        assert "title: Test File" in saved_content

    def test_preserve_frontmatter_with_no_original_frontmatter(self, file_repository):
        """Test preserve_frontmatter behavior when original file has no frontmatter."""
        temp_dir = tempfile.mkdtemp()
        file_path = Path(temp_dir) / "no_frontmatter.md"

        # Content without frontmatter
        content = "# Test Content\n\nThis is test content."
        file_path.write_text(content, encoding="utf-8")

        # Create MarkdownFile with frontmatter
        markdown_file = MarkdownFile(
            path=file_path,
            file_id="20250123000001",
            frontmatter=Frontmatter(
                title="Added Title",
                id="20250123000001",
            ),
            content="# Modified Content\n\nThis content was changed.",
        )

        # Save with frontmatter protection
        file_repository.save_file(
            markdown_file, backup=False, preserve_frontmatter=True
        )

        # Read the saved content
        saved_content = file_path.read_text(encoding="utf-8")

        # Should just return the content since there was no original frontmatter
        assert "# Modified Content" in saved_content
        assert "This content was changed." in saved_content

    def test_preserve_frontmatter_fallback_on_error(
        self, file_repository, temp_file_with_frontmatter
    ):
        """Test that preserve_frontmatter falls back to normal behavior on error."""
        # Load the file
        markdown_file = file_repository.load_file(temp_file_with_frontmatter)

        # Delete the original file to cause an error in preserve_frontmatter
        temp_file_with_frontmatter.unlink()

        # Modify the body content
        markdown_file.content = "# Modified Content\n\nThis content was changed."

        # Save with frontmatter protection (should fallback to normal behavior)
        file_repository.save_file(
            markdown_file, backup=False, preserve_frontmatter=True
        )

        # Read the saved content
        saved_content = temp_file_with_frontmatter.read_text(encoding="utf-8")

        # Should have saved with normal behavior as fallback
        assert "# Modified Content" in saved_content
        assert "This content was changed." in saved_content
        assert "title: Test File" in saved_content

"""
Tests for the index command implementation.

Tests the vector indexing functionality including:
- Basic indexing workflow
- Error handling
- Configuration options
- Output formatting
"""

from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from knowledge_base_organizer.cli.index_command import index_command
from knowledge_base_organizer.domain.services.ai_services import AIServiceError


@pytest.fixture
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def index_app():
    """Create a Typer app with the index command for testing."""
    app = typer.Typer()
    app.command()(index_command)
    return app


@pytest.fixture
def temp_vault(tmp_path):
    """Create a temporary vault with test files."""
    vault_path = tmp_path / "test_vault"
    vault_path.mkdir()

    # Create test markdown files
    (vault_path / "note1.md").write_text("""---
title: Test Note 1
tags: [test, sample]
---
# Test Note 1

This is a test note with some content.
""")

    (vault_path / "note2.md").write_text("""---
title: Test Note 2
tags: [test, example]
---
# Test Note 2

Another test note with different content.
""")

    return vault_path


class TestIndexCommand:
    """Test cases for the index command."""

    def test_index_command_help(self, runner, index_app):
        """Test that the index command shows help correctly."""
        result = runner.invoke(index_app, ["--help"])
        assert result.exit_code == 0
        assert "Create vector embeddings index" in result.output

    def test_index_command_nonexistent_vault(self, runner, index_app):
        """Test index command with non-existent vault path."""
        result = runner.invoke(index_app, ["/nonexistent/path"])
        assert result.exit_code == 1
        assert "Vault path does not exist" in result.output

    @patch("knowledge_base_organizer.cli.index_command.create_di_container")
    def test_index_command_ai_service_error(
        self, mock_di_container, runner, index_app, temp_vault
    ):
        """Test index command when AI services are not available."""
        # Setup mock to raise AIServiceError
        mock_di_container.side_effect = AIServiceError("Ollama not available")

        # Run the command
        result = runner.invoke(index_app, [str(temp_vault)])

        # Verify error handling
        assert result.exit_code == 1
        assert "AI service error" in result.output

    def test_prepare_content_for_embedding(self):
        """Test content preparation for embedding."""
        from knowledge_base_organizer.cli.index_command import (
            _prepare_content_for_embedding,
        )

        # Mock file object
        mock_file = MagicMock()
        mock_file.frontmatter = {"title": "Test Title", "tags": ["tag1", "tag2"]}
        mock_file.content = """---
title: Test Title
tags: [tag1, tag2]
---
# Test Title

This is the main content of the file.
"""

        result = _prepare_content_for_embedding(mock_file)

        # Verify content preparation
        assert "Title: Test Title" in result
        assert "Tags: tag1, tag2" in result
        assert "This is the main content" in result

    def test_prepare_content_for_embedding_no_frontmatter(self):
        """Test content preparation when no frontmatter exists."""
        from knowledge_base_organizer.cli.index_command import (
            _prepare_content_for_embedding,
        )

        # Mock file object without frontmatter
        mock_file = MagicMock()
        mock_file.frontmatter = {}
        mock_file.content = "Just plain content without frontmatter."

        result = _prepare_content_for_embedding(mock_file)

        # Verify content preparation
        assert "Just plain content without frontmatter." in result
        assert "Title:" not in result
        assert "Tags:" not in result

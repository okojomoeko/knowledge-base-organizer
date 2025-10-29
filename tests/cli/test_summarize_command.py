"""Tests for summarize command."""

from unittest.mock import Mock, patch

import click
import pytest
from typer.testing import CliRunner

from knowledge_base_organizer.cli.summarize_command import summarize_command
from knowledge_base_organizer.domain.models import Frontmatter, MarkdownFile


class TestSummarizeCommand:
    """Test cases for summarize command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_summarize_command_success(self, tmp_path):
        """Test successful summarization of a markdown file."""
        # Create test markdown file
        test_file = tmp_path / "test.md"
        test_content = """---
title: Test Note
tags: [test, example]
---

# Test Note

This is a test note with some content that should be summarized.
It contains multiple paragraphs and various information that the AI
should be able to condense into a concise summary.

## Section 1
Some detailed information here.

## Section 2
More content to summarize.
"""
        test_file.write_text(test_content)

        # Mock the LLM service
        mock_llm_service = Mock()
        mock_llm_service.summarize_content.return_value = (
            "This is a test note about examples with detailed sections."
        )

        # Mock the file repository and markdown file
        mock_markdown_file = MarkdownFile(
            path=test_file,
            frontmatter=Frontmatter(title="Test Note", tags=["test", "example"]),
            content=test_content,
        )

        with (
            patch(
                "knowledge_base_organizer.cli.summarize_command.OllamaLLMService"
            ) as mock_llm_class,
            patch(
                "knowledge_base_organizer.cli.summarize_command.FileRepository"
            ) as mock_file_repo_class,
        ):
            # Setup mocks
            mock_llm_class.return_value = mock_llm_service
            mock_file_repo = Mock()
            mock_file_repo.load_file.return_value = mock_markdown_file
            mock_file_repo_class.return_value = mock_file_repo

            # Run the command
            summarize_command(
                file_path=test_file, max_length=200, output_file=None, verbose=False
            )

            # Verify LLM service was called correctly
            mock_llm_service.summarize_content.assert_called_once_with(
                test_content, max_length=200
            )

    def test_summarize_command_with_output_file(self, tmp_path):
        """Test summarization with output file."""
        # Create test markdown file
        test_file = tmp_path / "test.md"
        test_content = "# Test\nSome content to summarize."
        test_file.write_text(test_content)

        # Create output file path
        output_file = tmp_path / "summary.md"

        # Mock the LLM service
        mock_llm_service = Mock()
        mock_llm_service.summarize_content.return_value = "Test summary content."

        # Mock the file repository and markdown file
        mock_markdown_file = MarkdownFile(
            path=test_file, frontmatter=Frontmatter(title="Test"), content=test_content
        )

        with (
            patch(
                "knowledge_base_organizer.cli.summarize_command.OllamaLLMService"
            ) as mock_llm_class,
            patch(
                "knowledge_base_organizer.cli.summarize_command.FileRepository"
            ) as mock_file_repo_class,
        ):
            # Setup mocks
            mock_llm_class.return_value = mock_llm_service
            mock_file_repo = Mock()
            mock_file_repo.load_file.return_value = mock_markdown_file
            mock_file_repo_class.return_value = mock_file_repo

            # Run the command
            summarize_command(
                file_path=test_file,
                max_length=100,
                output_file=output_file,
                verbose=True,
            )

            # Verify output file was created
            assert output_file.exists()
            content = output_file.read_text()
            assert "Summary of test.md" in content
            assert "Test summary content." in content

    def test_summarize_command_file_not_exists(self, tmp_path):
        """Test error handling when file doesn't exist."""
        non_existent_file = tmp_path / "nonexistent.md"

        with pytest.raises(click.exceptions.Exit):
            summarize_command(
                file_path=non_existent_file,
                max_length=200,
                output_file=None,
                verbose=False,
            )

    def test_summarize_command_non_markdown_file(self, tmp_path):
        """Test error handling when file is not markdown."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Some text content")

        with pytest.raises(click.exceptions.Exit):
            summarize_command(
                file_path=test_file,
                max_length=200,
                output_file=None,
                verbose=False,
            )

    def test_summarize_command_llm_service_failure(self, tmp_path):
        """Test error handling when LLM service fails to initialize."""
        # Create test markdown file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test\nContent")

        with patch(
            "knowledge_base_organizer.cli.summarize_command.OllamaLLMService"
        ) as mock_llm_class:
            # Make LLM service initialization fail
            mock_llm_class.side_effect = Exception("LLM service unavailable")

            with pytest.raises(click.exceptions.Exit):
                summarize_command(
                    file_path=test_file,
                    max_length=200,
                    output_file=None,
                    verbose=False,
                )

    def test_summarize_command_file_loading_failure(self, tmp_path):
        """Test error handling when file loading fails."""
        # Create test markdown file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test\nContent")

        # Mock the LLM service
        mock_llm_service = Mock()

        with (
            patch(
                "knowledge_base_organizer.cli.summarize_command.OllamaLLMService"
            ) as mock_llm_class,
            patch(
                "knowledge_base_organizer.cli.summarize_command.FileRepository"
            ) as mock_file_repo_class,
        ):
            # Setup mocks
            mock_llm_class.return_value = mock_llm_service
            mock_file_repo = Mock()
            mock_file_repo.load_file.side_effect = Exception("File loading failed")
            mock_file_repo_class.return_value = mock_file_repo

            with pytest.raises(click.exceptions.Exit):
                summarize_command(
                    file_path=test_file,
                    max_length=200,
                    output_file=None,
                    verbose=False,
                )

    def test_summarize_command_summarization_failure(self, tmp_path):
        """Test error handling when summarization fails."""
        # Create test markdown file
        test_file = tmp_path / "test.md"
        test_content = "# Test\nContent"
        test_file.write_text(test_content)

        # Mock the LLM service
        mock_llm_service = Mock()
        mock_llm_service.summarize_content.side_effect = Exception(
            "Summarization failed"
        )

        # Mock the file repository and markdown file
        mock_markdown_file = MarkdownFile(
            path=test_file, frontmatter=Frontmatter(title="Test"), content=test_content
        )

        with (
            patch(
                "knowledge_base_organizer.cli.summarize_command.OllamaLLMService"
            ) as mock_llm_class,
            patch(
                "knowledge_base_organizer.cli.summarize_command.FileRepository"
            ) as mock_file_repo_class,
        ):
            # Setup mocks
            mock_llm_class.return_value = mock_llm_service
            mock_file_repo = Mock()
            mock_file_repo.load_file.return_value = mock_markdown_file
            mock_file_repo_class.return_value = mock_file_repo

            with pytest.raises(click.exceptions.Exit):
                summarize_command(
                    file_path=test_file,
                    max_length=200,
                    output_file=None,
                    verbose=False,
                )

    def test_summarize_command_empty_summary(self, tmp_path):
        """Test handling when LLM returns empty summary."""
        # Create test markdown file
        test_file = tmp_path / "test.md"
        test_content = "# Test\nContent"
        test_file.write_text(test_content)

        # Mock the LLM service to return empty summary
        mock_llm_service = Mock()
        mock_llm_service.summarize_content.return_value = ""

        # Mock the file repository and markdown file
        mock_markdown_file = MarkdownFile(
            path=test_file, frontmatter=Frontmatter(title="Test"), content=test_content
        )

        with (
            patch(
                "knowledge_base_organizer.cli.summarize_command.OllamaLLMService"
            ) as mock_llm_class,
            patch(
                "knowledge_base_organizer.cli.summarize_command.FileRepository"
            ) as mock_file_repo_class,
        ):
            # Setup mocks
            mock_llm_class.return_value = mock_llm_service
            mock_file_repo = Mock()
            mock_file_repo.load_file.return_value = mock_markdown_file
            mock_file_repo_class.return_value = mock_file_repo

            # Should not raise exception, just show warning
            summarize_command(
                file_path=test_file, max_length=200, output_file=None, verbose=False
            )

            # Verify LLM service was called
            mock_llm_service.summarize_content.assert_called_once()

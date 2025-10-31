"""Tests for summarize command."""

from typing import Any
from unittest.mock import Mock, patch

import click
import pytest
from typer.testing import CliRunner

from knowledge_base_organizer.cli.summarize_command import summarize_command
from knowledge_base_organizer.domain.models import Frontmatter, MarkdownFile


class TestSummarizeCommand:
    """Test cases for summarize command."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_summarize_command_success(self, tmp_path: Any) -> None:
        """Test successful summarization of a markdown file."""
        # Create test file
        test_file = tmp_path / "test.md"
        test_content = """# Machine Learning Basics

Machine learning is a subset of artificial intelligence that focuses on algorithms
that can learn from and make predictions on data. It involves training models
on datasets to recognize patterns and make decisions without being explicitly
programmed for every scenario.

## Key Concepts

- Supervised Learning: Learning with labeled data
- Unsupervised Learning: Finding patterns in unlabeled data
- Reinforcement Learning: Learning through interaction and feedback

## Applications

Machine learning is used in various fields including:
- Image recognition
- Natural language processing
- Recommendation systems
- Autonomous vehicles
"""
        test_file.write_text(test_content)

        # Mock LLM service
        mock_llm_service = Mock()
        mock_llm_service.summarize_content.return_value = (
            "機械学習は人工知能の一分野で、データから学習し予測を行うアルゴリズムに焦点を当てています。"
            "教師あり学習、教師なし学習、強化学習の3つの主要な手法があり、"
            "画像認識、自然言語処理、推薦システムなど様々な分野で応用されています。"
        )

        # Create mock MarkdownFile
        mock_markdown_file = MarkdownFile(
            path=test_file,
            frontmatter=Frontmatter(title="Test Note", tags=["test", "example"]),
            content=test_content,
        )

        with (
            patch(
                "knowledge_base_organizer.infrastructure.llm_factory.create_llm_service"
            ) as mock_create_llm,
            patch(
                "knowledge_base_organizer.cli.summarize_command.FileRepository"
            ) as mock_file_repo_class,
        ):
            # Setup mocks
            mock_create_llm.return_value = mock_llm_service
            mock_file_repo = Mock()
            mock_file_repo.load_file.return_value = mock_markdown_file
            mock_file_repo_class.return_value = mock_file_repo

            # Run the command
            summarize_command(
                file_path=test_file,
                max_length=200,
                output_file=None,
                verbose=False,
            )

            # Verify LLM service was created and called
            mock_create_llm.assert_called_once()
            mock_llm_service.summarize_content.assert_called_once_with(
                test_content, max_length=200
            )

    def test_summarize_command_with_output_file(self, tmp_path: Any) -> None:
        """Test summarization with output file specified."""
        # Create test file
        test_file = tmp_path / "test.md"
        test_content = "# Test\nThis is a test document."
        test_file.write_text(test_content)

        # Create output file path
        output_file = tmp_path / "summary.md"

        # Mock LLM service
        mock_llm_service = Mock()
        mock_llm_service.summarize_content.return_value = (
            "テストドキュメントの要約です。"
        )

        # Create mock MarkdownFile
        mock_markdown_file = MarkdownFile(
            path=test_file,
            frontmatter=Frontmatter(title="Test", tags=[]),
            content=test_content,
        )

        with (
            patch(
                "knowledge_base_organizer.infrastructure.llm_factory.create_llm_service"
            ) as mock_create_llm,
            patch(
                "knowledge_base_organizer.cli.summarize_command.FileRepository"
            ) as mock_file_repo_class,
        ):
            # Setup mocks
            mock_create_llm.return_value = mock_llm_service
            mock_file_repo = Mock()
            mock_file_repo.load_file.return_value = mock_markdown_file
            mock_file_repo_class.return_value = mock_file_repo

            # Run the command with output file
            summarize_command(
                file_path=test_file,
                max_length=100,
                output_file=output_file,
                verbose=True,
            )

            # Verify output file was created
            assert output_file.exists()
            summary_content = output_file.read_text()
            assert "テストドキュメントの要約です。" in summary_content

            # Verify LLM service was called
            mock_create_llm.assert_called_once()
            mock_llm_service.summarize_content.assert_called_once_with(
                test_content, max_length=100
            )

    def test_summarize_command_llm_service_failure(self, tmp_path: Any) -> None:
        """Test handling of LLM service initialization failure."""
        # Create test file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test\nContent")

        with (
            patch(
                "knowledge_base_organizer.infrastructure.llm_factory.create_llm_service"
            ) as mock_create_llm,
            patch(
                "knowledge_base_organizer.cli.summarize_command.FileRepository"
            ) as mock_file_repo_class,
        ):
            # Make LLM service creation fail
            mock_create_llm.side_effect = Exception("LLM service unavailable")

            # Should handle the error gracefully
            with pytest.raises(click.exceptions.Exit):
                summarize_command(
                    file_path=test_file,
                    max_length=200,
                    output_file=None,
                    verbose=False,
                )

    def test_summarize_command_file_loading_failure(self, tmp_path: Any) -> None:
        """Test handling of file loading failure."""
        # Create test file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test\nContent")

        # Mock LLM service
        mock_llm_service = Mock()

        with (
            patch(
                "knowledge_base_organizer.infrastructure.llm_factory.create_llm_service"
            ) as mock_create_llm,
            patch(
                "knowledge_base_organizer.cli.summarize_command.FileRepository"
            ) as mock_file_repo_class,
        ):
            # Setup mocks
            mock_create_llm.return_value = mock_llm_service
            mock_file_repo = Mock()
            mock_file_repo.load_file.side_effect = Exception("File loading failed")
            mock_file_repo_class.return_value = mock_file_repo

            # Should handle the error gracefully
            with pytest.raises(click.exceptions.Exit):
                summarize_command(
                    file_path=test_file,
                    max_length=200,
                    output_file=None,
                    verbose=False,
                )

    def test_summarize_command_summarization_failure(self, tmp_path: Any) -> None:
        """Test handling of summarization failure."""
        # Create test file
        test_file = tmp_path / "test.md"
        test_content = "# Test\nContent"
        test_file.write_text(test_content)

        # Mock LLM service that fails during summarization
        mock_llm_service = Mock()
        mock_llm_service.summarize_content.side_effect = Exception(
            "Summarization failed"
        )

        # Create mock MarkdownFile
        mock_markdown_file = MarkdownFile(
            path=test_file,
            frontmatter=Frontmatter(title="Test", tags=[]),
            content=test_content,
        )

        with (
            patch(
                "knowledge_base_organizer.infrastructure.llm_factory.create_llm_service"
            ) as mock_create_llm,
            patch(
                "knowledge_base_organizer.cli.summarize_command.FileRepository"
            ) as mock_file_repo_class,
        ):
            # Setup mocks
            mock_create_llm.return_value = mock_llm_service
            mock_file_repo = Mock()
            mock_file_repo.load_file.return_value = mock_markdown_file
            mock_file_repo_class.return_value = mock_file_repo

            # Should handle the error gracefully
            with pytest.raises(click.exceptions.Exit):
                summarize_command(
                    file_path=test_file,
                    max_length=200,
                    output_file=None,
                    verbose=False,
                )

    def test_summarize_command_empty_summary(self, tmp_path: Any) -> None:
        """Test handling of empty summary result."""
        # Create test file
        test_file = tmp_path / "test.md"
        test_content = "# Test\nContent"
        test_file.write_text(test_content)

        # Mock LLM service that returns empty summary
        mock_llm_service = Mock()
        mock_llm_service.summarize_content.return_value = ""

        # Create mock MarkdownFile
        mock_markdown_file = MarkdownFile(
            path=test_file,
            frontmatter=Frontmatter(title="Test", tags=[]),
            content=test_content,
        )

        with (
            patch(
                "knowledge_base_organizer.infrastructure.llm_factory.create_llm_service"
            ) as mock_create_llm,
            patch(
                "knowledge_base_organizer.cli.summarize_command.FileRepository"
            ) as mock_file_repo_class,
        ):
            # Setup mocks
            mock_create_llm.return_value = mock_llm_service
            mock_file_repo = Mock()
            mock_file_repo.load_file.return_value = mock_markdown_file
            mock_file_repo_class.return_value = mock_file_repo

            # Should handle empty summary gracefully
            summarize_command(
                file_path=test_file,
                max_length=200,
                output_file=None,
                verbose=False,
            )

            # Verify LLM service was called
            mock_create_llm.assert_called_once()
            mock_llm_service.summarize_content.assert_called_once()

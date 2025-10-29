"""
Tests for the ask command implementation (RAG).

Tests the RAG functionality including:
- Question answering workflow
- Error handling
- Output formatting
"""

from unittest.mock import MagicMock

import pytest
import typer
from typer.testing import CliRunner

from knowledge_base_organizer.cli.ask_command import ask_command


@pytest.fixture
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def ask_app():
    """Create a Typer app with the ask command for testing."""
    app = typer.Typer()
    app.command()(ask_command)
    return app


class TestAskCommand:
    """Test cases for the ask command."""

    def test_ask_command_help(self, runner, ask_app):
        """Test that the ask command shows help correctly."""
        result = runner.invoke(ask_app, ["--help"])
        assert result.exit_code == 0
        assert "Ask questions about your vault content using RAG" in result.output

    def test_ask_command_nonexistent_vault(self, runner, ask_app):
        """Test ask command with non-existent vault path."""
        result = runner.invoke(
            ask_app, ["What is machine learning?", "--vault", "/nonexistent/path"]
        )
        assert result.exit_code == 1
        assert "Vault path does not exist" in result.output

    def test_ask_command_no_index(self, runner, ask_app, tmp_path):
        """Test ask command when no vector index exists."""
        vault_path = tmp_path / "no_index_vault"
        vault_path.mkdir()

        result = runner.invoke(
            ask_app, ["What is machine learning?", "--vault", str(vault_path)]
        )

        assert result.exit_code == 1
        assert "No vector index found" in result.output

    def test_generate_rag_answer(self):
        """Test RAG answer generation."""
        from knowledge_base_organizer.cli.ask_command import _generate_rag_answer

        # Mock LLM service
        mock_llm = MagicMock()
        mock_llm.summarize_content.return_value = "This is a test answer."

        # Test answer generation
        result = _generate_rag_answer(
            question="What is testing?",
            context="Testing is important for software quality.",
            llm_service=mock_llm,
        )

        assert result == "This is a test answer."
        mock_llm.summarize_content.assert_called_once()

    def test_generate_rag_answer_error_handling(self):
        """Test RAG answer generation with LLM error."""
        from knowledge_base_organizer.cli.ask_command import _generate_rag_answer

        # Mock LLM service that raises an error
        mock_llm = MagicMock()
        mock_llm.summarize_content.side_effect = Exception("LLM error")

        # Test error handling
        result = _generate_rag_answer(
            question="What is testing?",
            context="Testing is important.",
            llm_service=mock_llm,
        )

        assert "Error generating answer" in result

"""Tests for organize command."""

from typing import Any
from unittest.mock import Mock, patch

import click
import pytest
from typer.testing import CliRunner

from knowledge_base_organizer.cli.organize_command import (
    _analyze_vault_improvements,
    organize_command,
)
from knowledge_base_organizer.infrastructure.config import ProcessingConfig


class TestOrganizeCommand:
    """Test cases for organize command."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_organize_command_basic_functionality(self, tmp_path: Any) -> None:
        """Test basic organize command functionality without AI."""
        # Create test vault structure
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()

        test_file = vault_path / "test.md"
        test_content = """---
title: Test Note
---

# Test Note
Some content here.
"""
        test_file.write_text(test_content)

        # Mock the enhancement service and results
        mock_enhancement_service = Mock()
        mock_result = Mock()
        mock_result.improvements_made = 2
        mock_result.success = True
        mock_result.changes_applied = ["Added tags", "Added description"]
        mock_result.file_path = test_file
        mock_enhancement_service.enhance_vault_frontmatter.return_value = [mock_result]

        with (
            patch(
                "knowledge_base_organizer.cli.organize_command.FileRepository"
            ) as mock_file_repo_class,
            patch(
                "knowledge_base_organizer.cli.organize_command.FrontmatterEnhancementService"
            ) as mock_enhancement_class,
        ):
            # Setup mocks
            mock_file_repo = Mock()
            # Return a mock file to avoid "no files found" error
            mock_file = Mock()
            mock_file.path = test_file
            mock_file_repo.load_vault.return_value = [mock_file]
            mock_file_repo_class.return_value = mock_file_repo
            mock_enhancement_class.return_value = mock_enhancement_service

            # Run the command
            organize_command(
                vault_path=vault_path,
                dry_run=True,
                interactive=False,
                ai_suggest_metadata=False,
                verbose=False,
            )

            # Verify enhancement service was called
            mock_enhancement_service.enhance_vault_frontmatter.assert_called_once()

    def test_organize_command_with_ai_suggestions(self, tmp_path: Any) -> None:
        """Test organize command with AI metadata suggestions enabled."""
        # Create test vault structure
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()

        test_file = vault_path / "test.md"
        test_content = """---
title: Test Note
---

# Test Note
This is a note about machine learning and artificial intelligence.
It discusses various algorithms and techniques used in data science.
"""
        test_file.write_text(test_content)

        # Mock the LLM service
        mock_llm_service = Mock()
        mock_metadata_suggestion = Mock()
        mock_metadata_suggestion.suggested_tags = [
            "machine-learning",
            "ai",
            "data-science",
        ]
        mock_metadata_suggestion.suggested_aliases = ["ML Note", "AI Guide"]
        mock_metadata_suggestion.suggested_description = (
            "A comprehensive guide to ML and AI"
        )
        mock_metadata_suggestion.confidence_scores = {
            "tags": 0.9,
            "aliases": 0.8,
            "description": 0.85,
        }
        mock_llm_service.suggest_metadata.return_value = mock_metadata_suggestion

        # Mock the enhancement service and results
        mock_enhancement_service = Mock()
        mock_result = Mock()
        mock_result.improvements_made = 3
        mock_result.success = True
        mock_result.changes_applied = [
            "Added AI-suggested tags: ['machine-learning', 'ai', 'data-science']",
            "Added AI-suggested aliases: ['ML Note', 'AI Guide']",
            "Added AI-suggested description: A comprehensive guide to ML and AI...",
        ]
        mock_result.file_path = test_file
        mock_enhancement_service.enhance_vault_frontmatter.return_value = [mock_result]

        with (
            patch(
                "knowledge_base_organizer.cli.organize_command.FileRepository"
            ) as mock_file_repo_class,
            patch(
                "knowledge_base_organizer.cli.organize_command.FrontmatterEnhancementService"
            ) as mock_enhancement_class,
            patch(
                "knowledge_base_organizer.infrastructure.llm_factory.create_llm_service"
            ) as mock_create_llm,
        ):
            # Setup mocks
            mock_file_repo = Mock()
            # Return a mock file to avoid "no files found" error
            mock_file = Mock()
            mock_file.path = test_file
            mock_file_repo.load_vault.return_value = [mock_file]
            mock_file_repo_class.return_value = mock_file_repo
            mock_enhancement_class.return_value = mock_enhancement_service
            mock_create_llm.return_value = mock_llm_service

            # Run the command with AI enabled
            organize_command(
                vault_path=vault_path,
                dry_run=True,
                interactive=False,
                ai_suggest_metadata=True,
                verbose=True,
            )

            # Verify LLM service was created and set
            mock_create_llm.assert_called_once()
            mock_enhancement_service.set_llm_service.assert_called_once_with(
                mock_llm_service
            )

    def test_organize_command_ai_service_failure(self, tmp_path: Any) -> None:
        """Test organize command when AI service fails to initialize."""
        # Create test vault structure
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()

        test_file = vault_path / "test.md"
        test_file.write_text("---\ntitle: Test\n---\n# Test")

        # Mock the enhancement service
        mock_enhancement_service = Mock()
        mock_enhancement_service.enhance_vault_frontmatter.return_value = []

        with (
            patch(
                "knowledge_base_organizer.cli.organize_command.FileRepository"
            ) as mock_file_repo_class,
            patch(
                "knowledge_base_organizer.cli.organize_command.FrontmatterEnhancementService"
            ) as mock_enhancement_class,
            patch(
                "knowledge_base_organizer.infrastructure.llm_factory.create_llm_service"
            ) as mock_create_llm,
        ):
            # Setup mocks
            mock_file_repo = Mock()
            # Return a mock file to avoid "no files found" error
            mock_file = Mock()
            mock_file.path = test_file
            mock_file_repo.load_vault.return_value = [mock_file]
            mock_file_repo_class.return_value = mock_file_repo
            mock_enhancement_class.return_value = mock_enhancement_service

            # Make LLM service initialization fail
            mock_create_llm.side_effect = Exception("AI service unavailable")

            # Should not raise exception, just continue without AI
            organize_command(
                vault_path=vault_path,
                dry_run=True,
                interactive=False,
                ai_suggest_metadata=True,
                verbose=False,
            )

            # Verify enhancement service was still called (without AI)
            mock_enhancement_service.enhance_vault_frontmatter.assert_called_once()
            # Verify set_llm_service was not called since AI failed
            mock_enhancement_service.set_llm_service.assert_not_called()

    def test_organize_command_vault_not_exists(self, tmp_path: Any) -> None:
        """Test error handling when vault path doesn't exist."""
        non_existent_vault = tmp_path / "nonexistent"

        with pytest.raises(click.exceptions.Exit):
            organize_command(
                vault_path=non_existent_vault,
                dry_run=True,
                interactive=False,
                ai_suggest_metadata=False,
                verbose=False,
            )

    def test_analyze_vault_improvements_with_llm_service(self, tmp_path: Any) -> None:
        """Test _analyze_vault_improvements function with LLM service."""
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()

        config = ProcessingConfig.get_default_config()

        # Mock LLM service
        mock_llm_service = Mock()

        # Mock file repository and enhancement service
        mock_file_repo = Mock()
        # Return a mock file to avoid "no files found" error
        mock_file = Mock()
        mock_file.path = vault_path / "test.md"
        mock_file_repo.load_vault.return_value = [mock_file]

        mock_enhancement_service = Mock()
        mock_enhancement_service.enhance_vault_frontmatter.return_value = []

        with (
            patch(
                "knowledge_base_organizer.cli.organize_command.FileRepository"
            ) as mock_file_repo_class,
            patch(
                "knowledge_base_organizer.cli.organize_command.FrontmatterEnhancementService"
            ) as mock_enhancement_class,
        ):
            # Setup mocks
            mock_file_repo_class.return_value = mock_file_repo
            mock_enhancement_class.return_value = mock_enhancement_service

            # Call the function
            results = _analyze_vault_improvements(vault_path, config, mock_llm_service)

            # Verify LLM service was set
            mock_enhancement_service.set_llm_service.assert_called_once_with(
                mock_llm_service
            )

            # Verify results
            assert isinstance(results, list)

    def test_analyze_vault_improvements_without_llm_service(
        self, tmp_path: Any
    ) -> None:
        """Test _analyze_vault_improvements function without LLM service."""
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()

        config = ProcessingConfig.get_default_config()

        # Mock file repository and enhancement service
        mock_file_repo = Mock()
        # Return a mock file to avoid "no files found" error
        mock_file = Mock()
        mock_file.path = vault_path / "test.md"
        mock_file_repo.load_vault.return_value = [mock_file]

        mock_enhancement_service = Mock()
        mock_enhancement_service.enhance_vault_frontmatter.return_value = []

        with (
            patch(
                "knowledge_base_organizer.cli.organize_command.FileRepository"
            ) as mock_file_repo_class,
            patch(
                "knowledge_base_organizer.cli.organize_command.FrontmatterEnhancementService"
            ) as mock_enhancement_class,
        ):
            # Setup mocks
            mock_file_repo_class.return_value = mock_file_repo
            mock_enhancement_class.return_value = mock_enhancement_service

            # Call the function without LLM service
            results = _analyze_vault_improvements(vault_path, config, None)

            # Verify LLM service was not set
            mock_enhancement_service.set_llm_service.assert_not_called()

            # Verify results
            assert isinstance(results, list)

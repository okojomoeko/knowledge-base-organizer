"""End-to-end integration tests for AI-enhanced organize functionality."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from knowledge_base_organizer.cli.organize_command import organize_command
from knowledge_base_organizer.cli.summarize_command import summarize_command
from knowledge_base_organizer.domain.services.ai_services import MetadataSuggestion


class TestAIEnhancedOrganizeEndToEnd:
    """End-to-end tests for AI-enhanced organize functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        # Create temporary vault
        self.temp_dir = Path(tempfile.mkdtemp())
        self.vault_path = self.temp_dir / "test_vault"
        self.vault_path.mkdir()

        # Create test files with various content types
        self._create_test_files()

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def _create_test_files(self) -> None:
        """Create test files for AI enhancement testing."""
        # Machine learning note
        ml_note = self.vault_path / "machine_learning_basics.md"
        ml_content = """---
title: Machine Learning Basics
---

# Machine Learning Fundamentals

Machine learning is a subset of artificial intelligence that focuses on algorithms
that can learn from and make predictions on data. It involves training models
on datasets to recognize patterns and make decisions.

## Key Concepts

- Supervised Learning: Learning with labeled data
- Unsupervised Learning: Finding patterns in unlabeled data
- Reinforcement Learning: Learning through interaction and feedback

## Applications

- Image recognition and computer vision
- Natural language processing and text analysis
- Recommendation systems for e-commerce
- Autonomous vehicles and robotics
"""
        ml_note.write_text(ml_content)

        # Programming note
        prog_note = self.vault_path / "python_programming.md"
        prog_content = """---
title: Python Programming
---

# Python Programming Guide

Python is a high-level, interpreted programming language known for its
simplicity and readability. It's widely used in web development, data science,
artificial intelligence, and automation.

## Key Features

- Simple and readable syntax
- Extensive standard library
- Strong community support
- Cross-platform compatibility

## Popular Libraries

- NumPy for numerical computing
- Pandas for data manipulation
- Django for web development
- TensorFlow for machine learning
"""
        prog_note.write_text(prog_content)

    def test_organize_command_ai_integration_dry_run(self) -> None:
        """Test AI-enhanced organize command in dry-run mode."""
        # Mock LLM service with realistic responses
        mock_llm_service = Mock()

        def mock_suggest_metadata(
            content: str, current_frontmatter: dict
        ) -> MetadataSuggestion:
            if "machine learning" in content.lower():
                return MetadataSuggestion(
                    suggested_tags=["machine-learning", "ai", "data-science"],
                    suggested_aliases=["ML Basics", "AI Fundamentals"],
                    suggested_description="Introduction to machine learning concepts and applications",
                    confidence_scores={
                        "tags": 0.9,
                        "aliases": 0.8,
                        "description": 0.85,
                    },
                )
            if "python" in content.lower():
                return MetadataSuggestion(
                    suggested_tags=["programming", "python", "development"],
                    suggested_aliases=["Python Guide", "Programming Tutorial"],
                    suggested_description="Comprehensive guide to Python programming",
                    confidence_scores={"tags": 0.6, "aliases": 0.5, "description": 0.7},
                )
            return MetadataSuggestion(
                suggested_tags=[],
                suggested_aliases=[],
                suggested_description="",
                confidence_scores={"tags": 0.6, "aliases": 0.5, "description": 0.7},
            )

        mock_llm_service.suggest_metadata.side_effect = mock_suggest_metadata

        with patch(
            "knowledge_base_organizer.infrastructure.llm_factory.create_llm_service"
        ) as mock_create_llm:
            mock_create_llm.return_value = mock_llm_service

            # Run organize command with AI enabled
            organize_command(
                vault_path=self.vault_path,
                dry_run=True,  # Dry run to avoid file modifications
                interactive=False,
                ai_suggest_metadata=True,
                verbose=True,
            )

            # Verify LLM service was created and used
            mock_create_llm.assert_called_once()
            # Should have been called for each file
            assert mock_llm_service.suggest_metadata.call_count >= 2

    def test_organize_command_ai_integration_execute_mode(self) -> None:
        """Test AI-enhanced organize command in execute mode."""
        # Mock LLM service
        mock_llm_service = Mock()
        mock_llm_service.suggest_metadata.return_value = MetadataSuggestion(
            suggested_tags=["test", "integration"],
            suggested_aliases=["Test Note"],
            suggested_description="Test file for integration testing",
            confidence_scores={"tags": 0.8, "aliases": 0.7, "description": 0.9},
        )

        with patch(
            "knowledge_base_organizer.infrastructure.llm_factory.create_llm_service"
        ) as mock_create_llm:
            mock_create_llm.return_value = mock_llm_service

            # Run organize command in execute mode
            organize_command(
                vault_path=self.vault_path,
                dry_run=False,  # Execute mode
                interactive=False,
                ai_suggest_metadata=True,
                verbose=False,
            )

            # Verify LLM service was created
            mock_create_llm.assert_called_once()

    def test_organize_command_fallback_without_ai(self) -> None:
        """Test organize command fallback when AI service is unavailable."""
        with patch(
            "knowledge_base_organizer.infrastructure.llm_factory.create_llm_service"
        ) as mock_create_llm:
            # Make LLM service creation fail
            mock_create_llm.side_effect = Exception("AI service unavailable")

            # Should not raise exception, just continue without AI
            organize_command(
                vault_path=self.vault_path,
                dry_run=True,
                interactive=False,
                ai_suggest_metadata=True,  # AI requested but will fail
                verbose=False,
            )

            # Verify LLM service creation was attempted
            mock_create_llm.assert_called_once()

    def test_summarize_command_integration(self) -> None:
        """Test AI-enhanced summarize command integration."""
        # Select a test file for summarization
        test_file = self.vault_path / "machine_learning_basics.md"

        # Mock LLM service
        mock_llm_service = Mock()
        mock_llm_service.summarize_content.return_value = (
            "機械学習は人工知能の一分野で、データから学習し予測を行うアルゴリズムに焦点を当てています。"
            "教師あり学習、教師なし学習、強化学習の3つの主要な手法があり、"
            "画像認識、自然言語処理、推薦システムなど様々な分野で応用されています。"
        )

        with patch(
            "knowledge_base_organizer.infrastructure.llm_factory.create_llm_service"
        ) as mock_create_llm:
            mock_create_llm.return_value = mock_llm_service

            # Run summarize command
            summarize_command(
                file_path=test_file,
                max_length=200,
                output=None,
                verbose=True,
            )

            # Verify LLM service was created and used
            mock_create_llm.assert_called_once()
            mock_llm_service.summarize_content.assert_called_once()

    def test_summarize_command_with_output_file(self) -> None:
        """Test summarize command with output file."""
        # Select a test file for summarization
        test_file = self.vault_path / "python_programming.md"
        output_file = self.vault_path / "python_summary.md"

        # Mock LLM service
        mock_llm_service = Mock()
        mock_llm_service.summarize_content.return_value = (
            "Pythonは読みやすく簡潔な構文を持つプログラミング言語で、"
            "ウェブ開発、データサイエンス、AI分野で広く使用されています。"
        )

        with patch(
            "knowledge_base_organizer.infrastructure.llm_factory.create_llm_service"
        ) as mock_create_llm:
            mock_create_llm.return_value = mock_llm_service

            # Run summarize command with output file
            summarize_command(
                file_path=test_file,
                max_length=150,
                output=output_file,
                verbose=False,
            )

            # Verify output file was created
            assert output_file.exists()
            summary_content = output_file.read_text()
            assert "Python" in summary_content

            # Verify LLM service was used
            mock_create_llm.assert_called_once()
            mock_llm_service.summarize_content.assert_called_once()

    def test_ai_services_error_handling(self) -> None:
        """Test error handling when AI services encounter issues."""
        # Mock LLM service that raises exceptions
        mock_llm_service = Mock()
        mock_llm_service.suggest_metadata.side_effect = Exception(
            "AI processing failed"
        )

        with patch(
            "knowledge_base_organizer.infrastructure.llm_factory.create_llm_service"
        ) as mock_create_llm:
            mock_create_llm.return_value = mock_llm_service

            # Should handle AI errors gracefully
            organize_command(
                vault_path=self.vault_path,
                dry_run=True,
                interactive=False,
                ai_suggest_metadata=True,
                verbose=False,
            )

            # Verify LLM service was created
            mock_create_llm.assert_called_once()

    def test_ai_configuration_integration(self) -> None:
        """Test AI functionality with different configuration scenarios."""
        # Test with custom LLM configuration
        mock_llm_service = Mock()
        mock_llm_service.suggest_metadata.return_value = MetadataSuggestion(
            suggested_tags=["custom", "config"],
            suggested_aliases=["Custom Note"],
            suggested_description="Note processed with custom AI configuration",
            confidence_scores={"tags": 0.9, "aliases": 0.8, "description": 0.85},
        )

        with patch(
            "knowledge_base_organizer.infrastructure.llm_factory.create_llm_service"
        ) as mock_create_llm:
            mock_create_llm.return_value = mock_llm_service

            # Run with AI enabled
            organize_command(
                vault_path=self.vault_path,
                dry_run=True,
                interactive=False,
                ai_suggest_metadata=True,
                verbose=True,
            )

            # Verify service creation and usage
            mock_create_llm.assert_called_once()
            assert mock_llm_service.suggest_metadata.call_count >= 1

    def test_mixed_ai_and_traditional_processing(self) -> None:
        """Test combination of AI-enhanced and traditional processing."""
        # Create files with and without existing metadata
        basic_file = self.vault_path / "basic_note.md"
        basic_content = """---
title: Basic Note
tags: [existing, manual]
---

# Basic Note

This is a simple note with existing metadata.
"""
        basic_file.write_text(basic_content)

        # Mock LLM service
        mock_llm_service = Mock()
        mock_llm_service.suggest_metadata.return_value = MetadataSuggestion(
            suggested_tags=["enhanced", "ai-generated"],
            suggested_aliases=["Enhanced Note"],
            suggested_description="AI-enhanced note with additional metadata",
            confidence_scores={"tags": 0.7, "aliases": 0.6, "description": 0.8},
        )

        with patch(
            "knowledge_base_organizer.infrastructure.llm_factory.create_llm_service"
        ) as mock_create_llm:
            mock_create_llm.return_value = mock_llm_service

            # Run organize command
            organize_command(
                vault_path=self.vault_path,
                dry_run=True,
                interactive=False,
                ai_suggest_metadata=True,
                verbose=True,
            )

            # Verify AI service was used
            mock_create_llm.assert_called_once()
            # Should process all files, including those with existing metadata
            assert mock_llm_service.suggest_metadata.call_count >= 3

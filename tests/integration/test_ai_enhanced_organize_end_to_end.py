"""End-to-end integration tests for AI-enhanced organize functionality."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from knowledge_base_organizer.cli.organize_command import organize_command
from knowledge_base_organizer.cli.summarize_command import summarize_command
from knowledge_base_organizer.domain.services.ai_services import MetadataSuggestion


class TestAIEnhancedOrganizeEndToEnd:
    """End-to-end integration tests for AI-enhanced organize functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.vault_path = self.temp_dir / "test_vault"
        self.vault_path.mkdir()

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_organize_command_ai_integration_dry_run(self):
        """Test AI-enhanced organize command in dry-run mode."""
        # Create test files with various content types
        self._create_test_vault_files()

        # Mock LLM service with realistic responses
        mock_llm_service = Mock()

        def mock_suggest_metadata(content, existing_metadata):
            """Mock metadata suggestion based on content."""
            if "machine learning" in content.lower():
                return MetadataSuggestion(
                    suggested_tags=["machine-learning", "ai", "algorithms"],
                    suggested_aliases=["ML Guide", "AI Tutorial"],
                    suggested_description="Comprehensive guide to machine learning concepts",
                    confidence_scores={
                        "tags": 0.9,
                        "aliases": 0.8,
                        "description": 0.85,
                    },
                )
            if "python" in content.lower():
                return MetadataSuggestion(
                    suggested_tags=["python", "programming", "coding"],
                    suggested_aliases=["Python Guide", "Coding Tutorial"],
                    suggested_description="Python programming tutorial and examples",
                    confidence_scores={
                        "tags": 0.95,
                        "aliases": 0.85,
                        "description": 0.9,
                    },
                )
            return MetadataSuggestion(
                suggested_tags=["general", "notes"],
                suggested_aliases=["General Note"],
                suggested_description="General purpose note",
                confidence_scores={"tags": 0.6, "aliases": 0.5, "description": 0.7},
            )

        mock_llm_service.suggest_metadata.side_effect = mock_suggest_metadata

        with patch(
            "knowledge_base_organizer.cli.organize_command.OllamaLLMService"
        ) as mock_llm_class:
            mock_llm_class.return_value = mock_llm_service

            # Run organize command with AI enabled
            organize_command(
                vault_path=self.vault_path,
                dry_run=True,  # Dry run to avoid file modifications
                interactive=False,
                ai_suggest_metadata=True,
                verbose=True,
                create_backup=False,
            )

            # Verify LLM service was initialized
            mock_llm_class.assert_called_once()

            # Verify metadata suggestions were called
            assert mock_llm_service.suggest_metadata.call_count > 0

    def test_organize_command_ai_integration_execute_mode(self):
        """Test AI-enhanced organize command in execute mode."""
        # Create test files
        self._create_test_vault_files()

        # Mock LLM service
        mock_llm_service = Mock()
        mock_llm_service.suggest_metadata.return_value = MetadataSuggestion(
            suggested_tags=["test", "integration"],
            suggested_aliases=["Test Note"],
            suggested_description="Integration test note",
            confidence_scores={"tags": 0.8, "aliases": 0.7, "description": 0.9},
        )

        with patch(
            "knowledge_base_organizer.cli.organize_command.OllamaLLMService"
        ) as mock_llm_class:
            mock_llm_class.return_value = mock_llm_service

            # Run organize command in execute mode
            organize_command(
                vault_path=self.vault_path,
                dry_run=False,  # Execute mode
                interactive=False,
                ai_suggest_metadata=True,
                verbose=False,
                create_backup=False,  # Skip backup for test
            )

            # Verify LLM service was used
            mock_llm_class.assert_called_once()
            assert mock_llm_service.suggest_metadata.call_count > 0

    def test_organize_command_fallback_without_ai(self):
        """Test organize command fallback when AI service fails."""
        # Create test files
        self._create_test_vault_files()

        with patch(
            "knowledge_base_organizer.cli.organize_command.OllamaLLMService"
        ) as mock_llm_class:
            # Make AI service fail
            mock_llm_class.side_effect = Exception("AI service unavailable")

            # Should not raise exception, just continue without AI
            organize_command(
                vault_path=self.vault_path,
                dry_run=True,
                interactive=False,
                ai_suggest_metadata=True,  # Requested but will fail
                verbose=False,
                create_backup=False,
            )

            # Verify AI service initialization was attempted
            mock_llm_class.assert_called_once()

    def test_summarize_command_integration(self):
        """Test summarize command integration."""
        # Create a test file with substantial content
        test_file = self.vault_path / "detailed_note.md"
        test_content = """---
title: Comprehensive Machine Learning Guide
tags: [ml, ai, data-science]
---

# Comprehensive Machine Learning Guide

## Introduction

Machine learning is a subset of artificial intelligence that focuses on
algorithms that can learn and make decisions from data. This guide covers
the fundamental concepts and practical applications.

## Supervised Learning

Supervised learning involves training algorithms on labeled data. Common
algorithms include:

- Linear Regression
- Decision Trees
- Random Forest
- Support Vector Machines
- Neural Networks

## Unsupervised Learning

Unsupervised learning finds patterns in data without labeled examples:

- K-Means Clustering
- Hierarchical Clustering
- Principal Component Analysis
- Association Rules

## Deep Learning

Deep learning uses neural networks with multiple layers to model complex
patterns in data. Popular frameworks include TensorFlow and PyTorch.

## Conclusion

Machine learning continues to evolve and find applications across many
industries, from healthcare to finance to autonomous vehicles.
"""
        test_file.write_text(test_content)

        # Mock LLM service
        mock_llm_service = Mock()
        mock_llm_service.summarize_content.return_value = (
            "This guide covers machine learning fundamentals including supervised "
            "and unsupervised learning algorithms, deep learning concepts, and "
            "practical applications across various industries."
        )

        with patch(
            "knowledge_base_organizer.cli.summarize_command.OllamaLLMService"
        ) as mock_llm_class:
            mock_llm_class.return_value = mock_llm_service

            # Test summarize command
            summarize_command(
                file_path=test_file, max_length=200, output_file=None, verbose=True
            )

            # Verify LLM service was used
            mock_llm_class.assert_called_once()
            mock_llm_service.summarize_content.assert_called_once_with(
                test_content, max_length=200
            )

    def test_summarize_command_with_output_file(self):
        """Test summarize command with output file."""
        # Create a test file
        test_file = self.vault_path / "test_note.md"
        test_content = """---
title: Test Note
---

# Test Note

This is a test note with some content that needs to be summarized.
It contains information about testing and validation procedures.
"""
        test_file.write_text(test_content)

        # Create output file path
        output_file = self.vault_path / "summary.md"

        # Mock LLM service
        mock_llm_service = Mock()
        mock_llm_service.summarize_content.return_value = (
            "Test note covering testing and validation procedures."
        )

        with patch(
            "knowledge_base_organizer.cli.summarize_command.OllamaLLMService"
        ) as mock_llm_class:
            mock_llm_class.return_value = mock_llm_service

            # Test summarize command with output
            summarize_command(
                file_path=test_file,
                max_length=100,
                output_file=output_file,
                verbose=False,
            )

            # Verify output file was created
            assert output_file.exists()
            content = output_file.read_text()
            assert "Summary of test_note.md" in content
            assert "Test note covering testing and validation procedures." in content

    def test_ai_services_error_handling(self):
        """Test error handling when AI services are completely unavailable."""
        # Create test files
        self._create_test_vault_files()

        # Test organize command with AI service failure
        with patch(
            "knowledge_base_organizer.cli.organize_command.OllamaLLMService"
        ) as mock_llm_class:
            mock_llm_class.side_effect = ImportError("Ollama not available")

            # Should handle gracefully
            organize_command(
                vault_path=self.vault_path,
                dry_run=True,
                interactive=False,
                ai_suggest_metadata=True,
                verbose=False,
                create_backup=False,
            )

        # Test summarize command with AI service failure
        test_file = self.vault_path / "test.md"

        with patch(
            "knowledge_base_organizer.cli.summarize_command.OllamaLLMService"
        ) as mock_llm_class:
            mock_llm_class.side_effect = ImportError("Ollama not available")

            # Should raise SystemExit for summarize since it's core functionality
            with pytest.raises(SystemExit):
                summarize_command(
                    file_path=test_file, max_length=200, output_file=None, verbose=False
                )

    def _create_test_vault_files(self):
        """Create test vault files with various content types."""
        # Machine learning file
        ml_file = self.vault_path / "machine_learning.md"
        ml_content = """---
title: Machine Learning Basics
---

# Machine Learning Basics

This document covers fundamental machine learning concepts including
supervised learning, unsupervised learning, and neural networks.
We explore algorithms like decision trees and support vector machines.
"""
        ml_file.write_text(ml_content)

        # Python programming file
        python_file = self.vault_path / "python_guide.md"
        python_content = """---
title: Python Programming
tags: [programming]
---

# Python Programming Guide

Learn Python programming with examples and best practices.
This guide covers variables, functions, classes, and modules.
Perfect for beginners and intermediate developers.
"""
        python_file.write_text(python_content)

        # General note file
        general_file = self.vault_path / "general_note.md"
        general_content = """---
title: General Note
---

# General Note

This is a general purpose note with miscellaneous information.
It doesn't focus on any specific technical topic.
"""
        general_file.write_text(general_content)

        # File with minimal frontmatter
        minimal_file = self.vault_path / "minimal.md"
        minimal_content = """---
title: Minimal
---

# Minimal Note

Basic note with minimal frontmatter that could benefit from AI enhancement.
"""
        minimal_file.write_text(minimal_content)

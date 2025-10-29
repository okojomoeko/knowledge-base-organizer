"""Tests for AI-enhanced frontmatter enhancement service."""

from unittest.mock import Mock, patch

from knowledge_base_organizer.domain.models import Frontmatter, MarkdownFile
from knowledge_base_organizer.domain.services.ai_services import MetadataSuggestion
from knowledge_base_organizer.domain.services.frontmatter_enhancement_service import (
    FrontmatterEnhancementService,
)


class TestFrontmatterEnhancementServiceAI:
    """Test cases for AI-enhanced frontmatter enhancement service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = FrontmatterEnhancementService()

    def test_set_llm_service(self):
        """Test setting LLM service."""
        mock_llm_service = Mock()

        self.service.set_llm_service(mock_llm_service)

        assert self.service.llm_service == mock_llm_service

    def test_enhance_file_frontmatter_with_ai_suggestions(self, tmp_path):
        """Test frontmatter enhancement with AI suggestions."""
        # Create test file
        test_file = tmp_path / "test.md"
        test_content = """---
title: Machine Learning Basics
---

# Machine Learning Basics

This document covers fundamental concepts in machine learning,
including supervised learning, unsupervised learning, and deep learning.
We'll explore various algorithms like neural networks, decision trees,
and support vector machines.
"""
        test_file.write_text(test_content)

        # Create MarkdownFile object
        markdown_file = MarkdownFile(
            path=test_file,
            frontmatter=Frontmatter(title="Machine Learning Basics"),
            content=test_content,
        )

        # Mock LLM service
        mock_llm_service = Mock()
        mock_metadata_suggestion = MetadataSuggestion(
            suggested_tags=["machine-learning", "algorithms", "neural-networks"],
            suggested_aliases=["ML Basics", "AI Fundamentals"],
            suggested_description="A comprehensive guide to machine learning fundamentals",
            confidence_scores={"tags": 0.9, "aliases": 0.8, "description": 0.85},
        )
        mock_llm_service.suggest_metadata.return_value = mock_metadata_suggestion

        # Set LLM service
        self.service.set_llm_service(mock_llm_service)

        # Mock content analyzer to avoid complex setup
        with patch.object(self.service, "content_analyzer") as mock_analyzer:
            mock_analysis_result = Mock()
            mock_analysis_result.improvements = []
            mock_analyzer.analyze_file.return_value = mock_analysis_result

            # Enhance frontmatter
            result = self.service.enhance_file_frontmatter(
                markdown_file, apply_changes=True
            )

            # Verify AI service was called
            mock_llm_service.suggest_metadata.assert_called_once()
            call_args = mock_llm_service.suggest_metadata.call_args
            assert test_content in call_args[0][0]  # Content was passed
            assert isinstance(call_args[0][1], dict)  # Existing metadata was passed

            # Verify enhancements were applied
            assert result.success
            assert result.improvements_made > 0

            # Check that AI suggestions were included in changes
            ai_tag_changes = [
                change
                for change in result.changes_applied
                if "AI-suggested tags" in change
            ]
            ai_alias_changes = [
                change
                for change in result.changes_applied
                if "AI-suggested aliases" in change
            ]
            ai_desc_changes = [
                change
                for change in result.changes_applied
                if "AI-suggested description" in change
            ]

            assert len(ai_tag_changes) > 0
            assert len(ai_alias_changes) > 0
            assert len(ai_desc_changes) > 0

            # Verify enhanced frontmatter contains AI suggestions
            enhanced_fm = result.enhanced_frontmatter
            assert "machine-learning" in enhanced_fm.get("tags", [])
            assert "algorithms" in enhanced_fm.get("tags", [])
            assert "ML Basics" in enhanced_fm.get("aliases", [])
            assert (
                enhanced_fm.get("description")
                == "A comprehensive guide to machine learning fundamentals"
            )

    def test_enhance_file_frontmatter_ai_service_error(self, tmp_path):
        """Test frontmatter enhancement when AI service fails."""
        # Create test file
        test_file = tmp_path / "test.md"
        test_content = "---\ntitle: Test\n---\n# Test"
        test_file.write_text(test_content)

        # Create MarkdownFile object
        markdown_file = MarkdownFile(
            path=test_file, frontmatter=Frontmatter(title="Test"), content=test_content
        )

        # Mock LLM service that raises exception
        mock_llm_service = Mock()
        mock_llm_service.suggest_metadata.side_effect = Exception("AI service error")

        # Set LLM service
        self.service.set_llm_service(mock_llm_service)

        # Mock content analyzer
        with patch.object(self.service, "content_analyzer") as mock_analyzer:
            mock_analysis_result = Mock()
            mock_analysis_result.improvements = []
            mock_analyzer.analyze_file.return_value = mock_analysis_result

            # Enhance frontmatter - should not fail despite AI error
            result = self.service.enhance_file_frontmatter(
                markdown_file, apply_changes=True
            )

            # Verify enhancement still succeeded (without AI suggestions)
            assert result.success

            # Verify AI service was called but failed gracefully
            mock_llm_service.suggest_metadata.assert_called_once()

    def test_enhance_file_frontmatter_without_ai_service(self, tmp_path):
        """Test frontmatter enhancement without AI service."""
        # Create test file
        test_file = tmp_path / "test.md"
        test_content = "---\ntitle: Test\n---\n# Test"
        test_file.write_text(test_content)

        # Create MarkdownFile object
        markdown_file = MarkdownFile(
            path=test_file, frontmatter=Frontmatter(title="Test"), content=test_content
        )

        # Don't set LLM service (should be None by default)
        assert self.service.llm_service is None

        # Mock content analyzer
        with patch.object(self.service, "content_analyzer") as mock_analyzer:
            mock_analysis_result = Mock()
            mock_analysis_result.improvements = []
            mock_analyzer.analyze_file.return_value = mock_analysis_result

            # Enhance frontmatter
            result = self.service.enhance_file_frontmatter(
                markdown_file, apply_changes=True
            )

            # Verify enhancement succeeded without AI
            assert result.success

            # Verify no AI-related changes were applied
            ai_changes = [
                change for change in result.changes_applied if "AI-suggested" in change
            ]
            assert len(ai_changes) == 0

    def test_enhance_file_frontmatter_ai_partial_suggestions(self, tmp_path):
        """Test frontmatter enhancement with partial AI suggestions."""
        # Create test file with existing tags and aliases
        test_file = tmp_path / "test.md"
        test_content = """---
title: Test Note
tags: [existing-tag]
aliases: [Existing Alias]
---

# Test Note
Content about programming and software development.
"""
        test_file.write_text(test_content)

        # Create MarkdownFile object
        markdown_file = MarkdownFile(
            path=test_file,
            frontmatter=Frontmatter(
                title="Test Note", tags=["existing-tag"], aliases=["Existing Alias"]
            ),
            content=test_content,
        )

        # Mock LLM service with partial suggestions
        mock_llm_service = Mock()
        mock_metadata_suggestion = MetadataSuggestion(
            suggested_tags=["programming", "existing-tag"],  # One duplicate
            suggested_aliases=["Programming Guide"],  # New alias
            suggested_description=None,  # No description suggestion
            confidence_scores={"tags": 0.8, "aliases": 0.7, "description": 0.0},
        )
        mock_llm_service.suggest_metadata.return_value = mock_metadata_suggestion

        # Set LLM service
        self.service.set_llm_service(mock_llm_service)

        # Mock content analyzer
        with patch.object(self.service, "content_analyzer") as mock_analyzer:
            mock_analysis_result = Mock()
            mock_analysis_result.improvements = []
            mock_analyzer.analyze_file.return_value = mock_analysis_result

            # Enhance frontmatter
            result = self.service.enhance_file_frontmatter(
                markdown_file, apply_changes=True
            )

            # Verify enhancement succeeded
            assert result.success

            # Verify only new suggestions were added
            enhanced_fm = result.enhanced_frontmatter
            tags = enhanced_fm.get("tags", [])
            aliases = enhanced_fm.get("aliases", [])

            # Should have both existing and new tags
            assert "existing-tag" in tags
            assert "programming" in tags

            # Should have both existing and new aliases
            assert "Existing Alias" in aliases
            assert "Programming Guide" in aliases

            # Should not have description since AI didn't suggest one
            assert "description" not in enhanced_fm or not enhanced_fm.get(
                "description"
            )

    def test_enhance_file_frontmatter_ai_empty_suggestions(self, tmp_path):
        """Test frontmatter enhancement when AI returns empty suggestions."""
        # Create test file
        test_file = tmp_path / "test.md"
        test_content = "---\ntitle: Test\n---\n# Test"
        test_file.write_text(test_content)

        # Create MarkdownFile object
        markdown_file = MarkdownFile(
            path=test_file, frontmatter=Frontmatter(title="Test"), content=test_content
        )

        # Mock LLM service with empty suggestions
        mock_llm_service = Mock()
        mock_metadata_suggestion = MetadataSuggestion(
            suggested_tags=[],
            suggested_aliases=[],
            suggested_description=None,
            confidence_scores={"tags": 0.0, "aliases": 0.0, "description": 0.0},
        )
        mock_llm_service.suggest_metadata.return_value = mock_metadata_suggestion

        # Set LLM service
        self.service.set_llm_service(mock_llm_service)

        # Mock content analyzer
        with patch.object(self.service, "content_analyzer") as mock_analyzer:
            mock_analysis_result = Mock()
            mock_analysis_result.improvements = []
            mock_analyzer.analyze_file.return_value = mock_analysis_result

            # Enhance frontmatter
            result = self.service.enhance_file_frontmatter(
                markdown_file, apply_changes=True
            )

            # Verify enhancement succeeded
            assert result.success

            # Verify no AI-related changes were applied due to empty suggestions
            ai_changes = [
                change for change in result.changes_applied if "AI-suggested" in change
            ]
            assert len(ai_changes) == 0

    def test_enhance_vault_frontmatter_with_ai(self, tmp_path):
        """Test vault-wide frontmatter enhancement with AI."""
        # Create test vault with multiple files
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        # Create test files
        file1 = vault_path / "file1.md"
        file1.write_text("---\ntitle: File 1\n---\n# Machine Learning")

        file2 = vault_path / "file2.md"
        file2.write_text("---\ntitle: File 2\n---\n# Data Science")

        # Create MarkdownFile objects
        files = [
            MarkdownFile(
                path=file1,
                frontmatter=Frontmatter(title="File 1"),
                content="---\ntitle: File 1\n---\n# Machine Learning",
            ),
            MarkdownFile(
                path=file2,
                frontmatter=Frontmatter(title="File 2"),
                content="---\ntitle: File 2\n---\n# Data Science",
            ),
        ]

        # Mock LLM service
        mock_llm_service = Mock()
        mock_metadata_suggestion = MetadataSuggestion(
            suggested_tags=["ai", "tech"],
            suggested_aliases=["Tech Note"],
            suggested_description="Technical content",
            confidence_scores={"tags": 0.8, "aliases": 0.7, "description": 0.9},
        )
        mock_llm_service.suggest_metadata.return_value = mock_metadata_suggestion

        # Set LLM service
        self.service.set_llm_service(mock_llm_service)

        # Mock content analyzer
        with patch.object(self.service, "content_analyzer") as mock_analyzer:
            mock_analysis_result = Mock()
            mock_analysis_result.improvements = []
            mock_analyzer.analyze_file.return_value = mock_analysis_result

            # Enhance vault frontmatter
            results = self.service.enhance_vault_frontmatter(files, apply_changes=True)

            # Verify all files were processed
            assert len(results) == 2

            # Verify all enhancements succeeded
            for result in results:
                assert result.success
                assert result.improvements_made > 0

                # Check for AI suggestions in changes
                ai_changes = [
                    change
                    for change in result.changes_applied
                    if "AI-suggested" in change
                ]
                assert len(ai_changes) > 0

            # Verify LLM service was called for each file
            assert mock_llm_service.suggest_metadata.call_count == 2

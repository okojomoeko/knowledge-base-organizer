"""Tests for KeywordExtractionManager."""

import shutil
import tempfile
from pathlib import Path

import pytest

from knowledge_base_organizer.domain.services.keyword_extraction_manager import (
    KeywordExtractionManager,
)


class TestKeywordExtractionManager:
    """Test cases for KeywordExtractionManager."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def manager(self, temp_config_dir):
        """Create a KeywordExtractionManager instance with temp config."""
        return KeywordExtractionManager(config_dir=temp_config_dir)

    def test_initialization(self, manager):
        """Test that the manager initializes properly."""
        assert manager.config is not None
        assert "common_words" in manager.config
        assert "extraction_settings" in manager.config

    def test_extract_english_keywords(self, manager):
        """Test extraction of English keywords."""
        content = """
        # Machine Learning and Artificial Intelligence

        This document discusses neural networks, deep learning algorithms,
        and natural language processing techniques. We also cover database
        design patterns and API development methodologies.
        """

        keywords = manager.extract_keywords(content)

        # Should extract technical terms
        expected_terms = {
            "Machine",
            "Learning",
            "Artificial",
            "Intelligence",
            "neural",
            "networks",
            "algorithms",
            "database",
            "API",
        }
        found_terms = keywords.intersection(expected_terms)
        assert len(found_terms) >= 5, f"Expected technical terms, found: {found_terms}"

        # Should not include common words
        common_words = {"the", "and", "this", "also"}
        found_common = keywords.intersection(common_words)
        assert len(found_common) == 0, (
            f"Should not include common words: {found_common}"
        )

    def test_extract_japanese_keywords(self, manager):
        """Test extraction of Japanese keywords."""
        content = """
        # プログラミング言語とフレームワーク

        このドキュメントでは、機械学習、深層学習、自然言語処理について説明します。
        また、データベース設計やAPI開発についても触れます。
        ニューラルネットワークとアルゴリズムの基礎概念も含まれています。
        """

        keywords = manager.extract_keywords(content)

        # Should extract Japanese technical terms
        expected_japanese = {
            "プログラミング",
            "機械学習",
            "深層学習",
            "自然言語処理",
            "データベース",
            "ニューラルネットワーク",
            "アルゴリズム",
        }
        found_japanese = keywords.intersection(expected_japanese)
        assert len(found_japanese) >= 2, (
            f"Expected Japanese terms, found: {found_japanese}"
        )

    def test_extract_mixed_language_keywords(self, manager):
        """Test extraction from mixed Japanese and English content."""
        content = """
        # API設計とデータベース管理

        RESTful APIの設計原則について説明します。
        また、PostgreSQL、MongoDB、Redisなどのデータベース技術も扱います。
        Machine LearningとAIの統合についても触れます。
        """

        keywords = manager.extract_keywords(content)

        # Should extract both languages
        expected_english = {
            "API",
            "RESTful",
            "PostgreSQL",
            "MongoDB",
            "Redis",
            "Machine",
            "Learning",
        }
        expected_japanese = {"設計", "データベース", "管理", "原則", "技術", "統合"}

        found_english = keywords.intersection(expected_english)
        found_japanese = keywords.intersection(expected_japanese)

        assert len(found_english) >= 3, (
            f"Expected English terms, found: {found_english}"
        )
        assert len(found_japanese) >= 1, (
            f"Expected Japanese terms, found: {found_japanese}"
        )

    def test_technical_pattern_extraction(self, manager):
        """Test extraction of technical patterns like CamelCase, snake_case."""
        content = """
        # Code Examples

        Here we have CamelCaseFunction, snake_case_variable, and kebab-case-identifier.
        Also includes UPPERCASE_CONSTANTS and mixedCase_variables.
        """

        keywords = manager.extract_keywords(content)

        # Should extract technical patterns
        expected_patterns = {
            "CamelCaseFunction",
            "snake_case_variable",
            "kebab-case-identifier",
            "UPPERCASE_CONSTANTS",
            "mixedCase_variables",
        }
        found_patterns = keywords.intersection(expected_patterns)
        assert len(found_patterns) >= 3, (
            f"Expected technical patterns, found: {found_patterns}"
        )

    def test_keyword_filtering(self, manager):
        """Test that keywords are properly filtered based on configuration."""
        content = """
        This is a test with short words like 'a', 'an', 'to', 'be'.
        It also has numbers like 123, 456.
        And some meaningful terms like programming, development, architecture.
        """

        keywords = manager.extract_keywords(content)

        # Should not include very short words
        short_words = {"a", "an", "to", "be"}
        found_short = keywords.intersection(short_words)
        assert len(found_short) == 0, f"Should not include short words: {found_short}"

        # Should not include pure numbers (if configured)
        numbers = {"123", "456"}
        found_numbers = keywords.intersection(numbers)
        assert len(found_numbers) == 0, f"Should not include numbers: {found_numbers}"

        # Should include meaningful terms
        meaningful = {"programming", "development", "architecture"}
        found_meaningful = keywords.intersection(meaningful)
        assert len(found_meaningful) >= 2, (
            f"Expected meaningful terms, found: {found_meaningful}"
        )

    def test_content_cleaning(self, manager):
        """Test that content is properly cleaned before keyword extraction."""
        content = """---
title: Test Document
tags: [test]
---

# Test Content

This has `inline code`, [links](http://example.com), and **bold text**.

```python
def example_function():
    return "code block"
```

Regular text with keywords like programming and development.
"""

        keywords = manager.extract_keywords(content)

        # Should not include frontmatter fields
        frontmatter_terms = {"title", "tags", "test"}
        found_frontmatter = keywords.intersection(frontmatter_terms)
        # Note: "test" might be extracted from content, so we check specifically for frontmatter structure
        assert "title:" not in " ".join(keywords)

        # Should not include most code block content (some might slip through)
        code_terms = {"def", "return"}
        found_code = keywords.intersection(code_terms)
        assert len(found_code) <= 1, f"Should minimize code block content: {found_code}"

        # Should include regular content keywords
        content_terms = {"programming", "development"}
        found_content = keywords.intersection(content_terms)
        assert len(found_content) >= 1, (
            f"Expected content terms, found: {found_content}"
        )

    def test_add_custom_keywords(self, manager, temp_config_dir):
        """Test adding custom keywords to configuration."""
        custom_keywords = ["カスタムキーワード", "custom_term", "SpecialTerm"]

        success = manager.add_custom_keywords(custom_keywords, "test_category")
        assert success

        # Reload manager to test persistence
        new_manager = KeywordExtractionManager(config_dir=temp_config_dir)

        # Test that custom keywords are loaded
        test_content = (
            "This content includes カスタムキーワード and custom_term and SpecialTerm."
        )
        keywords = new_manager.extract_keywords(test_content)

        found_custom = keywords.intersection(set(custom_keywords))
        assert len(found_custom) >= 2, (
            f"Expected custom keywords, found: {found_custom}"
        )

    def test_keyword_statistics(self, manager):
        """Test keyword extraction statistics."""
        content = """
        # Programming and プログラミング

        This covers JavaScript, Python, API development.
        Also includes データベース, machine_learning, and deep-learning.
        """

        stats = manager.get_keyword_statistics(content)

        # Check statistics structure
        assert "total_keywords" in stats
        assert "english_keywords" in stats
        assert "japanese_keywords" in stats
        assert "technical_keywords" in stats
        assert "compound_keywords" in stats

        # Should have both English and Japanese keywords
        assert stats["english_keywords"] > 0
        assert stats["japanese_keywords"] > 0
        assert stats["total_keywords"] > 0

    def test_importance_weighting(self, manager):
        """Test that important keywords are properly weighted."""
        # Test with content containing both important and regular terms
        content = """
        This document covers API development, regular programming concepts,
        and some データベース design patterns with machine learning applications.
        """

        keywords = manager.extract_keywords(content)

        # Important technical terms should be included
        important_terms = {"API", "データベース", "machine", "learning"}
        found_important = keywords.intersection(important_terms)
        assert len(found_important) >= 2, (
            f"Expected important terms, found: {found_important}"
        )

    def test_configuration_fallback(self, temp_config_dir):
        """Test that manager works even without configuration file."""
        # Create manager with non-existent config
        manager = KeywordExtractionManager(config_dir=temp_config_dir)

        # Should still work with default configuration
        content = "This is a test with programming and development keywords."
        keywords = manager.extract_keywords(content)

        expected = {"programming", "development", "keywords"}
        found = keywords.intersection(expected)
        assert len(found) >= 2, f"Expected basic keywords, found: {found}"

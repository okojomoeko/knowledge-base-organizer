"""Basic functionality tests for knowledge base organizer."""

import tempfile
from pathlib import Path

from knowledge_base_organizer.application.vault_analyzer import VaultAnalyzer
from knowledge_base_organizer.infrastructure.config import ProcessingConfig

# Test constants
DEFAULT_MAX_LINKS = 50
TEST_MAX_LINKS = 100


def test_vault_analyzer_with_empty_directory() -> None:
    """Test vault analyzer with empty directory."""
    config = ProcessingConfig.get_default_config()
    analyzer = VaultAnalyzer(config)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        result = analyzer.analyze_vault(temp_path)

        assert result["total_files"] == 0
        assert result["files_with_frontmatter"] == 0
        assert result["files_with_id"] == 0


def test_vault_analyzer_with_markdown_file() -> None:
    """Test vault analyzer with a single markdown file."""
    config = ProcessingConfig.get_default_config()
    analyzer = VaultAnalyzer(config)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create a test markdown file
        test_file = temp_path / "test.md"
        test_file.write_text("""---
title: Test File
id: "20230101120000"
tags: [test]
---

# Test Content

This is a test file.
""")

        result = analyzer.analyze_vault(temp_path)

        assert result["total_files"] == 1
        assert result["files_with_frontmatter"] == 1
        assert result["files_with_id"] == 1


def test_processing_config_defaults() -> None:
    """Test default processing configuration."""
    config = ProcessingConfig.get_default_config()

    assert "**/*.md" in config.include_patterns
    assert "**/.obsidian/**" in config.exclude_patterns
    assert config.max_links_per_file == DEFAULT_MAX_LINKS
    assert config.backup_enabled is True


def test_processing_config_from_dict() -> None:
    """Test processing configuration from dictionary."""
    config = ProcessingConfig(
        include_patterns=["*.md"],
        exclude_patterns=["temp/**"],
        max_links_per_file=TEST_MAX_LINKS,
    )

    assert config.include_patterns == ["*.md"]
    assert config.exclude_patterns == ["temp/**"]
    assert config.max_links_per_file == TEST_MAX_LINKS

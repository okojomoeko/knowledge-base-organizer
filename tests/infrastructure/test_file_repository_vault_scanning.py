"""Tests for FileRepository vault scanning functionality."""

import tempfile
from pathlib import Path

import pytest

from knowledge_base_organizer.domain.models import MarkdownFile
from knowledge_base_organizer.infrastructure.config import ProcessingConfig
from knowledge_base_organizer.infrastructure.file_repository import FileRepository


class TestFileRepositoryVaultScanning:
    """Test FileRepository vault scanning with include/exclude patterns."""

    def test_load_vault_recursive_discovery(self) -> None:
        """Test recursive markdown file discovery."""
        config = ProcessingConfig.get_default_config()
        repo = FileRepository(config)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create nested directory structure with markdown files
            (temp_path / "subdir1").mkdir()
            (temp_path / "subdir1" / "subdir2").mkdir()

            # Create markdown files at different levels
            files_to_create = [
                temp_path / "root.md",
                temp_path / "subdir1" / "level1.md",
                temp_path / "subdir1" / "subdir2" / "level2.md",
            ]

            for file_path in files_to_create:
                file_path.write_text("""---
title: Test File
id: "20230101120000"
---

# Test Content
""")

            # Create non-markdown files (should be ignored)
            (temp_path / "readme.txt").write_text("Not markdown")
            (temp_path / "subdir1" / "config.json").write_text("{}")

            # Load vault
            markdown_files = repo.load_vault(temp_path)

            # Should find all 3 markdown files
            expected_files = 3
            assert len(markdown_files) == expected_files

            # Check that all files are MarkdownFile instances
            for file in markdown_files:
                assert isinstance(file, MarkdownFile)
                assert file.frontmatter.title == "Test File"
                assert file.frontmatter.id == "20230101120000"

    def test_load_vault_with_exclude_patterns(self) -> None:
        """Test vault loading with exclude patterns."""
        config = ProcessingConfig(
            include_patterns=["**/*.md"],
            exclude_patterns=["**/temp/**", "**/draft/**"],
        )
        repo = FileRepository(config)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create directories
            (temp_path / "notes").mkdir()
            (temp_path / "temp").mkdir()
            (temp_path / "draft").mkdir()

            # Create markdown files
            files_to_create = [
                (temp_path / "notes" / "note1.md", True),  # Should be included
                (temp_path / "temp" / "temp1.md", False),  # Should be excluded
                (temp_path / "draft" / "draft1.md", False),  # Should be excluded
                (temp_path / "regular.md", True),  # Should be included
            ]

            for file_path, _should_include in files_to_create:
                file_path.write_text("""---
title: Test File
---

# Content
""")

            # Load vault
            markdown_files = repo.load_vault(temp_path)

            # Should only find files not in excluded directories
            expected_count = sum(
                1 for _, should_include in files_to_create if should_include
            )
            assert len(markdown_files) == expected_count

            # Check that excluded files are not present
            file_paths = {file.path.name for file in markdown_files}
            assert "note1.md" in file_paths
            assert "regular.md" in file_paths
            assert "temp1.md" not in file_paths
            assert "draft1.md" not in file_paths

    def test_load_vault_with_custom_include_patterns(self) -> None:
        """Test vault loading with custom include patterns."""
        config = ProcessingConfig(
            include_patterns=["notes/*.md", "docs/**/*.md"],
            exclude_patterns=[],
        )
        repo = FileRepository(config)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create directories
            (temp_path / "notes").mkdir()
            (temp_path / "docs").mkdir()
            (temp_path / "docs" / "api").mkdir()
            (temp_path / "other").mkdir()

            # Create markdown files
            files_to_create = [
                (temp_path / "notes" / "note1.md", True),  # Matches notes/*.md
                (temp_path / "docs" / "doc1.md", True),  # Matches docs/**/*.md
                (temp_path / "docs" / "api" / "api1.md", True),  # Matches docs/**/*.md
                (temp_path / "other" / "other1.md", False),  # No matching pattern
                (temp_path / "root.md", False),  # No matching pattern
            ]

            for file_path, _should_include in files_to_create:
                file_path.write_text("""---
title: Test File
---

# Content
""")

            # Load vault
            markdown_files = repo.load_vault(temp_path)

            # Should only find files matching include patterns
            expected_count = sum(
                1 for _, should_include in files_to_create if should_include
            )
            assert len(markdown_files) == expected_count

            file_paths = {file.path.name for file in markdown_files}
            assert "note1.md" in file_paths
            assert "doc1.md" in file_paths
            assert "api1.md" in file_paths
            assert "other1.md" not in file_paths
            assert "root.md" not in file_paths

    def test_load_vault_with_obsidian_exclusions(self) -> None:
        """Test vault loading with typical Obsidian exclusions."""
        config = ProcessingConfig.get_default_config()  # Includes .obsidian exclusion
        repo = FileRepository(config)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create Obsidian-style directory structure
            (temp_path / ".obsidian").mkdir()
            (temp_path / ".obsidian" / "plugins").mkdir()
            (temp_path / "notes").mkdir()

            # Create files
            files_to_create = [
                (temp_path / "notes" / "note1.md", True),  # Should be included
                (temp_path / ".obsidian" / "config.md", False),  # Should be excluded
                (
                    temp_path / ".obsidian" / "plugins" / "plugin.md",
                    False,
                ),  # Should be excluded
            ]

            for file_path, _should_include in files_to_create:
                file_path.write_text("""---
title: Test File
---

# Content
""")

            # Load vault
            markdown_files = repo.load_vault(temp_path)

            # Should only find files not in .obsidian directory
            expected_count = sum(
                1 for _, should_include in files_to_create if should_include
            )
            assert len(markdown_files) == expected_count

            file_paths = {file.path.name for file in markdown_files}
            assert "note1.md" in file_paths
            assert "config.md" not in file_paths
            assert "plugin.md" not in file_paths

    def test_load_vault_error_handling(self) -> None:
        """Test vault loading with error handling for malformed files."""
        config = ProcessingConfig.get_default_config()
        repo = FileRepository(config)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create files with various issues
            files_to_create = [
                (
                    temp_path / "valid.md",
                    """---
title: Valid File
---

# Content
""",
                ),
                (
                    temp_path / "invalid_yaml.md",
                    """---
title: Invalid File
invalid_yaml: [unclosed
---

# Content
""",
                ),
                (temp_path / "empty.md", ""),
                (temp_path / "no_frontmatter.md", "# Just content"),
            ]

            for file_path, content in files_to_create:
                file_path.write_text(content)

            # Load vault - should handle errors gracefully
            markdown_files = repo.load_vault(temp_path)

            # Should load all files, even those with issues
            expected_files_with_errors = 4
            assert len(markdown_files) == expected_files_with_errors

            # Find the valid file
            valid_files = [f for f in markdown_files if f.path.name == "valid.md"]
            assert len(valid_files) == 1
            assert valid_files[0].frontmatter.title == "Valid File"

            # Files with issues should have empty/default frontmatter
            invalid_files = [
                f for f in markdown_files if f.path.name == "invalid_yaml.md"
            ]
            assert len(invalid_files) == 1
            assert invalid_files[0].frontmatter.title is None

    def test_load_vault_nonexistent_path(self) -> None:
        """Test vault loading with nonexistent path."""
        config = ProcessingConfig.get_default_config()
        repo = FileRepository(config)

        nonexistent_path = Path("/nonexistent/path")

        with pytest.raises(ValueError, match="Vault path does not exist"):
            repo.load_vault(nonexistent_path)

    def test_should_include_file_logic(self) -> None:
        """Test the _should_include_file method logic."""
        config = ProcessingConfig(
            exclude_patterns=["**/temp/**", "**/.git/**", "**/node_modules/**"]
        )
        repo = FileRepository(config)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Test cases: (relative_path, should_include)
            test_cases = [
                ("notes/file.md", True),
                ("temp/file.md", False),
                ("project/temp/file.md", False),
                (".git/config", False),
                ("project/.git/hooks/file", False),
                ("node_modules/package/file.md", False),
                ("src/node_modules/lib/file.md", False),
                ("regular/file.md", True),
            ]

            for relative_path_str, expected in test_cases:
                file_path = temp_path / relative_path_str
                result = repo._should_include_file(file_path, temp_path)
                assert result == expected, (
                    f"Failed for {relative_path_str}: expected {expected}, got {result}"
                )

    def test_load_vault_with_file_id_extraction(self) -> None:
        """Test vault loading with proper file ID extraction."""
        config = ProcessingConfig.get_default_config()
        repo = FileRepository(config)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create files with different ID scenarios
            files_to_create = [
                # File with ID in frontmatter
                (
                    temp_path / "with_frontmatter_id.md",
                    """---
title: File with ID
id: "20230101120000"
---

# Content
""",
                ),
                # File with 14-digit filename (Obsidian timestamp)
                (
                    temp_path / "20230101120001.md",
                    """---
title: Timestamp File
---

# Content
""",
                ),
                # File with regular name, no ID
                (
                    temp_path / "regular_name.md",
                    """---
title: Regular File
---

# Content
""",
                ),
            ]

            for file_path, content in files_to_create:
                file_path.write_text(content)

            # Load vault
            markdown_files = repo.load_vault(temp_path)

            expected_files_with_ids = 3
            assert len(markdown_files) == expected_files_with_ids

            # Check ID extraction
            files_by_name = {f.path.name: f for f in markdown_files}

            # File with frontmatter ID
            frontmatter_file = files_by_name["with_frontmatter_id.md"]
            assert frontmatter_file.file_id == "20230101120000"

            # File with timestamp filename
            timestamp_file = files_by_name["20230101120001.md"]
            assert timestamp_file.file_id == "20230101120001"

            # File with no ID
            regular_file = files_by_name["regular_name.md"]
            assert regular_file.file_id is None

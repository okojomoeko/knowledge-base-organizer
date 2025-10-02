"""Integration tests for FileRepository with realistic vault structures."""

import tempfile
from pathlib import Path

from knowledge_base_organizer.infrastructure.config import ProcessingConfig
from knowledge_base_organizer.infrastructure.file_repository import FileRepository

# Test constants
EXPECTED_FILES_COUNT = 4
EXPECTED_WIKI_LINKS_COUNT = 2


class TestVaultIntegration:
    """Integration tests for vault loading with realistic structures."""

    def _create_directories(self, vault_path: Path) -> None:
        """Create directory structure for test vault."""
        directories = [
            "100_FleetingNotes",
            "104_Books",
            "200_PermanentNotes",
            "900_TemplaterNotes",
            ".obsidian",
            ".obsidian/plugins",
            "attachments",
            "temp",
        ]

        for dir_name in directories:
            (vault_path / dir_name).mkdir(parents=True, exist_ok=True)

    def _create_test_files(self, vault_path: Path) -> None:
        """Create test files in the vault."""
        files_to_create = [
            ("100_FleetingNotes/20230101120000.md", self._get_fleeting_note_content()),
            ("104_Books/20230101120001.md", self._get_book_note_content()),
            ("200_PermanentNotes/synthesis.md", self._get_synthesis_note_content()),
            ("900_TemplaterNotes/template.md", self._get_template_content()),
            (".obsidian/config.md", self._get_obsidian_config_content()),
            ("temp/draft.md", self._get_draft_content()),
            ("attachments/image.png", "fake image data"),
            ("README.txt", "This is not markdown"),
        ]

        for file_path, content in files_to_create:
            full_path = vault_path / file_path
            full_path.write_text(content, encoding="utf-8")

    def _get_fleeting_note_content(self) -> str:
        """Get fleeting note content."""
        return """---
title: Quick Thought
id: "20230101120000"
tags: [fleeting, idea]
date: "2023-01-01"
---

# Quick Thought

This is a fleeting note about [[20230101120001|Important Concept]].
"""

    def _get_book_note_content(self) -> str:
        """Get book note content."""
        return """---
title: Important Concept
id: "20230101120001"
aliases: [concept, key-idea]
tags: [book, concept]
author: John Doe
isbn13: "9781234567890"
---

# Important Concept

This concept is referenced by many other notes.

See also: [External Link](https://example.com)
"""

    def _get_synthesis_note_content(self) -> str:
        """Get synthesis note content."""
        return """---
title: Synthesis Note
tags: [synthesis, permanent]
---

# Synthesis Note

This note synthesizes ideas from:
- [[20230101120000]]
- [[20230101120001|Important Concept]]

[ref1|Reference]: /path/to/ref "Reference Title"
"""

    def _get_template_content(self) -> str:
        """Get template content."""
        return """---
title: Template Note
template: true
---

# Template

This is a template with <% tp.file.cursor(1) %> variables.
"""

    def _get_obsidian_config_content(self) -> str:
        """Get Obsidian config content."""
        return """---
title: Obsidian Config
---

# Config
"""

    def _get_draft_content(self) -> str:
        """Get draft content."""
        return """---
title: Draft Note
---

# Draft
"""

    def create_realistic_vault_structure(self, vault_path: Path) -> None:
        """Create a realistic Obsidian vault structure for testing."""
        self._create_directories(vault_path)
        self._create_test_files(vault_path)

    def test_realistic_vault_loading(self) -> None:
        """Test loading a realistic vault structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_path = Path(temp_dir)

            # Create realistic vault structure
            self.create_realistic_vault_structure(vault_path)

            # Configure FileRepository with typical Obsidian exclusions
            config = ProcessingConfig(
                include_patterns=["**/*.md"],
                exclude_patterns=["**/.obsidian/**", "**/temp/**"],
            )

            repo = FileRepository(config)

            # Load vault
            markdown_files = repo.load_vault(vault_path)

            # Analyze results
            files_by_path = {
                str(f.path.relative_to(vault_path)): f for f in markdown_files
            }

            expected_files = [
                "100_FleetingNotes/20230101120000.md",
                "104_Books/20230101120001.md",
                "200_PermanentNotes/synthesis.md",
                "900_TemplaterNotes/template.md",
            ]

            excluded_files = [
                ".obsidian/config.md",
                "temp/draft.md",
            ]

            # Verify expected behavior
            assert len(markdown_files) == EXPECTED_FILES_COUNT

            # Check that all expected files are present
            for expected_file in expected_files:
                assert expected_file in files_by_path, (
                    f"Missing expected file: {expected_file}"
                )

            # Check that excluded files are not present
            for excluded_file in excluded_files:
                assert excluded_file not in files_by_path, (
                    f"Found excluded file: {excluded_file}"
                )

            # Verify file content and metadata
            self._verify_file_contents(files_by_path)

    def _verify_file_contents(self, files_by_path: dict[str, object]) -> None:
        """Verify the contents of loaded files."""
        # Verify fleeting note
        fleeting_note = files_by_path["100_FleetingNotes/20230101120000.md"]
        assert fleeting_note.frontmatter.title == "Quick Thought"
        assert fleeting_note.file_id == "20230101120000"
        assert len(fleeting_note.wiki_links) == 1
        assert fleeting_note.wiki_links[0].target_id == "20230101120001"
        assert fleeting_note.wiki_links[0].alias == "Important Concept"

        # Verify book note
        book_note = files_by_path["104_Books/20230101120001.md"]
        assert book_note.frontmatter.title == "Important Concept"
        assert book_note.file_id == "20230101120001"
        assert "concept" in book_note.frontmatter.aliases
        assert len(book_note.regular_links) == 1
        assert book_note.regular_links[0].url == "https://example.com"

        # Verify synthesis note
        synthesis_note = files_by_path["200_PermanentNotes/synthesis.md"]
        assert synthesis_note.frontmatter.title == "Synthesis Note"
        assert len(synthesis_note.wiki_links) == EXPECTED_WIKI_LINKS_COUNT
        assert len(synthesis_note.link_reference_definitions) == 1
        assert synthesis_note.link_reference_definitions[0].id == "ref1"

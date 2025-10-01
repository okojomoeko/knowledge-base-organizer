"""Tests for MarkdownFile entity and frontmatter parsing."""

import tempfile
from pathlib import Path

from knowledge_base_organizer.domain.models import Frontmatter, MarkdownFile
from knowledge_base_organizer.infrastructure.config import ProcessingConfig
from knowledge_base_organizer.infrastructure.file_repository import FileRepository

# Test constants
EXPECTED_WIKI_LINKS = 2
EXPECTED_REGULAR_LINKS = 2
EXPECTED_LINK_REFS = 2
FIRST_WIKI_LINE = 3
SECOND_WIKI_LINE = 4
FIRST_REGULAR_LINE = 3


class TestMarkdownFile:
    """Test MarkdownFile entity functionality."""

    def test_extract_links_wiki_links(self) -> None:
        """Test WikiLink extraction from content."""
        content = """# Test File

This is a [[20230101120000]] link.
And this is a [[20230101120001|Custom Alias]] link.
"""

        markdown_file = MarkdownFile(
            path=Path("test.md"),
            frontmatter=Frontmatter(),
            content=content,
        )

        markdown_file.extract_links()

        assert len(markdown_file.wiki_links) == EXPECTED_WIKI_LINKS

        # First link
        assert markdown_file.wiki_links[0].target_id == "20230101120000"
        assert markdown_file.wiki_links[0].alias is None
        assert markdown_file.wiki_links[0].line_number == FIRST_WIKI_LINE

        # Second link
        assert markdown_file.wiki_links[1].target_id == "20230101120001"
        assert markdown_file.wiki_links[1].alias == "Custom Alias"
        assert markdown_file.wiki_links[1].line_number == SECOND_WIKI_LINE

    def test_extract_links_regular_links(self) -> None:
        """Test regular markdown link extraction."""
        content = """# Test File

Check out [Google](https://google.com) for search.
Also see [Local File](./local.md) for more info.
"""

        markdown_file = MarkdownFile(
            path=Path("test.md"),
            frontmatter=Frontmatter(),
            content=content,
        )

        markdown_file.extract_links()

        assert len(markdown_file.regular_links) == EXPECTED_REGULAR_LINKS

        # First link
        assert markdown_file.regular_links[0].text == "Google"
        assert markdown_file.regular_links[0].url == "https://google.com"
        assert markdown_file.regular_links[0].line_number == FIRST_REGULAR_LINE

        # Second link
        assert markdown_file.regular_links[1].text == "Local File"
        assert markdown_file.regular_links[1].url == "./local.md"

    def test_extract_links_reference_definitions(self) -> None:
        """Test Link Reference Definition extraction."""
        content = """# Test File

[note1|My Note]: /path/to/note "Note Title"
[note2|Another]: /another/path "Another Title"

Some content here.
"""

        markdown_file = MarkdownFile(
            path=Path("test.md"),
            frontmatter=Frontmatter(),
            content=content,
        )

        markdown_file.extract_links()

        assert len(markdown_file.link_reference_definitions) == EXPECTED_LINK_REFS

        # First definition
        ref1 = markdown_file.link_reference_definitions[0]
        assert ref1.id == "note1"
        assert ref1.alias == "My Note"
        assert ref1.path == "/path/to/note"
        assert ref1.title == "Note Title"

        # Second definition
        ref2 = markdown_file.link_reference_definitions[1]
        assert ref2.id == "note2"
        assert ref2.alias == "Another"
        assert ref2.path == "/another/path"
        assert ref2.title == "Another Title"

    def test_validate_frontmatter_valid(self) -> None:
        """Test frontmatter validation with valid data."""
        frontmatter = Frontmatter(
            title="Test File",
            tags=["test", "example"],
            id="20230101120000",
        )

        markdown_file = MarkdownFile(
            path=Path("test.md"),
            frontmatter=frontmatter,
            content="# Test content",
        )

        schema = {
            "required": ["title", "id"],
            "properties": {
                "title": {"type": "string"},
                "tags": {"type": "array"},
                "id": {"type": "string"},
            },
        }

        result = markdown_file.validate_frontmatter(schema)

        assert result["is_valid"] is True
        assert len(result["missing_fields"]) == 0
        assert len(result["invalid_fields"]) == 0

    def test_validate_frontmatter_missing_fields(self) -> None:
        """Test frontmatter validation with missing required fields."""
        frontmatter = Frontmatter(title="Test File")

        markdown_file = MarkdownFile(
            path=Path("test.md"),
            frontmatter=frontmatter,
            content="# Test content",
        )

        schema = {
            "required": ["title", "id", "tags"],
            "properties": {
                "title": {"type": "string"},
                "id": {"type": "string"},
                "tags": {"type": "array"},
            },
        }

        result = markdown_file.validate_frontmatter(schema)

        assert result["is_valid"] is False
        assert "id" in result["missing_fields"]
        assert "tags" in result["missing_fields"]
        assert "title" not in result["missing_fields"]


class TestFileRepositoryFrontmatterParsing:
    """Test enhanced frontmatter parsing in FileRepository."""

    def test_parse_frontmatter_with_variations(self) -> None:
        """Test frontmatter parsing with field name variations."""
        content = """---
title: Test File
tag: example
alias: test-alias
created: 2023-01-01
published: true
---

# Content here
"""

        config = ProcessingConfig.get_default_config()
        repo = FileRepository(config)

        frontmatter, _body = repo._parse_frontmatter(content)

        assert frontmatter.title == "Test File"
        assert frontmatter.tags == ["example"]  # Normalized from 'tag'
        assert frontmatter.aliases == ["test-alias"]  # Normalized from 'alias'
        assert frontmatter.publish is True  # Normalized from 'published'

    def test_parse_frontmatter_with_plus_delimiters(self) -> None:
        """Test frontmatter parsing with +++ delimiters."""
        content = """+++
title: Test File
tags: [test, example]
+++

# Content here
"""

        config = ProcessingConfig.get_default_config()
        repo = FileRepository(config)

        frontmatter, _body = repo._parse_frontmatter(content)

        assert frontmatter.title == "Test File"
        assert frontmatter.tags == ["test", "example"]
        assert "# Content here" in _body

    def test_parse_frontmatter_with_yaml_error(self) -> None:
        """Test frontmatter parsing with YAML syntax error."""
        content = """---
title: Test File
invalid_yaml: [unclosed list
tags: [test]
---

# Content here
"""

        config = ProcessingConfig.get_default_config()
        repo = FileRepository(config)

        frontmatter, _body = repo._parse_frontmatter(content)

        # Should create empty frontmatter when YAML is invalid
        assert frontmatter.title is None
        assert len(frontmatter.tags) == 0

    def test_load_file_with_links(self) -> None:
        """Test loading file and automatic link extraction."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.md"

            content = """---
title: Test File
id: "20230101120000"
---

# Test Content

This links to [[20230101120001|Another Note]].
Check out [Google](https://google.com).
"""

            test_file.write_text(content)

            config = ProcessingConfig.get_default_config()
            repo = FileRepository(config)

            markdown_file = repo.load_file(test_file)

            # Check frontmatter
            assert markdown_file.frontmatter.title == "Test File"
            assert markdown_file.frontmatter.id == "20230101120000"

            # Check links were extracted
            assert len(markdown_file.wiki_links) == 1
            assert markdown_file.wiki_links[0].target_id == "20230101120001"
            assert markdown_file.wiki_links[0].alias == "Another Note"

            assert len(markdown_file.regular_links) == 1
            assert markdown_file.regular_links[0].text == "Google"
            assert markdown_file.regular_links[0].url == "https://google.com"

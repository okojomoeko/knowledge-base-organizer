"""Tests for template schema repository."""

import tempfile
from pathlib import Path

import pytest

from src.knowledge_base_organizer.domain.models import (
    FieldType,
    Frontmatter,
    MarkdownFile,
)
from src.knowledge_base_organizer.infrastructure.config import ProcessingConfig
from src.knowledge_base_organizer.infrastructure.template_schema_repository import (
    TemplateSchemaRepository,
)


class TestTemplateSchemaRepository:
    """Test template schema repository functionality."""

    @pytest.fixture
    def temp_vault(self):
        """Create a temporary vault with template files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_path = Path(temp_dir)

            # Create template directories
            template_dir = vault_path / "900_TemplaterNotes"
            template_dir.mkdir()

            book_template_dir = vault_path / "903_BookSearchTemplates"
            book_template_dir.mkdir()

            # Create fleeting note template
            fleeting_template = template_dir / "new-fleeing-note.md"
            fleeting_template.write_text("""---
title: <% tp.file.cursor(1) %>
aliases: []
tags: []
id: <% tp.file.creation_date("YYYYMMDDHHmmss") %>
date: <% tp.file.creation_date("YYYY-MM-DD") %>
publish: false
category: ""
description: ""
---

# <% tp.file.cursor(2) %>

""")

            # Create book search template
            book_template = book_template_dir / "booksearchtemplate.md"
            book_template.write_text("""---
title: "{{title}}"
author: "{{author}}"
publisher: "{{publisher}}"
totalPage: "{{totalPage}}"
isbn13: "{{isbn13}}"
tags: [books]
id: <% tp.file.creation_date("YYYYMMDDHHmmss") %>
date: <% tp.file.creation_date("YYYY-MM-DD") %>
publish: false
---

# {{title}}

## 基本情報
- 著者: {{author}}
- 出版社: {{publisher}}
- ページ数: {{totalPage}}
- ISBN: {{isbn13}}

""")

            yield vault_path

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return ProcessingConfig.get_default_config()

    @pytest.fixture
    def repository(self, temp_vault, config):
        """Create template schema repository."""
        return TemplateSchemaRepository(temp_vault, config)

    def test_extract_schemas_from_templates(self, repository):
        """Test extracting schemas from template files."""
        schemas = repository.extract_schemas_from_templates()

        assert len(schemas) == 2
        assert "new-fleeing-note" in schemas
        assert "booksearchtemplate" in schemas

        # Test fleeting note schema
        fleeting_schema = schemas["new-fleeing-note"]
        assert fleeting_schema.template_name == "new-fleeing-note"
        assert "title" in fleeting_schema.fields
        assert "id" in fleeting_schema.fields
        assert "date" in fleeting_schema.fields

        # Test book schema
        book_schema = schemas["booksearchtemplate"]
        assert book_schema.template_name == "booksearchtemplate"
        assert "title" in book_schema.fields
        assert "author" in book_schema.fields
        assert "isbn13" in book_schema.fields

    def test_parse_template_schema_fleeting_note(self, repository, temp_vault):
        """Test parsing fleeting note template schema."""
        template_path = temp_vault / "900_TemplaterNotes" / "new-fleeing-note.md"
        schema = repository._parse_template_schema(template_path)

        assert schema is not None
        assert schema.template_name == "new-fleeing-note"

        # Check field types
        assert schema.fields["title"].field_type == FieldType.STRING
        assert schema.fields["title"].required is True
        assert schema.fields["aliases"].field_type == FieldType.ARRAY
        assert schema.fields["tags"].field_type == FieldType.ARRAY
        assert schema.fields["id"].field_type == FieldType.STRING
        assert schema.fields["date"].field_type == FieldType.DATE
        assert schema.fields["publish"].field_type == FieldType.BOOLEAN

    def test_parse_template_schema_book(self, repository, temp_vault):
        """Test parsing book template schema."""
        template_path = temp_vault / "903_BookSearchTemplates" / "booksearchtemplate.md"
        schema = repository._parse_template_schema(template_path)

        assert schema is not None
        assert schema.template_name == "booksearchtemplate"

        # Check field types
        assert schema.fields["title"].field_type == FieldType.STRING
        assert schema.fields["author"].field_type == FieldType.STRING
        assert schema.fields["publisher"].field_type == FieldType.STRING
        assert (
            schema.fields["totalPage"].field_type == FieldType.STRING
        )  # Template variable makes it string
        assert schema.fields["isbn13"].field_type == FieldType.STRING

        # Check validation patterns
        assert schema.fields["isbn13"].validation_pattern == r"^\d{13}$"

    def test_detect_template_type_by_directory(self, repository, temp_vault):
        """Test template type detection by directory."""
        # Create test files in different directories
        fleeting_dir = temp_vault / "100_FleetingNotes"
        fleeting_dir.mkdir()
        fleeting_file = fleeting_dir / "test-note.md"
        fleeting_file.write_text("---\ntitle: Test\n---\n# Test")

        book_dir = temp_vault / "104_Books"
        book_dir.mkdir()
        book_file = book_dir / "test-book.md"
        book_file.write_text("---\ntitle: Test Book\n---\n# Test Book")

        # Create MarkdownFile objects
        fleeting_md = MarkdownFile(
            path=fleeting_file,
            frontmatter=Frontmatter(title="Test"),
            content="# Test",
        )

        book_md = MarkdownFile(
            path=book_file,
            frontmatter=Frontmatter(title="Test Book"),
            content="# Test Book",
        )

        # Test detection
        assert repository.detect_template_type(fleeting_md) == "new-fleeing-note"
        assert repository.detect_template_type(book_md) == "booksearchtemplate"

    def test_detect_template_type_by_content(self, repository, temp_vault):
        """Test template type detection by content."""
        # Create test file with book-specific frontmatter
        test_file = temp_vault / "test-book.md"
        test_file.write_text(
            "---\ntitle: Test Book\nisbn13: '1234567890123'\n---\n# Test"
        )

        book_md = MarkdownFile(
            path=test_file,
            frontmatter=Frontmatter(title="Test Book", isbn13="1234567890123"),
            content="# Test Book",
        )

        # Test detection
        assert repository.detect_template_type(book_md) == "booksearchtemplate"

    def test_field_type_determination(self, repository):
        """Test field type determination logic."""
        # Test string field
        field_type = repository._determine_field_type("test", None)
        assert field_type == FieldType.STRING

        # Test boolean field
        field_type = repository._determine_field_type(False, None)
        assert field_type == FieldType.BOOLEAN

        # Test array field
        field_type = repository._determine_field_type([], None)
        assert field_type == FieldType.ARRAY

        # Test integer field
        field_type = repository._determine_field_type(42, None)
        assert field_type == FieldType.INTEGER

        # Test template variable patterns
        field_type = repository._determine_field_type(
            "", 'tp.file.creation_date("YYYY-MM-DD")'
        )
        assert field_type == FieldType.DATE

        field_type = repository._determine_field_type(
            "", 'tp.file.creation_date("YYYYMMDDHHmmss")'
        )
        assert field_type == FieldType.STRING  # ID format

    def test_required_field_detection(self, repository):
        """Test required field detection logic."""
        # Core fields should be required
        assert repository._is_field_required("title", "", None) is True
        assert repository._is_field_required("id", "", None) is True

        # Fields with template variables should be required
        assert repository._is_field_required("test", "", "tp.file.cursor(1)") is True

        # Empty/placeholder values should be optional
        assert repository._is_field_required("description", "", None) is False
        assert repository._is_field_required("category", "<placeholder>", None) is False

        # Arrays and booleans are often optional
        assert repository._is_field_required("tags", [], None) is False
        assert repository._is_field_required("publish", False, None) is False

    def test_validation_pattern_creation(self, repository):
        """Test validation pattern creation."""
        # ID field pattern
        pattern = repository._create_validation_pattern("id", FieldType.STRING)
        assert pattern == r"^\d{14}$"

        # Date field pattern
        pattern = repository._create_validation_pattern("date", FieldType.DATE)
        assert pattern == r"^\d{4}-\d{2}-\d{2}$"

        # ISBN pattern
        pattern = repository._create_validation_pattern("isbn13", FieldType.STRING)
        assert pattern == r"^\d{13}$"

        # No pattern for regular fields
        pattern = repository._create_validation_pattern("title", FieldType.STRING)
        assert pattern is None

    def test_schema_validation(self, repository):
        """Test schema validation functionality."""
        schemas = repository.extract_schemas_from_templates()
        fleeting_schema = schemas["new-fleeing-note"]

        # Test valid frontmatter
        valid_frontmatter = Frontmatter(
            title="Test Note",
            id="20230101120000",
            date="2023-01-01",
            publish=False,
            aliases=[],
            tags=[],
            category="test",
            description="A test note",
        )

        result = fleeting_schema.validate_frontmatter(valid_frontmatter)
        assert result.is_valid is True
        assert len(result.missing_fields) == 0

        # Test invalid frontmatter (missing required fields)
        invalid_frontmatter = Frontmatter(
            publish=False,
            aliases=[],
            tags=[],
        )

        result = fleeting_schema.validate_frontmatter(invalid_frontmatter)
        assert result.is_valid is False
        assert "title" in result.missing_fields

    def test_empty_vault(self, config):
        """Test behavior with empty vault."""
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_path = Path(temp_dir)
            repository = TemplateSchemaRepository(vault_path, config)

            schemas = repository.extract_schemas_from_templates()
            assert len(schemas) == 0

    def test_invalid_template_file(self, temp_vault, config):
        """Test handling of invalid template files."""
        # Create invalid template file
        template_dir = temp_vault / "900_TemplaterNotes"
        invalid_template = template_dir / "invalid-template.md"
        invalid_template.write_text("This is not a valid template file")

        repository = TemplateSchemaRepository(temp_vault, config)
        schemas = repository.extract_schemas_from_templates()

        # Should still extract valid schemas, skip invalid ones
        assert "new-fleeing-note" in schemas
        assert "booksearchtemplate" in schemas
        assert "invalid-template" not in schemas

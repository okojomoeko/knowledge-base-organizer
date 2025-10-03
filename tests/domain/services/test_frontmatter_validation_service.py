"""Tests for frontmatter validation service."""

from pathlib import Path

import pytest

from src.knowledge_base_organizer.domain.models import (
    FieldType,
    Frontmatter,
    FrontmatterSchema,
    SchemaField,
)
from src.knowledge_base_organizer.domain.services import FrontmatterValidationService


class TestFrontmatterValidationService:
    """Test frontmatter validation service."""

    @pytest.fixture
    def validation_service(self):
        """Create validation service."""
        return FrontmatterValidationService()

    @pytest.fixture
    def sample_schema(self):
        """Create sample schema for testing."""
        fields = {
            "title": SchemaField(
                name="title",
                field_type=FieldType.STRING,
                required=True,
                description="Note title",
            ),
            "id": SchemaField(
                name="id",
                field_type=FieldType.STRING,
                required=True,
                validation_pattern=r"^\d{14}$",
                description="Unique ID",
            ),
            "date": SchemaField(
                name="date",
                field_type=FieldType.DATE,
                required=True,
                validation_pattern=r"^\d{4}-\d{2}-\d{2}$",
                description="Creation date",
            ),
            "tags": SchemaField(
                name="tags",
                field_type=FieldType.ARRAY,
                required=False,
                default_value=[],
                description="Tags",
            ),
            "publish": SchemaField(
                name="publish",
                field_type=FieldType.BOOLEAN,
                required=False,
                default_value=False,
                description="Publish status",
            ),
        }

        return FrontmatterSchema(
            template_name="test-template",
            template_path=Path("test-template.md"),
            fields=fields,
            required_fields=set(),
            optional_fields=set(),
        )

    def test_validate_with_detailed_analysis_valid(
        self, validation_service, sample_schema
    ):
        """Test detailed validation with valid frontmatter."""
        frontmatter = Frontmatter(
            title="Test Note",
            id="20230101120000",
            date="2023-01-01",
            tags=["test"],
            publish=False,
        )

        result = validation_service.validate_with_detailed_analysis(
            frontmatter, sample_schema, Path("test.md")
        )

        assert result.is_valid is True
        assert len(result.missing_fields) == 0
        assert len(result.invalid_fields) == 0

    def test_validate_with_detailed_analysis_missing_fields(
        self, validation_service, sample_schema
    ):
        """Test detailed validation with missing required fields."""
        frontmatter = Frontmatter(
            tags=["test"],
            publish=False,
        )

        result = validation_service.validate_with_detailed_analysis(
            frontmatter, sample_schema, Path("test.md")
        )

        assert result.is_valid is False
        assert "title" in result.missing_fields
        assert "id" in result.missing_fields
        assert "date" in result.missing_fields

    def test_validate_with_detailed_analysis_type_errors(
        self, validation_service, sample_schema
    ):
        """Test detailed validation with type errors."""
        # Use model_construct to bypass Pydantic validation
        frontmatter = Frontmatter.model_construct(
            title="Test Note",
            id="20230101120000",
            date="2023-01-01",
            tags="should be array",  # Type error
            publish="should be boolean",  # Type error
        )

        result = validation_service.validate_with_detailed_analysis(
            frontmatter, sample_schema, Path("test.md")
        )

        assert result.is_valid is False
        assert "tags" in result.invalid_fields
        assert "publish" in result.invalid_fields

    def test_validate_with_detailed_analysis_pattern_violations(
        self, validation_service, sample_schema
    ):
        """Test detailed validation with pattern violations."""
        frontmatter = Frontmatter(
            title="Test Note",
            id="invalid_id",  # Pattern violation
            date="2023/01/01",  # Pattern violation
            tags=["test"],
            publish=False,
        )

        result = validation_service.validate_with_detailed_analysis(
            frontmatter, sample_schema, Path("test.md")
        )

        assert result.is_valid is False
        assert "id" in result.invalid_fields
        assert "date" in result.invalid_fields

    def test_generate_comprehensive_fixes_missing_fields(
        self, validation_service, sample_schema
    ):
        """Test comprehensive fix generation for missing fields."""
        frontmatter = Frontmatter(
            tags=["test"],
            publish=False,
        )

        fixes = validation_service.generate_comprehensive_fixes(
            frontmatter, sample_schema
        )

        # Should have fixes for missing required fields
        fix_fields = {fix.field_name for fix in fixes}
        assert "title" in fix_fields
        assert "id" in fix_fields
        assert "date" in fix_fields

        # Check fix types
        for fix in fixes:
            if fix.field_name in ("title", "id", "date"):
                assert fix.fix_type == "add"
                assert fix.suggested_value is not None

    def test_generate_comprehensive_fixes_type_mismatches(
        self, validation_service, sample_schema
    ):
        """Test comprehensive fix generation for type mismatches."""
        # Use model_construct to bypass Pydantic validation
        frontmatter = Frontmatter.model_construct(
            title="Test Note",
            id="20230101120000",
            date="2023-01-01",
            tags="tag1,tag2",  # String instead of array
            publish="true",  # String instead of boolean
        )

        fixes = validation_service.generate_comprehensive_fixes(
            frontmatter, sample_schema
        )

        # Should have fixes for type mismatches
        fix_fields = {fix.field_name for fix in fixes}
        assert "tags" in fix_fields
        assert "publish" in fix_fields

        # Check suggested values
        tags_fix = next(fix for fix in fixes if fix.field_name == "tags")
        assert isinstance(tags_fix.suggested_value, list)
        assert tags_fix.suggested_value == ["tag1", "tag2"]

        publish_fix = next(fix for fix in fixes if fix.field_name == "publish")
        assert isinstance(publish_fix.suggested_value, bool)
        assert publish_fix.suggested_value is True

    def test_generate_comprehensive_fixes_pattern_violations(
        self, validation_service, sample_schema
    ):
        """Test comprehensive fix generation for pattern violations."""
        frontmatter = Frontmatter(
            title="Test Note",
            id="2023/01/01 12:00:00",  # Wrong format
            date="2023/01/01",  # Wrong format
            tags=["test"],
            publish=False,
        )

        fixes = validation_service.generate_comprehensive_fixes(
            frontmatter, sample_schema
        )

        # Should have fixes for pattern violations
        fix_fields = {fix.field_name for fix in fixes}
        assert "date" in fix_fields  # Date format can be fixed

        # Check date fix
        date_fix = next(fix for fix in fixes if fix.field_name == "date")
        assert date_fix.suggested_value == "2023-01-01"

    def test_generate_comprehensive_fixes_value_improvements(
        self, validation_service, sample_schema
    ):
        """Test comprehensive fix generation for value improvements."""
        frontmatter = Frontmatter(
            title="Test Note",
            id="20230101120000",
            date="2023-01-01",
            tags=[
                "test",
                "test",
                " duplicate ",
                "duplicate",
            ],  # Duplicates and whitespace
            publish=False,
        )

        fixes = validation_service.generate_comprehensive_fixes(
            frontmatter, sample_schema
        )

        # Should have fix for tags cleanup
        tags_fix = next((fix for fix in fixes if fix.field_name == "tags"), None)
        if tags_fix:
            assert len(tags_fix.suggested_value) < len(tags_fix.current_value)
            assert "duplicate" in tags_fix.suggested_value
            assert tags_fix.suggested_value.count("duplicate") == 1

    def test_smart_default_generation(self, validation_service):
        """Test smart default value generation."""
        # Test ID field
        id_field = SchemaField(name="id", field_type=FieldType.STRING, required=True)
        default_id = validation_service._get_smart_default(id_field)
        assert isinstance(default_id, str)
        assert len(default_id) == 14
        assert default_id.isdigit()

        # Test date field
        date_field = SchemaField(name="date", field_type=FieldType.DATE, required=True)
        default_date = validation_service._get_smart_default(date_field)
        assert isinstance(default_date, str)
        assert len(default_date) == 10  # YYYY-MM-DD format

        # Test array field
        array_field = SchemaField(
            name="tags", field_type=FieldType.ARRAY, required=False
        )
        default_array = validation_service._get_smart_default(array_field)
        assert isinstance(default_array, list)
        assert len(default_array) == 0

    def test_cross_field_validation(self, validation_service, sample_schema):
        """Test cross-field validation warnings."""
        frontmatter = Frontmatter(
            title="Test Note",
            id="invalid_timestamp",  # Invalid timestamp
            date="2023-01-01",
            tags=["test"],
            publish=False,
            aliases=["Test Note"],  # Title duplicated in aliases
        )

        result = validation_service.validate_with_detailed_analysis(
            frontmatter, sample_schema, Path("test.md")
        )

        # Should have warnings about cross-field issues
        assert len(result.warnings) > 0

    def test_pattern_fix_date_format(self, validation_service):
        """Test date format fixing."""
        # Test various date formats
        assert validation_service._fix_date_format("2023/01/01") == "2023-01-01"
        assert validation_service._fix_date_format("01/01/2023") == "2023-01-01"
        assert validation_service._fix_date_format("2023.01.01") == "2023-01-01"
        assert validation_service._fix_date_format("invalid") is None

    def test_pattern_fix_id_format(self, validation_service):
        """Test ID format fixing."""
        # Test ID format fixing
        assert (
            validation_service._fix_id_format("2023-01-01-12-00-00") == "20230101120000"
        )
        assert (
            validation_service._fix_id_format("2023/01/01 12:00:00") == "20230101120000"
        )
        assert validation_service._fix_id_format("abc123") is None

    def test_clean_aliases_list(self, validation_service):
        """Test aliases list cleaning."""
        aliases = ["  test  ", "duplicate", "duplicate", "", "another"]
        cleaned = validation_service._clean_aliases_list(aliases)

        assert "test" in cleaned
        assert cleaned.count("duplicate") == 1
        assert "" not in cleaned
        assert "another" in cleaned

    def test_clean_tags_list(self, validation_service):
        """Test tags list cleaning."""
        tags = ["  Test  ", "DUPLICATE", "duplicate", "", "Another"]
        cleaned = validation_service._clean_tags_list(tags)

        assert "test" in cleaned
        assert cleaned.count("duplicate") == 1
        assert "" not in cleaned
        assert "another" in cleaned

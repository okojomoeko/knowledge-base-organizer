"""Tests for YAML type conversion service."""

from datetime import date, datetime
from pathlib import Path

from knowledge_base_organizer.domain.models import (
    FieldType,
    FrontmatterSchema,
    SchemaField,
)
from knowledge_base_organizer.domain.services.yaml_type_converter import (
    TypeConversion,
    YAMLTypeConverter,
)


class TestYAMLTypeConverter:
    """Test cases for YAMLTypeConverter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.converter = YAMLTypeConverter()

        # Create a sample schema for testing
        self.schema = FrontmatterSchema(
            template_name="test-template",
            template_path=Path("test-template.md"),
            fields={
                "id": SchemaField(
                    name="id",
                    field_type=FieldType.STRING,
                    required=True,
                ),
                "date": SchemaField(
                    name="date",
                    field_type=FieldType.STRING,
                    required=True,
                ),
                "published": SchemaField(
                    name="published",
                    field_type=FieldType.STRING,
                    required=False,
                ),
                "tags": SchemaField(
                    name="tags",
                    field_type=FieldType.ARRAY,
                    required=False,
                ),
                "publish": SchemaField(
                    name="publish",
                    field_type=FieldType.BOOLEAN,
                    required=False,
                ),
            },
            required_fields={"id", "date"},
            optional_fields={"published", "tags", "publish"},
        )

    def test_convert_integer_id_to_string(self):
        """Test conversion of integer ID to string."""
        frontmatter = {"id": 20250107123456, "title": "Test"}

        converted, conversions = self.converter.convert_frontmatter_types(
            frontmatter, self.schema
        )

        assert converted["id"] == "20250107123456"
        assert len(conversions) == 1
        assert conversions[0].field_name == "id"
        assert conversions[0].original_type == "int"
        assert conversions[0].converted_type == "str"

    def test_convert_datetime_to_iso_string(self):
        """Test conversion of datetime object to ISO string."""
        test_datetime = datetime(2025, 1, 7, 12, 34, 56)
        frontmatter = {"date": test_datetime, "id": "123"}

        converted, conversions = self.converter.convert_frontmatter_types(
            frontmatter, self.schema
        )

        assert converted["date"] == "2025-01-07T12:34:56"
        assert len(conversions) == 1
        assert conversions[0].field_name == "date"
        assert conversions[0].original_type == "datetime"
        assert conversions[0].converted_type == "str"

    def test_convert_date_to_iso_string(self):
        """Test conversion of date object to ISO string."""
        test_date = date(2025, 1, 7)
        frontmatter = {"published": test_date, "id": "123"}

        converted, conversions = self.converter.convert_frontmatter_types(
            frontmatter, self.schema
        )

        assert converted["published"] == "2025-01-07"
        assert len(conversions) == 1
        assert conversions[0].field_name == "published"
        assert conversions[0].original_type == "date"
        assert conversions[0].converted_type == "str"

    def test_convert_string_to_array(self):
        """Test conversion of string to array for array fields."""
        frontmatter = {"tags": "tag1, tag2, tag3", "id": "123"}

        converted, conversions = self.converter.convert_frontmatter_types(
            frontmatter, self.schema
        )

        assert converted["tags"] == ["tag1", "tag2", "tag3"]
        assert len(conversions) == 1
        assert conversions[0].field_name == "tags"
        assert conversions[0].original_type == "str"
        assert conversions[0].converted_type == "list"

    def test_convert_datetime_to_boolean_for_publish_field(self):
        """Test conversion of datetime to boolean for publish field."""
        test_datetime = datetime(2025, 1, 7, 12, 34, 56)
        frontmatter = {"publish": test_datetime, "id": "123"}

        converted, conversions = self.converter.convert_frontmatter_types(
            frontmatter, self.schema
        )

        assert converted["publish"] is True
        assert len(conversions) == 1
        assert conversions[0].field_name == "publish"
        assert conversions[0].original_type == "datetime"
        assert conversions[0].converted_type == "bool"

    def test_preserve_unknown_fields(self):
        """Test that unknown fields are preserved as-is."""
        frontmatter = {"id": "123", "unknown_field": "some_value"}

        converted, conversions = self.converter.convert_frontmatter_types(
            frontmatter, self.schema
        )

        assert converted["unknown_field"] == "some_value"
        assert len(conversions) == 0  # No conversions for unknown fields

    def test_no_conversion_needed(self):
        """Test that no conversion is performed when types already match."""
        frontmatter = {
            "id": "123",
            "date": "2025-01-07",
            "tags": ["tag1", "tag2"],
            "publish": False,
        }

        converted, conversions = self.converter.convert_frontmatter_types(
            frontmatter, self.schema
        )

        assert converted == frontmatter
        assert len(conversions) == 0

    def test_multiple_conversions(self):
        """Test multiple type conversions in a single operation."""
        test_datetime = datetime(2025, 1, 7, 12, 34, 56)
        frontmatter = {
            "id": 20250107123456,
            "date": test_datetime,
            "tags": "tag1, tag2",
            "publish": "true",
        }

        converted, conversions = self.converter.convert_frontmatter_types(
            frontmatter, self.schema
        )

        assert converted["id"] == "20250107123456"
        assert converted["date"] == "2025-01-07T12:34:56"
        assert converted["tags"] == ["tag1", "tag2"]
        assert converted["publish"] is True
        assert len(conversions) == 4

    def test_conversion_summary(self):
        """Test conversion summary generation."""
        conversions = [
            TypeConversion(
                field_name="id",
                original_value=123,
                original_type="int",
                converted_value="123",
                converted_type="str",
                reason="ID field converted from integer to string for consistency",
            ),
            TypeConversion(
                field_name="date",
                original_value=datetime(2025, 1, 7),
                original_type="datetime",
                converted_value="2025-01-07T00:00:00",
                converted_type="str",
                reason="Date field converted from datetime object to ISO string",
            ),
        ]

        summary = self.converter.get_conversion_summary(conversions)

        assert summary["total_conversions"] == 2
        assert "id" in summary["fields_converted"]
        assert "date" in summary["fields_converted"]
        assert "int -> str" in summary["conversion_types"]
        assert "datetime -> str" in summary["conversion_types"]

    def test_empty_conversions_summary(self):
        """Test conversion summary with no conversions."""
        summary = self.converter.get_conversion_summary([])

        assert summary["total_conversions"] == 0
        assert summary["fields_converted"] == []
        assert summary["conversion_types"] == {}

    def test_convert_to_string_with_list(self):
        """Test string conversion with list input."""
        result = self.converter._convert_to_string(["item1", "item2"])
        assert result == "item1, item2"

    def test_convert_to_string_with_boolean(self):
        """Test string conversion with boolean input."""
        assert self.converter._convert_to_string(True) == "true"
        assert self.converter._convert_to_string(False) == "false"

    def test_convert_to_array_with_single_string(self):
        """Test array conversion with single string."""
        result = self.converter._convert_to_array("single_item")
        assert result == ["single_item"]

    def test_convert_to_array_with_empty_string(self):
        """Test array conversion with empty string."""
        result = self.converter._convert_to_array("")
        assert result == []

    def test_convert_to_boolean_with_string_values(self):
        """Test boolean conversion with various string values."""
        assert self.converter._convert_to_boolean("true") is True
        assert self.converter._convert_to_boolean("yes") is True
        assert self.converter._convert_to_boolean("1") is True
        assert self.converter._convert_to_boolean("on") is True
        assert self.converter._convert_to_boolean("false") is False
        assert self.converter._convert_to_boolean("no") is False
        assert self.converter._convert_to_boolean("0") is False

    def test_convert_to_boolean_with_datetime(self):
        """Test boolean conversion with datetime object."""
        test_datetime = datetime(2025, 1, 7)
        result = self.converter._convert_to_boolean(test_datetime)
        assert result is True

    def test_get_conversion_reason_for_id_field(self):
        """Test conversion reason for ID field."""
        reason = self.converter._get_conversion_reason("id", "int", FieldType.STRING)
        assert "ID field converted from integer to string for consistency" in reason

    def test_get_conversion_reason_for_date_field(self):
        """Test conversion reason for date field."""
        reason = self.converter._get_conversion_reason(
            "date", "datetime", FieldType.STRING
        )
        assert "Date field converted from datetime object to ISO string" in reason

    def test_get_conversion_reason_for_general_field(self):
        """Test conversion reason for general field."""
        reason = self.converter._get_conversion_reason("title", "int", FieldType.STRING)
        assert "Field type converted from int to string per schema" in reason

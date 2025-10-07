"""YAML type conversion service for handling automatic YAML type conversion."""

import logging
from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict

from ..models import FieldType, FrontmatterSchema

logger = logging.getLogger(__name__)


class TypeConversion(BaseModel):
    """Record of a type conversion performed."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    field_name: str
    original_value: Any
    original_type: str
    converted_value: Any
    converted_type: str
    reason: str


class YAMLTypeConverter:
    """Service for handling automatic YAML type conversion.

    This service intelligently converts YAML types to match schema expectations,
    particularly handling cases where YAML automatically converts values to
    native Python types (integers, dates, booleans) but the schema expects
    strings or other types.
    """

    def __init__(self) -> None:
        """Initialize the YAML type converter."""
        self.conversion_rules = self._load_conversion_rules()

    def convert_frontmatter_types(
        self,
        frontmatter: dict[str, Any],
        schema: FrontmatterSchema,
    ) -> tuple[dict[str, Any], list[TypeConversion]]:
        """Convert YAML types to match schema expectations.

        Args:
            frontmatter: The frontmatter dictionary to convert
            schema: The schema to match against

        Returns:
            Tuple of (converted_frontmatter, list_of_conversions)
        """
        converted = {}
        conversions = []

        for field_name, value in frontmatter.items():
            if field_name in schema.fields:
                expected_type = schema.fields[field_name].field_type
                converted_value, conversion = self._convert_field_value(
                    field_name, value, expected_type
                )
                converted[field_name] = converted_value
                if conversion:
                    conversions.append(conversion)
                    logger.info(
                        f"Type conversion: {field_name} "
                        f"{conversion.original_type} -> {conversion.converted_type}"
                    )
            else:
                # Preserve unknown fields as-is
                converted[field_name] = value

        return converted, conversions

    def _convert_field_value(
        self,
        field_name: str,
        value: Any,
        expected_type: FieldType,
    ) -> tuple[Any, TypeConversion | None]:
        """Convert individual field value to expected type.

        Args:
            field_name: Name of the field being converted
            value: Original value to convert
            expected_type: Expected field type from schema

        Returns:
            Tuple of (converted_value, conversion_record_or_none)
        """
        original_value = value
        original_type = type(value).__name__

        # Handle None values
        if value is None:
            return None, None

        # Apply conversion rules based on field name and expected type
        converted_value = self._apply_conversion_rules(field_name, value, expected_type)

        # Create conversion record if value changed
        conversion = None
        if converted_value != original_value:
            conversion = TypeConversion(
                field_name=field_name,
                original_value=original_value,
                original_type=original_type,
                converted_value=converted_value,
                converted_type=type(converted_value).__name__,
                reason=self._get_conversion_reason(
                    field_name, original_type, expected_type
                ),
            )

        return converted_value, conversion

    def _apply_conversion_rules(
        self,
        field_name: str,
        value: Any,
        expected_type: FieldType,
    ) -> Any:
        """Apply conversion rules based on field name and expected type.

        Args:
            field_name: Name of the field
            value: Value to convert
            expected_type: Expected type from schema

        Returns:
            Converted value
        """
        # Special case: ID fields should always be strings
        if field_name == "id" and isinstance(value, int):
            return str(value)

        # Special case: Date fields - convert datetime/date objects to ISO strings
        if field_name in ("date", "published"):
            if hasattr(value, "isoformat"):
                return value.isoformat()
            if isinstance(value, date):
                return value.isoformat()

        # General type conversions based on expected type
        type_converters = {
            FieldType.STRING: (
                lambda v: not isinstance(v, str),
                self._convert_to_string,
            ),
            FieldType.ARRAY: (
                lambda v: not isinstance(v, list),
                self._convert_to_array,
            ),
            FieldType.BOOLEAN: (
                lambda v: not isinstance(v, bool),
                self._convert_to_boolean,
            ),
            FieldType.INTEGER: (
                lambda v: not isinstance(v, int),
                self._convert_to_integer,
            ),
            FieldType.NUMBER: (
                lambda v: not isinstance(v, (int, float)),
                self._convert_to_number,
            ),
        }

        if expected_type in type_converters:
            needs_conversion, converter = type_converters[expected_type]
            if needs_conversion(value):
                return converter(value)

        # No conversion needed
        return value

    def _convert_to_string(self, value: Any) -> str:
        """Convert value to string representation.

        Args:
            value: Value to convert

        Returns:
            String representation of the value
        """
        if hasattr(value, "isoformat"):
            # Handle datetime/date objects
            return value.isoformat()
        if isinstance(value, list):
            # Convert list to comma-separated string
            return ", ".join(str(item) for item in value)
        if isinstance(value, bool):
            # Convert boolean to lowercase string
            return str(value).lower()
        return str(value)

    def _convert_to_array(self, value: Any) -> list[Any]:
        """Convert value to array/list.

        Args:
            value: Value to convert

        Returns:
            List representation of the value
        """
        if isinstance(value, str):
            # Split comma-separated string into list
            if "," in value:
                return [item.strip() for item in value.split(",") if item.strip()]
            # Single string becomes single-item list
            return [value] if value.strip() else []
        # Wrap single value in list
        return [value]

    def _convert_to_boolean(self, value: Any) -> bool:
        """Convert value to boolean.

        Args:
            value: Value to convert

        Returns:
            Boolean representation of the value
        """
        if isinstance(value, str):
            return value.lower() in ("true", "yes", "1", "on")
        if hasattr(value, "isoformat"):
            # Datetime objects are considered True (published)
            return True
        return bool(value)

    def _convert_to_integer(self, value: Any) -> int:
        """Convert value to integer.

        Args:
            value: Value to convert

        Returns:
            Integer representation of the value

        Raises:
            ValueError: If conversion is not possible
        """
        if isinstance(value, str):
            # Try to parse string as integer
            return int(value)
        if isinstance(value, float):
            # Convert float to integer (truncate)
            return int(value)
        if isinstance(value, bool):
            # Convert boolean to integer (True=1, False=0)
            return int(value)
        return int(value)

    def _convert_to_number(self, value: Any) -> float:
        """Convert value to number (float).

        Args:
            value: Value to convert

        Returns:
            Float representation of the value

        Raises:
            ValueError: If conversion is not possible
        """
        if isinstance(value, str):
            # Try to parse string as float
            return float(value)
        if isinstance(value, bool):
            # Convert boolean to float (True=1.0, False=0.0)
            return float(value)
        return float(value)

    def _get_conversion_reason(
        self,
        field_name: str,
        original_type: str,
        expected_type: FieldType,
    ) -> str:
        """Get human-readable reason for the conversion.

        Args:
            field_name: Name of the field
            original_type: Original type name
            expected_type: Expected field type

        Returns:
            Human-readable conversion reason
        """
        if field_name == "id" and original_type == "int":
            return "ID field converted from integer to string for consistency"

        if field_name in ("date", "published") and original_type in (
            "date",
            "datetime",
        ):
            return f"Date field converted from {original_type} object to ISO string"

        return (
            f"Field type converted from {original_type} to {expected_type.value} "
            "per schema"
        )

    def _load_conversion_rules(self) -> dict[str, Any]:
        """Load conversion rules configuration.

        Returns:
            Dictionary of conversion rules
        """
        # Default conversion rules - could be loaded from config file in the future
        return {
            "id_fields": ["id"],
            "date_fields": ["date", "published", "created", "modified"],
            "string_fields": ["title", "description", "category"],
            "array_fields": ["tags", "aliases", "categories"],
            "boolean_fields": ["publish", "draft", "featured"],
        }

    def log_conversions(self, conversions: list[TypeConversion]) -> None:
        """Log all type conversions performed.

        Args:
            conversions: List of type conversions to log
        """
        if not conversions:
            logger.debug("No type conversions performed")
            return

        logger.info(f"Performed {len(conversions)} type conversions:")
        for conversion in conversions:
            logger.info(
                f"  {conversion.field_name}: "
                f"{conversion.original_type}({conversion.original_value}) -> "
                f"{conversion.converted_type}({conversion.converted_value}) "
                f"({conversion.reason})"
            )

    def get_conversion_summary(
        self, conversions: list[TypeConversion]
    ) -> dict[str, Any]:
        """Get summary statistics of conversions performed.

        Args:
            conversions: List of type conversions

        Returns:
            Dictionary with conversion statistics
        """
        if not conversions:
            return {
                "total_conversions": 0,
                "fields_converted": [],
                "conversion_types": {},
            }

        conversion_types = {}
        fields_converted = []

        for conversion in conversions:
            fields_converted.append(conversion.field_name)
            conversion_key = (
                f"{conversion.original_type} -> {conversion.converted_type}"
            )
            conversion_types[conversion_key] = (
                conversion_types.get(conversion_key, 0) + 1
            )

        return {
            "total_conversions": len(conversions),
            "fields_converted": list(set(fields_converted)),
            "conversion_types": conversion_types,
            "most_common_conversions": sorted(
                conversion_types.items(), key=lambda x: x[1], reverse=True
            )[:5],
        }

"""Advanced frontmatter validation service."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from ..models import (
    FieldFix,
    FieldType,
    Frontmatter,
    FrontmatterSchema,
    ValidationResult,
)


class FrontmatterValidationService:
    """Advanced service for frontmatter validation and fix suggestions."""

    def validate_with_detailed_analysis(
        self, frontmatter: Frontmatter, schema: FrontmatterSchema, file_path: Path
    ) -> ValidationResult:
        """Perform detailed validation with enhanced error reporting."""
        missing_fields = []
        invalid_fields = {}
        warnings = []
        suggested_fixes = {}

        frontmatter_dict = frontmatter.model_dump(exclude_unset=True)

        # Enhanced required field validation
        missing_fields, suggested_fixes = self._validate_required_fields(
            frontmatter_dict, schema
        )

        # Enhanced type and pattern validation
        type_errors = self._validate_field_types_and_patterns(frontmatter_dict, schema)
        invalid_fields.update(type_errors)

        # Cross-field validation
        cross_field_warnings = self._validate_cross_field_consistency(
            frontmatter_dict, schema
        )
        warnings.extend(cross_field_warnings)

        # Schema completeness warnings
        completeness_warnings = self._check_schema_completeness(
            frontmatter_dict, schema
        )
        warnings.extend(completeness_warnings)

        is_valid = not missing_fields and not invalid_fields

        return ValidationResult(
            file_path=file_path,
            template_type=schema.template_name,
            is_valid=is_valid,
            missing_fields=missing_fields,
            invalid_fields=invalid_fields,
            suggested_fixes=suggested_fixes,
            warnings=warnings,
        )

    def generate_comprehensive_fixes(
        self, frontmatter: Frontmatter, schema: FrontmatterSchema
    ) -> list[FieldFix]:
        """Generate comprehensive fix suggestions."""
        fixes = []
        frontmatter_dict = frontmatter.model_dump(exclude_unset=True)

        # Fixes for missing required fields
        fixes.extend(self._generate_missing_field_fixes(frontmatter_dict, schema))

        # Fixes for type mismatches
        fixes.extend(self._generate_type_mismatch_fixes(frontmatter_dict, schema))

        # Fixes for pattern violations
        fixes.extend(self._generate_pattern_violation_fixes(frontmatter_dict, schema))

        # Fixes for value improvements
        fixes.extend(self._generate_value_improvement_fixes(frontmatter_dict, schema))

        return fixes

    def _validate_required_fields(
        self, frontmatter_dict: dict[str, Any], schema: FrontmatterSchema
    ) -> tuple[list[str], dict[str, Any]]:
        """Validate required fields with smart defaults."""
        missing_fields = []
        suggested_fixes = {}

        for field_name in schema.required_fields:
            field_def = schema.fields[field_name]

            if field_name not in frontmatter_dict:
                missing_fields.append(field_name)
                suggested_fixes[field_name] = self._get_smart_default(field_def)
            elif not frontmatter_dict[field_name]:
                # Empty value for required field
                if field_def.field_type != FieldType.BOOLEAN:  # Boolean false is valid
                    missing_fields.append(field_name)
                    suggested_fixes[field_name] = self._get_smart_default(field_def)

        return missing_fields, suggested_fixes

    def _validate_field_types_and_patterns(
        self, frontmatter_dict: dict[str, Any], schema: FrontmatterSchema
    ) -> dict[str, str]:
        """Enhanced field type and pattern validation."""
        invalid_fields = {}

        for field_name, field_def in schema.fields.items():
            if field_name not in frontmatter_dict:
                continue

            value = frontmatter_dict[field_name]

            # Type validation with detailed error messages
            if not self._validate_field_type(value, field_def.field_type):
                invalid_fields[field_name] = self._get_type_error_message(
                    value, field_def.field_type
                )
                continue

            # Pattern validation with helpful suggestions
            if field_def.validation_pattern:
                pattern_error = self._validate_pattern_with_suggestions(
                    value, field_def.validation_pattern, field_name
                )
                if pattern_error:
                    invalid_fields[field_name] = pattern_error

        return invalid_fields

    def _validate_cross_field_consistency(
        self,
        frontmatter_dict: dict[str, Any],
        schema: FrontmatterSchema,
    ) -> list[str]:
        """Validate consistency between related fields."""
        warnings = []

        # Check ID and filename consistency
        if "id" in frontmatter_dict:
            warnings.extend(self._check_id_consistency(frontmatter_dict))

        # Check title and aliases consistency
        if "title" in frontmatter_dict and "aliases" in frontmatter_dict:
            warnings.extend(self._check_title_aliases_consistency(frontmatter_dict))

        # Check date format consistency
        if "date" in frontmatter_dict:
            warnings.extend(self._check_date_consistency(frontmatter_dict))

        return warnings

    def _check_schema_completeness(
        self, frontmatter_dict: dict[str, Any], schema: FrontmatterSchema
    ) -> list[str]:
        """Check for schema completeness and suggest improvements."""
        warnings = []

        # Check for unexpected fields
        schema_fields = set(schema.fields.keys())
        frontmatter_fields = set(frontmatter_dict.keys())
        unexpected_fields = frontmatter_fields - schema_fields

        if unexpected_fields:
            warnings.append(
                f"Unexpected fields not in template schema: "
                f"{', '.join(unexpected_fields)}"
            )

        # Check for recommended optional fields
        recommended_fields = self._get_recommended_optional_fields(schema)
        missing_recommended = recommended_fields - frontmatter_fields

        if missing_recommended:
            warnings.append(
                f"Consider adding recommended fields: {', '.join(missing_recommended)}"
            )

        return warnings

    def _generate_missing_field_fixes(
        self, frontmatter_dict: dict[str, Any], schema: FrontmatterSchema
    ) -> list[FieldFix]:
        """Generate fixes for missing required fields."""
        fixes = []

        for field_name in schema.required_fields:
            if field_name not in frontmatter_dict or not frontmatter_dict[field_name]:
                field_def = schema.fields[field_name]
                suggested_value = self._get_smart_default(field_def)

                fix = FieldFix(
                    field_name=field_name,
                    current_value=frontmatter_dict.get(field_name),
                    suggested_value=suggested_value,
                    fix_type="add" if field_name not in frontmatter_dict else "modify",
                    reason=f"Required field '{field_name}' is missing or empty",
                )
                fixes.append(fix)

        return fixes

    def _generate_type_mismatch_fixes(
        self, frontmatter_dict: dict[str, Any], schema: FrontmatterSchema
    ) -> list[FieldFix]:
        """Generate fixes for type mismatches."""
        fixes = []

        for field_name, field_def in schema.fields.items():
            if field_name not in frontmatter_dict:
                continue

            value = frontmatter_dict[field_name]
            if not self._validate_field_type(value, field_def.field_type):
                suggested_value = self._convert_to_correct_type(
                    value, field_def.field_type
                )

                if suggested_value is not None:
                    fix = FieldFix(
                        field_name=field_name,
                        current_value=value,
                        suggested_value=suggested_value,
                        fix_type="modify",
                        reason=f"Type mismatch: expected {field_def.field_type.value}",
                    )
                    fixes.append(fix)

        return fixes

    def _generate_pattern_violation_fixes(
        self, frontmatter_dict: dict[str, Any], schema: FrontmatterSchema
    ) -> list[FieldFix]:
        """Generate fixes for pattern violations."""
        fixes = []

        for field_name, field_def in schema.fields.items():
            if (
                field_name in frontmatter_dict
                and field_def.validation_pattern
                and isinstance(frontmatter_dict[field_name], str)
            ):
                value = frontmatter_dict[field_name]
                suggested_value = self._fix_pattern_violation(
                    value, field_def.validation_pattern, field_name
                )

                if suggested_value and suggested_value != value:
                    fix = FieldFix(
                        field_name=field_name,
                        current_value=value,
                        suggested_value=suggested_value,
                        fix_type="modify",
                        reason=f"Pattern violation: {field_def.validation_pattern}",
                    )
                    fixes.append(fix)

        return fixes

    def _generate_value_improvement_fixes(
        self,
        frontmatter_dict: dict[str, Any],
        schema: FrontmatterSchema,
    ) -> list[FieldFix]:
        """Generate fixes for value improvements."""
        fixes = []

        # Normalize aliases (remove duplicates, clean whitespace)
        if "aliases" in frontmatter_dict:
            aliases = frontmatter_dict["aliases"]
            if isinstance(aliases, list):
                cleaned_aliases = self._clean_aliases_list(aliases)
                if cleaned_aliases != aliases:
                    fix = FieldFix(
                        field_name="aliases",
                        current_value=aliases,
                        suggested_value=cleaned_aliases,
                        fix_type="modify",
                        reason="Clean up aliases: remove duplicates and whitespace",
                    )
                    fixes.append(fix)

        # Normalize tags
        if "tags" in frontmatter_dict:
            tags = frontmatter_dict["tags"]
            if isinstance(tags, list):
                cleaned_tags = self._clean_tags_list(tags)
                if cleaned_tags != tags:
                    fix = FieldFix(
                        field_name="tags",
                        current_value=tags,
                        suggested_value=cleaned_tags,
                        fix_type="modify",
                        reason="Clean up tags: remove duplicates and normalize format",
                    )
                    fixes.append(fix)

        return fixes

    def _get_smart_default(self, field_def: Any) -> Any:
        """Get smart default value for a field."""
        if field_def.default_value is not None:
            return field_def.default_value

        # Generate smart defaults based on field name and type
        return self._generate_default_by_name_or_type(field_def)

    def _generate_default_by_name_or_type(self, field_def: Any) -> Any:
        """Generate default value by field name or type."""
        if field_def.name == "id":
            return datetime.now().strftime("%Y%m%d%H%M%S")
        if field_def.name == "date":
            return datetime.now().strftime("%Y-%m-%d")

        # Type-based defaults
        type_defaults = {
            FieldType.ARRAY: [],
            FieldType.BOOLEAN: False,
            FieldType.STRING: "",
        }
        return type_defaults.get(field_def.field_type)

    def _validate_field_type(self, value: Any, field_type: FieldType) -> bool:
        """Validate field type."""
        type_validators = {
            FieldType.STRING: lambda v: isinstance(v, str),
            FieldType.ARRAY: lambda v: isinstance(v, list),
            FieldType.BOOLEAN: lambda v: isinstance(v, bool),
            FieldType.INTEGER: lambda v: isinstance(v, int),
            FieldType.NUMBER: lambda v: isinstance(v, (int, float)),
            FieldType.DATE: lambda v: isinstance(v, str),
            FieldType.DATETIME: lambda v: isinstance(v, str),
        }

        validator = type_validators.get(field_type)
        return validator(value) if validator else True

    def _get_type_error_message(self, value: Any, expected_type: FieldType) -> str:
        """Get detailed type error message."""
        actual_type = type(value).__name__
        return f"Expected {expected_type.value}, got {actual_type}. Value: {value!r}"

    def _validate_pattern_with_suggestions(
        self, value: str, pattern: str, field_name: str
    ) -> str | None:
        """Validate pattern with helpful suggestions."""

        if not re.match(pattern, value):
            if field_name == "id":
                return (
                    f"ID must be 14-digit timestamp format (YYYYMMDDHHMMSS), "
                    f"got: {value}"
                )
            if field_name == "date":
                return f"Date must be YYYY-MM-DD format, got: {value}"
            if field_name in ("isbn", "isbn13"):
                return f"ISBN must be 13 digits, got: {value}"
            return f"Value '{value}' does not match pattern '{pattern}'"

        return None

    def _check_id_consistency(self, frontmatter_dict: dict[str, Any]) -> list[str]:
        """Check ID field consistency."""
        warnings = []
        id_value = frontmatter_dict.get("id", "")

        if isinstance(id_value, str) and len(id_value) == 14 and id_value.isdigit():
            # Check if ID looks like a reasonable timestamp
            try:
                datetime.strptime(id_value, "%Y%m%d%H%M%S")
            except ValueError:
                warnings.append(f"ID '{id_value}' is not a valid timestamp format")

        return warnings

    def _check_title_aliases_consistency(
        self, frontmatter_dict: dict[str, Any]
    ) -> list[str]:
        """Check title and aliases consistency."""
        warnings = []
        title = frontmatter_dict.get("title", "")
        aliases = frontmatter_dict.get("aliases", [])

        if isinstance(aliases, list) and title in aliases:
            warnings.append("Title should not be duplicated in aliases list")

        return warnings

    def _check_date_consistency(self, frontmatter_dict: dict[str, Any]) -> list[str]:
        """Check date field consistency."""
        warnings = []
        date_value = frontmatter_dict.get("date", "")

        if isinstance(date_value, str):
            try:
                datetime.strptime(date_value, "%Y-%m-%d")
            except ValueError:
                warnings.append(f"Date '{date_value}' is not in YYYY-MM-DD format")

        return warnings

    def _get_recommended_optional_fields(self, schema: FrontmatterSchema) -> set[str]:
        """Get recommended optional fields for the schema."""
        # Define recommended fields based on template type
        if schema.template_name == "booksearchtemplate":
            return {"author", "publisher", "totalPage"}
        if schema.template_name == "new-fleeing-note":
            return {"description", "category"}

        return set()

    def _convert_to_correct_type(self, value: Any, field_type: FieldType) -> Any:
        """Convert value to correct type."""
        try:
            converters = {
                FieldType.STRING: lambda v: str(v),
                FieldType.ARRAY: self._convert_to_array,
                FieldType.BOOLEAN: self._convert_to_boolean,
                FieldType.INTEGER: lambda v: int(v),
                FieldType.NUMBER: lambda v: float(v),
            }

            converter = converters.get(field_type)
            return converter(value) if converter else None
        except (ValueError, TypeError):
            return None

    def _convert_to_array(self, value: Any) -> list[Any]:
        """Convert value to array."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",")]
        return [value] if not isinstance(value, list) else value

    def _convert_to_boolean(self, value: Any) -> bool:
        """Convert value to boolean."""
        if isinstance(value, str):
            return value.lower() in {"true", "yes", "1", "on"}
        return bool(value)

    def _fix_pattern_violation(
        self,
        value: str,
        pattern: str,
        field_name: str,
    ) -> str | None:
        """Attempt to fix pattern violations."""
        if field_name == "date":
            # Try to fix common date format issues
            return self._fix_date_format(value)
        if field_name == "id":
            # Try to fix ID format issues
            return self._fix_id_format(value)

        return None

    def _fix_date_format(self, value: str) -> str | None:
        """Fix common date format issues."""

        # Try various date formats and convert to YYYY-MM-DD
        date_patterns = [
            (r"(\d{4})/(\d{1,2})/(\d{1,2})", r"\1-\2-\3"),
            (r"(\d{1,2})/(\d{1,2})/(\d{4})", r"\3-\1-\2"),
            (r"(\d{4})\.(\d{1,2})\.(\d{1,2})", r"\1-\2-\3"),
        ]

        for pattern, replacement in date_patterns:
            if re.match(pattern, value):
                fixed = re.sub(pattern, replacement, value)
                try:
                    # Validate the fixed date
                    datetime.strptime(fixed, "%Y-%m-%d")
                    return fixed
                except ValueError:
                    continue

        return None

    def _fix_id_format(self, value: str) -> str | None:
        """Fix common ID format issues."""
        # Remove non-digit characters
        digits_only = "".join(c for c in value if c.isdigit())

        if len(digits_only) == 14:
            return digits_only

        return None

    def _clean_aliases_list(self, aliases: list[str]) -> list[str]:
        """Clean up aliases list."""
        if not isinstance(aliases, list):
            return aliases

        # Remove duplicates, strip whitespace, remove empty strings
        cleaned = []
        seen = set()

        for alias in aliases:
            if isinstance(alias, str):
                cleaned_alias = alias.strip()
                if cleaned_alias and cleaned_alias not in seen:
                    cleaned.append(cleaned_alias)
                    seen.add(cleaned_alias)

        return cleaned

    def _clean_tags_list(self, tags: list[str]) -> list[str]:
        """Clean up tags list."""
        if not isinstance(tags, list):
            return tags

        # Remove duplicates, strip whitespace, normalize case, remove empty strings
        cleaned = []
        seen = set()

        for tag in tags:
            if isinstance(tag, str):
                cleaned_tag = tag.strip().lower()
                if cleaned_tag and cleaned_tag not in seen:
                    cleaned.append(cleaned_tag)
                    seen.add(cleaned_tag)

        return cleaned

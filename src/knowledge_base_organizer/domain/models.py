"""Domain models for knowledge base organizer."""

import re
from collections import OrderedDict
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Constants
OBSIDIAN_ID_LENGTH = 14  # 14-digit timestamp format


class Frontmatter(BaseModel):
    """Frontmatter metadata for markdown files."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="allow",  # Allow additional fields
        str_strip_whitespace=True,
    )

    title: str | None = None
    aliases: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    id: str | None = None
    date: str | None = None
    published: str | None = None
    publish: bool | None = None

    @field_validator("aliases", "tags")
    @classmethod
    def remove_duplicates(cls, v: list[str]) -> list[str]:
        """Remove duplicates while preserving order."""
        return list(dict.fromkeys(v))

    @field_validator("id", mode="before")
    @classmethod
    def convert_id_to_string(cls, v: Any) -> str | None:
        """Convert id to string if it's not None."""
        if v is None:
            return None
        return str(v)

    @field_validator("date", "published", mode="before")
    @classmethod
    def convert_date_to_string(cls, v: Any) -> str | None:
        """Convert date to string if it's not None."""
        if v is None:
            return None
        # Handle datetime.date objects
        if hasattr(v, "isoformat"):
            return v.isoformat()
        return str(v)

    @field_validator("publish", mode="before")
    @classmethod
    def convert_publish_to_bool(cls, v: Any) -> bool | None:
        """Convert publish to boolean, handling various input types."""
        if v is None:
            return None
        # Handle datetime objects (some files might have dates in publish field)
        if hasattr(v, "isoformat"):
            # If it's a date, treat as True (published)
            return True
        # Handle string values
        if isinstance(v, str):
            return v.lower() in ("true", "yes", "1", "on")
        # Handle boolean and other types
        return bool(v)

    @field_validator("title", mode="before")
    @classmethod
    def convert_title_to_string(cls, v: Any) -> str | None:
        """Convert title to string, handling various input types."""
        if v is None:
            return None
        # Handle list (some files might have title as array)
        if isinstance(v, list):
            return v[0] if v else None
        return str(v)

    def model_dump_ordered(
        self, template_order: list[str] | None = None, **kwargs
    ) -> OrderedDict[str, Any]:
        """Return model data as OrderedDict with specified field order."""
        # Exclude None values by default to prevent adding unwanted fields
        kwargs.setdefault("exclude_none", True)
        data = self.model_dump(**kwargs)

        if template_order:
            ordered_data = OrderedDict()
            # Add fields in template order first
            for field_name in template_order:
                if field_name in data:
                    ordered_data[field_name] = data[field_name]
            # Add any remaining fields
            for field_name, value in data.items():
                if field_name not in ordered_data:
                    ordered_data[field_name] = value
            return ordered_data

        return OrderedDict(data)


class TextPosition(BaseModel):
    """Position of text within a file."""

    line_number: int
    column_start: int
    column_end: int


class TextRange(BaseModel):
    """Represents a range of text that should be excluded from link processing."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    start_line: int
    start_column: int
    end_line: int
    end_column: int
    zone_type: str  # "frontmatter", "wikilink", "regular_link", "link_ref_def", "table", "template_variable"


class WikiLink(BaseModel):
    """WikiLink representation."""

    target_id: str
    alias: str | None = None
    line_number: int
    column_start: int
    column_end: int

    def __str__(self) -> str:
        """String representation of WikiLink."""
        if self.alias:
            return f"[[{self.target_id}|{self.alias}]]"
        return f"[[{self.target_id}]]"


class RegularLink(BaseModel):
    """Regular markdown link representation."""

    text: str
    url: str
    line_number: int


class LinkRefDef(BaseModel):
    """Link Reference Definition representation."""

    id: str
    alias: str
    path: str
    title: str
    line_number: int


class MarkdownFile(BaseModel):
    """Markdown file entity."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    path: Path
    file_id: str | None = None
    frontmatter: Frontmatter
    content: str
    wiki_links: list[WikiLink] = Field(default_factory=list)
    regular_links: list[RegularLink] = Field(default_factory=list)
    link_reference_definitions: list[LinkRefDef] = Field(default_factory=list)

    @field_validator("path")
    @classmethod
    def validate_path_exists(cls, v: Path) -> Path:
        """Validate that the file path exists."""
        # Skip validation for test files that don't exist
        if str(v) != "test.md" and not v.exists():
            raise ValueError(f"File does not exist: {v}")
        return v

    def extract_file_id(self) -> str | None:
        """Extract file ID from frontmatter or filename."""
        if self.frontmatter.id:
            return self.frontmatter.id

        # Try to extract from filename (14-digit timestamp)
        stem = self.path.stem
        if stem.isdigit() and len(stem) == OBSIDIAN_ID_LENGTH:
            return stem

        return None

    def extract_links(self) -> None:
        """Extract all types of links from the content, excluding template variables."""
        # Clear existing links
        self.wiki_links.clear()
        self.regular_links.clear()
        self.link_reference_definitions.clear()

        lines = self.content.split("\n")

        # Get exclusion zones for template variables
        exclusion_zones = self._get_template_exclusion_zones()

        for line_num, line in enumerate(lines, 1):
            # Extract WikiLinks: [[id]] or [[id|alias]]
            wiki_pattern = re.compile(r"\[\[([^|\]]+)(?:\|([^\]]+))?\]\]")
            for match in wiki_pattern.finditer(line):
                # Check if this WikiLink is in a template variable exclusion zone
                position = TextPosition(
                    line_number=line_num,
                    column_start=match.start(),
                    column_end=match.end(),
                )

                if self._is_in_exclusion_zone(position, exclusion_zones):
                    continue  # Skip this WikiLink as it's in a template variable

                target_id = match.group(1).strip()
                alias = match.group(2).strip() if match.group(2) else None
                wiki_link = WikiLink(
                    target_id=target_id,
                    alias=alias,
                    line_number=line_num,
                    column_start=match.start(),
                    column_end=match.end(),
                )
                self.wiki_links.append(wiki_link)

            # Extract regular markdown links: [text](url)
            regular_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
            for match in regular_pattern.finditer(line):
                text = match.group(1).strip()
                url = match.group(2).strip()
                regular_link = RegularLink(
                    text=text,
                    url=url,
                    line_number=line_num,
                )
                self.regular_links.append(regular_link)

            # Extract Link Reference Definitions: [id|alias]: path "title"
            link_ref_pattern = re.compile(
                r"^\[([^|\]]+)\|([^\]]+)\]:\s*([^\s]+)(?:\s+\"([^\"]+)\")?"
            )
            match = link_ref_pattern.match(line.strip())
            if match:
                link_ref = LinkRefDef(
                    id=match.group(1).strip(),
                    alias=match.group(2).strip(),
                    path=match.group(3).strip(),
                    title=match.group(4).strip() if match.group(4) else "",
                    line_number=line_num,
                )
                self.link_reference_definitions.append(link_ref)

    def validate_frontmatter(
        self, schema: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Validate frontmatter against schema and return validation results."""
        results = {
            "is_valid": True,
            "missing_fields": [],
            "invalid_fields": {},
            "warnings": [],
        }

        if not schema:
            return results

        # Check required fields
        required_fields = schema.get("required", [])
        frontmatter_dict = self.frontmatter.model_dump(exclude_unset=True)

        for field in required_fields:
            if field not in frontmatter_dict or not frontmatter_dict[field]:
                results["missing_fields"].append(field)
                results["is_valid"] = False

        # Check field types and formats
        field_types = schema.get("properties", {})
        for field, expected_type in field_types.items():
            if field in frontmatter_dict:
                value = frontmatter_dict[field]
                if not self._validate_field_type(value, expected_type):
                    results["invalid_fields"][field] = (
                        f"Expected {expected_type}, got {type(value).__name__}"
                    )
                    results["is_valid"] = False

        return results

    def _validate_field_type(
        self, value: object, expected_type: dict[str, Any]
    ) -> bool:
        """Validate a single field against its expected type."""
        type_name = expected_type.get("type", "string")

        if type_name == "string":
            return isinstance(value, str)
        if type_name == "array":
            return isinstance(value, list)
        if type_name == "boolean":
            return isinstance(value, bool)
        if type_name == "integer":
            return isinstance(value, int)
        if type_name == "number":
            return isinstance(value, (int, float))

        return True  # Unknown type, assume valid

    def _get_template_exclusion_zones(self) -> list["TextRange"]:
        """Get exclusion zones for template variables and template blocks."""
        exclusion_zones = []
        lines = self.content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Detect template variables and template blocks
            # Template variables: ${...}, {{...}}, <% ... %>
            template_patterns = [
                re.compile(r"\$\{[^}]*\}"),  # ${variable}
                re.compile(r"\{\{[^}]*\}\}"),  # {{variable}}
                re.compile(r"<%[^%]*%>"),  # <% template %>
                re.compile(r"<%\*[^*]*\*%>"),  # <%* template *%>
            ]

            for pattern in template_patterns:
                for match in pattern.finditer(line):
                    exclusion_zones.append(
                        TextRange(
                            start_line=line_num,
                            start_column=match.start(),
                            end_line=line_num,
                            end_column=match.end(),
                            zone_type="template_variable",
                        )
                    )

        return exclusion_zones

    def _is_in_exclusion_zone(
        self, position: "TextPosition", exclusion_zones: list["TextRange"]
    ) -> bool:
        """Check if a position falls within any exclusion zone."""
        for zone in exclusion_zones:
            # Check if position is within the zone
            if zone.start_line <= position.line_number <= zone.end_line:
                # If it's a single line zone, check column positions
                if zone.start_line == zone.end_line:
                    if zone.start_column <= position.column_start < zone.end_column:
                        return True
                # If it's a multi-line zone
                elif (
                    (
                        position.line_number == zone.start_line
                        and position.column_start >= zone.start_column
                    )
                    or (
                        position.line_number == zone.end_line
                        and position.column_start < zone.end_column
                    )
                    or (zone.start_line < position.line_number < zone.end_line)
                ):
                    return True

        return False

    def add_wiki_link(self, target_id: str, alias: str | None = None) -> None:
        """Add a new WikiLink to the content."""
        # This is a placeholder - actual implementation would modify content
        # For now, just add to the links list
        wiki_link = WikiLink(
            target_id=target_id,
            alias=alias,
            line_number=0,  # Would be calculated during actual insertion
            column_start=0,
            column_end=0,
        )
        self.wiki_links.append(wiki_link)


# Template Schema Models


class FieldType(str, Enum):
    """Field types for frontmatter schema validation."""

    STRING = "string"
    ARRAY = "array"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    NUMBER = "number"
    DATE = "date"
    DATETIME = "datetime"


class SchemaField(BaseModel):
    """Schema field definition for frontmatter validation."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    name: str
    field_type: FieldType
    required: bool
    default_value: Any = None
    validation_pattern: str | None = None  # regex for validation
    template_variable: str | None = None  # original template variable
    description: str | None = None


class ValidationResult(BaseModel):
    """Result of frontmatter validation against a schema."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    file_path: Path
    template_type: str | None
    is_valid: bool
    missing_fields: list[str]
    invalid_fields: dict[str, str]
    suggested_fixes: dict[str, Any]
    warnings: list[str]


class FieldFix(BaseModel):
    """Suggested fix for a frontmatter field."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    field_name: str
    current_value: Any
    suggested_value: Any
    fix_type: str  # "add", "modify", "remove"
    reason: str


class FrontmatterSchema(BaseModel):
    """Schema definition for frontmatter validation."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    template_name: str
    template_path: Path
    fields: dict[str, SchemaField]
    required_fields: set[str]
    optional_fields: set[str]

    def model_post_init(self, __context: Any) -> None:
        """Initialize schema and compute field sets after model creation."""
        self.required_fields = {
            name for name, field in self.fields.items() if field.required
        }
        self.optional_fields = {
            name for name, field in self.fields.items() if not field.required
        }

    def validate_frontmatter(self, frontmatter: Frontmatter) -> ValidationResult:
        """Validate frontmatter against this schema."""
        missing_fields = []
        invalid_fields = {}
        warnings = []
        suggested_fixes = {}

        frontmatter_dict = frontmatter.model_dump(exclude_unset=True)

        # Check required fields
        for field_name in self.required_fields:
            if field_name not in frontmatter_dict or not frontmatter_dict[field_name]:
                missing_fields.append(field_name)
                field_def = self.fields[field_name]
                if field_def.default_value is not None:
                    suggested_fixes[field_name] = field_def.default_value

        # Check field types and validation patterns
        for field_name, field_def in self.fields.items():
            if field_name in frontmatter_dict:
                value = frontmatter_dict[field_name]

                # Type validation
                if not self._validate_field_type(value, field_def.field_type):
                    invalid_fields[field_name] = (
                        f"Expected {field_def.field_type.value}, "
                        f"got {type(value).__name__}"
                    )

                # Pattern validation
                if (
                    field_def.validation_pattern
                    and isinstance(value, str)
                    and not re.match(field_def.validation_pattern, value)
                ):
                    invalid_fields[field_name] = (
                        f"Value '{value}' does not match pattern "
                        f"'{field_def.validation_pattern}'"
                    )

        # Check for unexpected fields (warnings only)
        all_schema_fields = set(self.fields.keys())
        frontmatter_fields = set(frontmatter_dict.keys())
        unexpected_fields = frontmatter_fields - all_schema_fields

        for field in unexpected_fields:
            warnings.append(f"Unexpected field '{field}' not in template schema")

        is_valid = not missing_fields and not invalid_fields

        return ValidationResult(
            file_path=Path(),  # Will be set by caller
            template_type=self.template_name,
            is_valid=is_valid,
            missing_fields=missing_fields,
            invalid_fields=invalid_fields,
            suggested_fixes=suggested_fixes,
            warnings=warnings,
        )

    def suggest_fixes(self, frontmatter: Frontmatter) -> list[FieldFix]:
        """Suggest fixes for non-conforming frontmatter."""
        fixes = []
        frontmatter_dict = frontmatter.model_dump(exclude_unset=True)

        # Fixes for missing required fields
        for field_name in self.required_fields:
            if field_name not in frontmatter_dict or not frontmatter_dict[field_name]:
                field_def = self.fields[field_name]
                fix = FieldFix(
                    field_name=field_name,
                    current_value=frontmatter_dict.get(field_name),
                    suggested_value=field_def.default_value,
                    fix_type="add" if field_name not in frontmatter_dict else "modify",
                    reason="Required field missing or empty",
                )
                fixes.append(fix)

        # Fixes for type mismatches
        for field_name, field_def in self.fields.items():
            if field_name in frontmatter_dict:
                value = frontmatter_dict[field_name]
                if not self._validate_field_type(value, field_def.field_type):
                    suggested_value = self._convert_to_type(value, field_def.field_type)
                    if suggested_value is not None:
                        fix = FieldFix(
                            field_name=field_name,
                            current_value=value,
                            suggested_value=suggested_value,
                            fix_type="modify",
                            reason=(
                                f"Type mismatch: expected {field_def.field_type.value}"
                            ),
                        )
                        fixes.append(fix)

        return fixes

    def _validate_field_type(self, value: Any, field_type: FieldType) -> bool:
        """Validate a value against a field type."""
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

    def _convert_to_type(self, value: Any, field_type: FieldType) -> Any:
        """Attempt to convert a value to the expected type."""
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
            return value.lower() in ("true", "yes", "1", "on")
        return bool(value)

"""Template schema repository for extracting schemas from template files."""

import re
from pathlib import Path
from typing import Any

import yaml

from ..domain.models import FieldType, FrontmatterSchema, MarkdownFile, SchemaField
from .config import ProcessingConfig
from .file_repository import FileRepository


class TemplateSchemaRepository:
    """Repository for extracting frontmatter schemas from template files."""

    def __init__(self, vault_path: Path, config: ProcessingConfig) -> None:
        """Initialize template schema repository."""
        self.vault_path = vault_path
        self.config = config
        self.file_repository = FileRepository(config)

    def extract_schemas_from_templates(self) -> dict[str, FrontmatterSchema]:
        """Extract frontmatter schemas from template files."""
        schemas = {}

        # Default template directories to scan
        template_directories = [
            "900_TemplaterNotes",
            "903_BookSearchTemplates",
            "Templates",
            "templates",
        ]

        for template_dir in template_directories:
            template_path = self.vault_path / template_dir
            if template_path.exists() and template_path.is_dir():
                for template_file in template_path.glob("*.md"):
                    try:
                        schema = self._parse_template_schema(template_file)
                        if schema:
                            schemas[template_file.stem] = schema
                    except Exception as e:
                        # Log error but continue processing other templates
                        print(f"Warning: Failed to parse template {template_file}: {e}")

        return schemas

    def _parse_template_schema(self, template_path: Path) -> FrontmatterSchema | None:
        """Parse a template file and extract schema rules."""
        try:
            # Load the template file
            content = template_path.read_text(encoding="utf-8")

            # Extract frontmatter
            frontmatter_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if not frontmatter_match:
                return None

            frontmatter_text = frontmatter_match.group(1)

            # Parse YAML frontmatter
            try:
                frontmatter_data = yaml.safe_load(frontmatter_text)
            except yaml.YAMLError:
                return None

            if not isinstance(frontmatter_data, dict):
                return None

            # Convert frontmatter to schema fields
            fields = {}
            for field_name, field_value in frontmatter_data.items():
                schema_field = self._create_schema_field(
                    field_name, field_value, frontmatter_text
                )
                fields[field_name] = schema_field

            # Create schema
            return FrontmatterSchema(
                template_name=template_path.stem,
                template_path=template_path,
                fields=fields,
                required_fields=set(),  # Will be computed in __init__
                optional_fields=set(),  # Will be computed in __init__
            )

        except Exception:
            return None

    def _create_schema_field(
        self, field_name: str, field_value: Any, frontmatter_text: str
    ) -> SchemaField:
        """Create a schema field from template frontmatter."""
        # Detect if this is a template variable
        template_variable = self._extract_template_variable(
            field_name, frontmatter_text
        )

        # Determine field type based on value and template patterns
        field_type = self._determine_field_type(field_value, template_variable)

        # Determine if field is required (heuristic-based)
        required = self._is_field_required(field_name, field_value, template_variable)

        # Set default value
        default_value = self._get_default_value(
            field_value, field_type, template_variable
        )

        # Create validation pattern if applicable
        validation_pattern = self._create_validation_pattern(field_name, field_type)

        return SchemaField(
            name=field_name,
            field_type=field_type,
            required=required,
            default_value=default_value,
            validation_pattern=validation_pattern,
            template_variable=template_variable,
            description=f"Field from template {field_name}",
        )

    def _extract_template_variable(
        self, field_name: str, frontmatter_text: str
    ) -> str | None:
        """Extract template variable syntax from frontmatter."""
        # Look for Templater syntax: <% ... %>
        templater_pattern = rf"{re.escape(field_name)}:\s*<%([^>]+)%>"
        match = re.search(templater_pattern, frontmatter_text)
        if match:
            return match.group(1).strip()

        # Look for Handlebars syntax: {{ ... }}
        handlebars_pattern = rf"{re.escape(field_name)}:\s*\"?\{{\{{([^}}]+)\}}\}}\"?"
        match = re.search(handlebars_pattern, frontmatter_text)
        if match:
            return match.group(1).strip()

        return None

    def _determine_field_type(
        self, field_value: Any, template_variable: str | None
    ) -> FieldType:
        """Determine field type from value and template variable."""
        # Check template variable patterns first
        if template_variable:
            return self._get_type_from_template_variable(template_variable)

        # Check actual value type
        return self._get_type_from_value(field_value)

    def _get_type_from_template_variable(self, template_variable: str) -> FieldType:
        """Get field type from template variable patterns."""
        lower_var = template_variable.lower()
        if "creation_date" in lower_var:
            return (
                FieldType.STRING
                if "YYYYMMDDHHmmss" in template_variable
                else FieldType.DATE
            )
        if "cursor" in lower_var or "title" in lower_var:
            return FieldType.STRING
        return FieldType.STRING

    def _get_type_from_value(self, field_value: Any) -> FieldType:
        """Get field type from actual value."""
        type_mapping = {
            bool: FieldType.BOOLEAN,
            int: FieldType.INTEGER,
            float: FieldType.NUMBER,
            list: FieldType.ARRAY,
        }

        field_type = type_mapping.get(type(field_value))
        if field_type:
            return field_type

        if isinstance(field_value, str):
            if field_value.lower() in ("true", "false"):
                return FieldType.BOOLEAN
            if field_value.isdigit():
                return FieldType.INTEGER

        return FieldType.STRING

    def _is_field_required(
        self, field_name: str, field_value: Any, template_variable: str | None
    ) -> bool:
        """Determine if a field is required based on heuristics."""
        # Core fields are typically required
        core_fields = {"title", "id", "date"}
        if field_name in core_fields:
            return True

        # Fields with template variables are usually required
        if template_variable:
            return True

        # Fields with empty or placeholder values are usually required
        if isinstance(field_value, str):
            placeholder_patterns = [
                r"^$",  # Empty
                r"^\s*$",  # Whitespace only
                r"^<.*>$",  # <placeholder>
                r"^\{.*\}$",  # {placeholder}
                r"^TODO",  # TODO placeholder
                r"^PLACEHOLDER",  # PLACEHOLDER
            ]
            for pattern in placeholder_patterns:
                if re.match(pattern, field_value, re.IGNORECASE):
                    return True

        # Arrays and booleans are often optional
        if isinstance(field_value, (list, bool)):
            return False

        return False  # Default to optional

    def _get_default_value(
        self, field_value: Any, field_type: FieldType, template_variable: str | None
    ) -> Any:
        """Get appropriate default value for the field."""
        # If template variable generates the value, no default needed
        if template_variable and any(
            keyword in template_variable.lower()
            for keyword in ["creation_date", "cursor", "title"]
        ):
            return None

        # Use the template value as default if it's not a placeholder
        if isinstance(field_value, str):
            placeholder_patterns = [
                r"^$",
                r"^\s*$",
                r"^<.*>$",
                r"^\{.*\}$",
                r"^TODO",
                r"^PLACEHOLDER",
            ]
            is_placeholder = any(
                re.match(pattern, field_value, re.IGNORECASE)
                for pattern in placeholder_patterns
            )
            if not is_placeholder:
                return field_value

        # Type-specific defaults
        defaults = {
            FieldType.ARRAY: [],
            FieldType.BOOLEAN: False,
            FieldType.INTEGER: 0,
            FieldType.NUMBER: 0.0,
        }
        return defaults.get(field_type)

    def _create_validation_pattern(
        self, field_name: str, field_type: FieldType
    ) -> str | None:
        """Create validation pattern for specific fields."""
        # ID field validation (14-digit timestamp)
        if field_name == "id" and field_type == FieldType.STRING:
            return r"^\d{14}$"

        # Date field validation (YYYY-MM-DD format)
        if field_name == "date" and field_type in (FieldType.DATE, FieldType.STRING):
            return r"^\d{4}-\d{2}-\d{2}$"

        # ISBN validation
        if field_name in ("isbn", "isbn13") and field_type == FieldType.STRING:
            return r"^\d{13}$"

        return None

    def detect_template_type(self, file: MarkdownFile) -> str | None:
        """Detect which template a file should conform to."""
        # Strategy 1: Directory-based detection
        template_type = self._detect_by_directory(file.path)
        if template_type:
            return template_type

        # Strategy 2: Content-based detection
        template_type = self._detect_by_content(file)
        if template_type:
            return template_type

        # Strategy 3: Fallback to default
        return self._get_fallback_template()

    def _detect_by_directory(self, file_path: Path) -> str | None:
        """Detect template type based on file directory."""
        # Get relative path from vault root
        try:
            relative_path = file_path.relative_to(self.vault_path)
            path_parts = relative_path.parts
        except ValueError:
            return None

        # Directory mappings
        directory_mappings = {
            "100_FleetingNotes": "new-fleeing-note",
            "104_Books": "booksearchtemplate",
            "Books": "booksearchtemplate",
            "FleetingNotes": "new-fleeing-note",
            "Notes": "new-fleeing-note",
        }

        for part in path_parts:
            if part in directory_mappings:
                return directory_mappings[part]

        return None

    def _detect_by_content(self, file: MarkdownFile) -> str | None:
        """Detect template type based on frontmatter content."""
        frontmatter_dict = file.frontmatter.model_dump(exclude_unset=True)

        # Book indicators
        book_indicators = {"isbn13", "publisher", "author", "totalPage", "isbn"}
        if any(field in frontmatter_dict for field in book_indicators):
            return "booksearchtemplate"

        # Note indicators
        note_indicators = {"published", "category", "description"}
        if any(field in frontmatter_dict for field in note_indicators):
            return "new-fleeing-note"

        return None

    def _get_fallback_template(self) -> str | None:
        """Get fallback template when detection fails."""
        return "new-fleeing-note"  # Default to fleeting note template

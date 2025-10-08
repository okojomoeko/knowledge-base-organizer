"""Template schema repository for extracting schemas from template files."""

import re
from collections import OrderedDict
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

    def extract_schema_from_single_template(
        self, template_path: Path
    ) -> FrontmatterSchema:
        """Extract schema from a single template file specified via --template option.

        Args:
            template_path: Path to the template file

        Returns:
            FrontmatterSchema extracted from the template

        Raises:
            FileNotFoundError: If template file doesn't exist
            ValueError: If template file cannot be parsed
        """
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")

        if not template_path.is_file():
            raise ValueError(f"Template path is not a file: {template_path}")

        if not template_path.suffix.lower() == ".md":
            raise ValueError(
                f"Template file must be a markdown file (.md): {template_path}"
            )

        try:
            schema = self._parse_template_schema(template_path)
            if not schema:
                raise ValueError(
                    f"Could not extract valid schema from template: {template_path}"
                )
            return schema
        except Exception as e:
            raise ValueError(f"Failed to parse template {template_path}: {e}") from e

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

            # Convert frontmatter to schema fields (preserve order)
            fields = OrderedDict()
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

        # Special handling for known array fields that might be None in template
        if field_value is None and field_name in ("category", "tags", "aliases"):
            field_type = FieldType.ARRAY

        # Determine if field is required (heuristic-based)
        required = self._is_field_required(field_name, field_value, template_variable)

        # Set default value
        default_value = self._get_default_value(
            field_value, field_type, template_variable
        )

        # For template-based validation, don't set default values for arrays
        # This preserves existing values in files
        # Special handling for array fields that are None in template
        if field_value is None and field_type == FieldType.ARRAY:
            default_value = None  # Don't set default to preserve existing values

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
        # Core fields that are truly required for file structure
        core_required_fields = {
            "title",
            "id",
        }
        if field_name in core_required_fields:
            return True

        # Fields with template variables that generate required content
        if template_variable and any(
            keyword in template_variable.lower()
            for keyword in ["creation_date", "cursor", "title"]
        ):
            # Special case: published field should be optional even with template variable
            if field_name == "published":
                return False
            return True

        # Most other fields should be optional to preserve existing values
        # This prevents overwriting existing valid content with template defaults

        # Special cases for fields that should remain optional
        optional_fields = {
            "published",  # Can be empty or have date
            "image",  # Optional with default
            "description",  # Optional, can be empty
            "category",  # Optional, can be array or string
            "tags",  # Optional array
            "aliases",  # Optional array
        }
        if field_name in optional_fields:
            return False

        # Arrays and booleans are typically optional
        if isinstance(field_value, (list, bool)):
            return False

        # Empty strings in template indicate optional fields
        if isinstance(field_value, str) and not field_value.strip():
            return False

        return False  # Default to optional to preserve existing values

    def _get_default_value(
        self, field_value: Any, _field_type: FieldType, template_variable: str | None
    ) -> Any:
        """Get appropriate default value for the field."""
        # If template variable generates the value, no default needed
        if template_variable and any(
            keyword in template_variable.lower()
            for keyword in ["creation_date", "cursor", "title"]
        ):
            return None

        # For template-based validation, we should NOT use template values as defaults
        # Template values are structure definitions, not default values

        # Only use template string values as defaults if they are meaningful defaults
        # (not empty strings, placeholders, or structural values)
        if isinstance(field_value, str) and field_value.strip():
            # Check if it's a meaningful default (like image path)
            if field_value.startswith(("../../assets/", "assets/")):
                return field_value

            # Don't use other string values from template as defaults
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
            if is_placeholder:
                return None

        # Special handling for specific template fields
        if isinstance(field_value, str) and field_value == "None":
            return None

        # For arrays and other types, don't use template values as defaults
        # Template structure should not override existing file values
        if isinstance(field_value, list):
            return None  # No default for arrays - preserve existing values

        if isinstance(field_value, bool):
            return None  # No default for booleans - preserve existing values

        # Only return None (no default) to preserve existing values
        return None

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

        # Use configuration-based directory mappings
        directory_mappings = self.config.directory_template_mappings

        # Check each path part against mappings
        for part in path_parts:
            if part in directory_mappings:
                return directory_mappings[part]

        # Check for partial matches (case-insensitive)
        for part in path_parts:
            for dir_pattern, template_name in directory_mappings.items():
                if (
                    part.lower() in dir_pattern.lower()
                    or dir_pattern.lower() in part.lower()
                ):
                    return template_name

        return None

    def _detect_by_content(self, file: MarkdownFile) -> str | None:
        """Detect template type based on frontmatter content."""
        frontmatter_dict = file.frontmatter.model_dump(exclude_unset=True)

        # Enhanced content-based detection with scoring
        template_scores = {}

        # Book template indicators (strong indicators)
        book_strong_indicators = {"isbn13", "isbn", "publisher", "totalPage"}
        book_weak_indicators = {"author", "pages", "publication"}

        book_score = 0
        book_score += sum(
            3 for field in book_strong_indicators if field in frontmatter_dict
        )
        book_score += sum(
            1 for field in book_weak_indicators if field in frontmatter_dict
        )

        if book_score > 0:
            template_scores["booksearchtemplate"] = book_score

        # Note template indicators
        note_strong_indicators = {"category", "description", "published"}
        note_weak_indicators = {"summary", "notes", "content"}

        note_score = 0
        note_score += sum(
            3 for field in note_strong_indicators if field in frontmatter_dict
        )
        note_score += sum(
            1 for field in note_weak_indicators if field in frontmatter_dict
        )

        if note_score > 0:
            template_scores["new-fleeing-note"] = note_score

        # Return template with highest score
        if template_scores:
            return max(template_scores, key=template_scores.get)

        return None

    def _get_fallback_template(self) -> str | None:
        """Get fallback template when detection fails."""
        return self.config.fallback_template

"""File repository for loading and saving markdown files."""

import fnmatch
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from knowledge_base_organizer.domain.models import (
    OBSIDIAN_ID_LENGTH,
    Frontmatter,
    MarkdownFile,
)
from knowledge_base_organizer.infrastructure.config import ProcessingConfig


class FileRepository:
    """Repository for file operations."""

    def __init__(self, config: ProcessingConfig) -> None:
        """Initialize file repository with configuration."""
        self.config = config

    def load_vault(self, vault_path: Path) -> list[MarkdownFile]:
        """Load all markdown files matching include/exclude patterns."""
        if not vault_path.exists():
            raise ValueError(f"Vault path does not exist: {vault_path}")

        files = []
        for pattern in self.config.include_patterns:
            for file_path in vault_path.rglob(pattern):
                if self._should_include_file(file_path, vault_path):
                    try:
                        markdown_file = self.load_file(file_path)
                        files.append(markdown_file)
                    except (ValueError, yaml.YAMLError, ValidationError) as e:
                        # Log error and continue with other files
                        print(f"Warning: Failed to load {file_path}: {e}")
                        continue

        return files

    def load_file(self, file_path: Path) -> MarkdownFile:
        """Load a single markdown file."""
        if not file_path.exists():
            raise ValueError(f"File does not exist: {file_path}")

        content = file_path.read_text(encoding="utf-8")
        frontmatter, body_content = self._parse_frontmatter(content)

        # Extract file ID
        file_id = None
        if frontmatter.id:
            file_id = frontmatter.id
        elif file_path.stem.isdigit() and len(file_path.stem) == OBSIDIAN_ID_LENGTH:
            file_id = file_path.stem

        markdown_file = MarkdownFile(
            path=file_path,
            file_id=file_id,
            frontmatter=frontmatter,
            content=body_content,
        )

        # Extract links from content
        markdown_file.extract_links()

        return markdown_file

    def save_file(
        self,
        file: MarkdownFile,
        *,
        backup: bool = True,
        template_order: list[str] | None = None,
    ) -> None:
        """Save file with optional backup creation."""
        if backup and self.config.backup_enabled:
            self.create_backup(file.path)

        # Reconstruct full content with frontmatter
        full_content = self._reconstruct_content(file, template_order)
        file.path.write_text(full_content, encoding="utf-8")

    def create_backup(self, file_path: Path) -> Path:
        """Create timestamped backup of file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = file_path.with_suffix(f".backup_{timestamp}.bak")
        backup_path.write_text(file_path.read_text(encoding="utf-8"), encoding="utf-8")
        return backup_path

    def restore_from_backup(self, file_path: Path, backup_path: Path) -> None:
        """Restore file from backup."""
        if not backup_path.exists():
            raise ValueError(f"Backup file does not exist: {backup_path}")

        backup_content = backup_path.read_text(encoding="utf-8")
        file_path.write_text(backup_content, encoding="utf-8")

    def _should_include_file(self, file_path: Path, vault_path: Path) -> bool:
        """Check if file should be included based on exclude patterns."""
        # Skip directories - only process files
        if not file_path.is_file():
            return False

        # Only process markdown files
        if file_path.suffix.lower() != ".md":
            return False

        relative_path = file_path.relative_to(vault_path)
        relative_str = str(relative_path)
        path_parts = relative_path.parts

        # Check against each exclude pattern
        for exclude_pattern in self.config.exclude_patterns:
            # Handle **/dirname/** patterns by checking path parts
            if exclude_pattern.startswith("**/") and exclude_pattern.endswith("/**"):
                # Extract directory name from **/dirname/** pattern
                dir_name = exclude_pattern[3:-3]  # Remove **/ and /**
                if dir_name in path_parts:
                    return False
            # Handle other patterns with fnmatch
            elif fnmatch.fnmatch(relative_str, exclude_pattern):
                return False

        return True

    def _parse_frontmatter(self, content: str) -> tuple[Frontmatter, str]:
        """Parse frontmatter from markdown content with enhanced error handling."""
        # Support both --- and +++ delimiters
        frontmatter_pattern = re.compile(
            r"^(---|\+\+\+)\s*\n(.*?)\n(---|\+\+\+)\s*\n", re.DOTALL
        )
        match = frontmatter_pattern.match(content)

        if match:
            frontmatter_text = match.group(2)
            body_content = content[match.end() :]

            try:
                frontmatter_data = yaml.safe_load(frontmatter_text) or {}

                # Handle common frontmatter field variations
                frontmatter_data = self._normalize_frontmatter_fields(frontmatter_data)

                frontmatter = Frontmatter(**frontmatter_data)
            except yaml.YAMLError as e:
                # Log YAML parsing error but continue with empty frontmatter
                print(f"Warning: YAML parsing error in frontmatter: {e}")
                frontmatter = Frontmatter()
            except ValidationError as e:
                # Log validation error but continue with partial frontmatter
                print(f"Warning: Frontmatter validation error: {e}")
                # Try to create frontmatter with only valid fields
                frontmatter = self._create_partial_frontmatter(frontmatter_data)
        else:
            frontmatter = Frontmatter()
            body_content = content

        return frontmatter, body_content

    def _normalize_frontmatter_fields(self, data: dict[str, Any]) -> dict[str, Any]:
        """Normalize common frontmatter field variations."""
        normalized = {}

        for key, value in data.items():
            # Normalize key names
            normalized_key = key.lower().strip()

            # Handle common field name variations
            if normalized_key in {"tag", "category", "categories"}:
                normalized_key = "tags"
            elif normalized_key in {"alias", "aka"}:
                normalized_key = "aliases"
            elif normalized_key in {"created", "created_date", "creation_date"}:
                normalized_key = "date"
            elif normalized_key in {"public"}:
                normalized_key = "publish"
            else:
                normalized_key = key  # Keep original case for other fields

            # Normalize values
            if normalized_key in {"tags", "aliases"} and isinstance(value, str):
                # Convert single string to list
                normalized[normalized_key] = [value]
            elif normalized_key == "publish" and isinstance(value, str):
                # Convert string to boolean
                normalized[normalized_key] = value.lower() in {"true", "yes", "1"}
            elif value is None and normalized_key in {"description"}:
                # Convert None to empty string for description field
                normalized[normalized_key] = ""
            else:
                normalized[normalized_key] = value

        return normalized

    def _create_partial_frontmatter(self, data: dict[str, Any]) -> Frontmatter:
        """Create frontmatter with only valid fields when validation fails."""
        valid_fields = {}

        # Try each field individually
        for field in ["title", "aliases", "tags", "id", "date", "published", "publish"]:
            if field in data:
                try:
                    # Test if this field would be valid
                    test_data = {field: data[field]}
                    Frontmatter(**test_data)
                    valid_fields[field] = data[field]
                except ValidationError:
                    # Skip invalid field
                    continue

        return Frontmatter(**valid_fields)

    def save_file_content(
        self, file_path: Path, content: str, *, backup: bool = True
    ) -> None:
        """Save content to a file with optional backup."""
        if backup and self.config.backup_enabled:
            self.create_backup(file_path)

        file_path.write_text(content, encoding="utf-8")

    def update_frontmatter(
        self,
        file_path: Path,
        frontmatter_changes: dict[str, Any],
        *,
        backup: bool = True,
    ) -> None:
        """Update frontmatter fields in a file."""
        if backup and self.config.backup_enabled:
            self.create_backup(file_path)

        # Load current file
        current_file = self.load_file(file_path)

        # Update frontmatter fields
        frontmatter_dict = current_file.frontmatter.model_dump(exclude_unset=True)
        frontmatter_dict.update(frontmatter_changes)

        # Create new frontmatter object (validation only)
        Frontmatter(**frontmatter_dict)

        # Reconstruct content with updated frontmatter
        if frontmatter_dict:
            frontmatter_yaml = yaml.dump(
                frontmatter_dict, default_flow_style=False, allow_unicode=True
            )
            full_content = f"---\n{frontmatter_yaml}---\n{current_file.content}"
        else:
            full_content = current_file.content

        # Save updated content
        file_path.write_text(full_content, encoding="utf-8")

    def _reconstruct_content(
        self, file: MarkdownFile, template_order: list[str] | None = None
    ) -> str:
        """Reconstruct full content with frontmatter."""
        if template_order:
            frontmatter_dict = file.frontmatter.model_dump_ordered(
                template_order, exclude_unset=True, exclude_none=True
            )
        else:
            frontmatter_dict = file.frontmatter.model_dump(
                exclude_unset=True, exclude_none=True
            )

        if frontmatter_dict:
            # Use custom YAML formatting to preserve template style
            frontmatter_yaml = self._format_frontmatter_yaml(
                frontmatter_dict, template_order
            )
            return f"---\n{frontmatter_yaml}---\n{file.content}"
        return file.content

    def _format_frontmatter_yaml(
        self, frontmatter_dict: dict[str, Any], template_order: list[str] | None = None
    ) -> str:
        """Format frontmatter YAML with template-style formatting."""
        lines = []

        # Process fields in template order if provided
        fields_to_process = (
            template_order if template_order else list(frontmatter_dict.keys())
        )

        for field_name in fields_to_process:
            if field_name not in frontmatter_dict:
                continue

            value = frontmatter_dict[field_name]

            # Format based on value type and template expectations
            if isinstance(value, list):
                # Always use inline array format to match template style
                if not value:  # Empty array
                    lines.append(f"{field_name}: []")
                else:
                    # Format as inline array: [item1, item2, item3]
                    formatted_items = []
                    for item in value:
                        if self._needs_quoting(str(item), field_name):
                            formatted_items.append(f'"{item}"')
                        else:
                            formatted_items.append(str(item))
                    lines.append(f"{field_name}: [{','.join(formatted_items)}]")
            elif isinstance(value, bool):
                lines.append(f"{field_name}: {str(value).lower()}")
            elif value is None:
                lines.append(f"{field_name}:")
            elif isinstance(value, str):
                # Handle empty strings (like description field in template)
                if value == "":
                    lines.append(f"{field_name}:")
                # Don't quote simple strings unless they contain special characters
                elif self._needs_quoting(value, field_name):
                    lines.append(f'{field_name}: "{value}"')
                else:
                    lines.append(f"{field_name}: {value}")
            else:
                lines.append(f"{field_name}: {value}")

        # Add any remaining fields not in template order
        if template_order:
            for field_name, value in frontmatter_dict.items():
                if field_name not in template_order:
                    if isinstance(value, list):
                        # Always use inline array format
                        if not value:
                            lines.append(f"{field_name}: []")
                        else:
                            formatted_items = []
                            for item in value:
                                if self._needs_quoting(str(item), field_name):
                                    formatted_items.append(f'"{item}"')
                                else:
                                    formatted_items.append(str(item))
                            lines.append(f"{field_name}: [{','.join(formatted_items)}]")
                    elif isinstance(value, bool):
                        lines.append(f"{field_name}: {str(value).lower()}")
                    elif value is None:
                        lines.append(f"{field_name}:")
                    elif isinstance(value, str):
                        # Handle empty strings
                        if value == "":
                            lines.append(f"{field_name}:")
                        elif self._needs_quoting(value, field_name):
                            lines.append(f'{field_name}: "{value}"')
                        else:
                            lines.append(f"{field_name}: {value}")
                    else:
                        lines.append(f"{field_name}: {value}")

        return "\n".join(lines) + "\n"

    def _needs_quoting(self, value: str, field_name: str = "") -> bool:
        """Determine if a string value needs quoting in YAML."""
        # Special handling for fields that should always be quoted
        always_quote_fields = {"image"}
        if field_name in always_quote_fields:
            return True

        # Special handling for specific fields that should not be quoted
        # even if they look like numbers
        numeric_fields_no_quote = {"id"}
        if field_name in numeric_fields_no_quote:
            # Only quote if contains special characters, not for numeric values
            special_chars = [
                ":",
                "[",
                "]",
                "{",
                "}",
                "|",
                ">",
                "#",
                "&",
                "*",
                "!",
                "%",
                "@",
                "`",
            ]
            return any(char in value for char in special_chars)

        # Quote if contains special YAML characters or looks like a number/boolean
        special_chars = [
            ":",
            "[",
            "]",
            "{",
            "}",
            "|",
            ">",
            "#",
            "&",
            "*",
            "!",
            "%",
            "@",
            "`",
        ]
        if any(char in value for char in special_chars):
            return True

        # Quote if looks like a number or boolean
        if value.lower() in ("true", "false", "null", "yes", "no", "on", "off"):
            return True

        try:
            float(value)
            return True
        except ValueError:
            pass

        return False

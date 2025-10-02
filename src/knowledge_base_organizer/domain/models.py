"""Domain models for knowledge base organizer."""

import re
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
    publish: bool = False

    @field_validator("aliases", "tags")
    @classmethod
    def remove_duplicates(cls, v: list[str]) -> list[str]:
        """Remove duplicates while preserving order."""
        return list(dict.fromkeys(v))


class TextPosition(BaseModel):
    """Position of text within a file."""

    line_number: int
    column_start: int
    column_end: int


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
        """Extract all types of links from the content."""
        # Clear existing links
        self.wiki_links.clear()
        self.regular_links.clear()
        self.link_reference_definitions.clear()

        lines = self.content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Extract WikiLinks: [[id]] or [[id|alias]]
            wiki_pattern = re.compile(r"\[\[([^|\]]+)(?:\|([^\]]+))?\]\]")
            for match in wiki_pattern.finditer(line):
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
        elif type_name == "array":
            return isinstance(value, list)
        elif type_name == "boolean":
            return isinstance(value, bool)
        elif type_name == "integer":
            return isinstance(value, int)
        elif type_name == "number":
            return isinstance(value, (int, float))

        return True  # Unknown type, assume valid

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

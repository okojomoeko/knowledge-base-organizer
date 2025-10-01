"""Domain models for knowledge base organizer."""

from pathlib import Path

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
        if not v.exists():
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

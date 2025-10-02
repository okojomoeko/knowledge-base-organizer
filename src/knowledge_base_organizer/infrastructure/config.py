"""Configuration management for knowledge base organizer."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class ProcessingConfig(BaseModel):
    """Configuration for processing operations."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    include_patterns: list[str] = Field(default_factory=lambda: ["**/*.md"])
    exclude_patterns: list[str] = Field(default_factory=list)
    frontmatter_schema: dict[str, Any] = Field(default_factory=dict)
    exclude_tables_from_linking: bool = False
    max_links_per_file: int = 50
    backup_enabled: bool = True
    template_directories: list[str] = Field(
        default_factory=lambda: [
            "900_TemplaterNotes",
            "903_BookSearchTemplates",
            "Templates",
            "templates",
        ]
    )

    # Template detection settings
    directory_template_mappings: dict[str, str] = Field(
        default_factory=lambda: {
            "100_FleetingNotes": "new-fleeing-note",
            "104_Books": "booksearchtemplate",
            "Books": "booksearchtemplate",
            "FleetingNotes": "new-fleeing-note",
            "Notes": "new-fleeing-note",
        }
    )

    fallback_template: str = "new-fleeing-note"

    @classmethod
    def from_file(cls, config_path: Path) -> "ProcessingConfig":
        """Load configuration from YAML file."""
        if not config_path.exists():
            return cls()

        with config_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return cls(**data)

    @classmethod
    def get_default_config(cls) -> "ProcessingConfig":
        """Get default configuration for standard Obsidian vaults."""
        return cls(
            include_patterns=["**/*.md"],
            exclude_patterns=[
                "**/.obsidian/**",
                "**/node_modules/**",
                "**/.git/**",
            ],
            exclude_tables_from_linking=False,
            max_links_per_file=50,
            backup_enabled=True,
        )


class OutputFormat(str):
    """Output format enumeration."""

    JSON = "json"
    CSV = "csv"
    CONSOLE = "console"

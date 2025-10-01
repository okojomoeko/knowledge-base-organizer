"""File repository for loading and saving markdown files."""

import re
from datetime import datetime
from pathlib import Path

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
                    except Exception as e:
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

        return MarkdownFile(
            path=file_path,
            file_id=file_id,
            frontmatter=frontmatter,
            content=body_content,
        )

    def save_file(self, file: MarkdownFile, backup: bool = True) -> None:
        """Save file with optional backup creation."""
        if backup and self.config.backup_enabled:
            self.create_backup(file.path)

        # Reconstruct full content with frontmatter
        full_content = self._reconstruct_content(file)
        file.path.write_text(full_content, encoding="utf-8")

    def create_backup(self, file_path: Path) -> Path:
        """Create timestamped backup of file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = file_path.with_suffix(f".{timestamp}.bak")
        backup_path.write_text(file_path.read_text(encoding="utf-8"))
        return backup_path

    def _should_include_file(self, file_path: Path, vault_path: Path) -> bool:
        """Check if file should be included based on exclude patterns."""
        relative_path = file_path.relative_to(vault_path)
        relative_str = str(relative_path)

        for exclude_pattern in self.config.exclude_patterns:
            if Path(relative_str).match(exclude_pattern):
                return False

        return True

    def _parse_frontmatter(self, content: str) -> tuple[Frontmatter, str]:
        """Parse frontmatter from markdown content."""
        frontmatter_pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
        match = frontmatter_pattern.match(content)

        if match:
            frontmatter_text = match.group(1)
            body_content = content[match.end() :]

            try:
                frontmatter_data = yaml.safe_load(frontmatter_text) or {}
                frontmatter = Frontmatter(**frontmatter_data)
            except (yaml.YAMLError, ValidationError):
                # If frontmatter parsing fails, create empty frontmatter
                frontmatter = Frontmatter()
        else:
            frontmatter = Frontmatter()
            body_content = content

        return frontmatter, body_content

    def _reconstruct_content(self, file: MarkdownFile) -> str:
        """Reconstruct full content with frontmatter."""
        frontmatter_dict = file.frontmatter.model_dump(exclude_unset=True)

        if frontmatter_dict:
            frontmatter_yaml = yaml.dump(
                frontmatter_dict, default_flow_style=False, allow_unicode=True
            )
            return f"---\n{frontmatter_yaml}---\n{file.content}"
        else:
            return file.content

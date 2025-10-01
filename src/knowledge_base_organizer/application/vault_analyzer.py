"""Vault analysis use case."""

from pathlib import Path
from typing import Any

from knowledge_base_organizer.domain.models import MarkdownFile
from knowledge_base_organizer.infrastructure.config import ProcessingConfig
from knowledge_base_organizer.infrastructure.file_repository import FileRepository


class VaultAnalyzer:
    """Use case for analyzing vault contents."""

    def __init__(self, config: ProcessingConfig) -> None:
        """Initialize vault analyzer with configuration."""
        self.config = config
        self.file_repository = FileRepository(config)

    def analyze_vault(self, vault_path: Path) -> dict[str, Any]:
        """Analyze vault and return summary statistics."""
        files = self.file_repository.load_vault(vault_path)

        return {
            "total_files": len(files),
            "files_with_frontmatter": sum(1 for f in files if self._has_frontmatter(f)),
            "files_with_id": sum(1 for f in files if f.file_id),
            "files_by_extension": self._count_by_extension(files),
            "average_content_length": self._calculate_average_content_length(files),
        }

    def load_vault_files(self, vault_path: Path) -> list[MarkdownFile]:
        """Load all files from vault."""
        return self.file_repository.load_vault(vault_path)

    def _has_frontmatter(self, file: MarkdownFile) -> bool:
        """Check if file has meaningful frontmatter."""
        frontmatter_dict = file.frontmatter.model_dump(exclude_unset=True)
        return bool(frontmatter_dict)

    def _count_by_extension(self, files: list[MarkdownFile]) -> dict[str, int]:
        """Count files by extension."""
        counts: dict[str, int] = {}
        for file in files:
            ext = file.path.suffix
            counts[ext] = counts.get(ext, 0) + 1
        return counts

    def _calculate_average_content_length(self, files: list[MarkdownFile]) -> float:
        """Calculate average content length."""
        if not files:
            return 0.0

        total_length = sum(len(file.content) for file in files)
        return total_length / len(files)

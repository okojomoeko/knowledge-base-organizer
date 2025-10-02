"""Vault analysis use case."""

from collections import Counter
from datetime import datetime
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

    def analyze_vault_detailed(self, vault_path: Path) -> dict[str, Any]:
        """Analyze vault and return detailed statistics for the analyze command."""
        files = self.file_repository.load_vault(vault_path)

        # Extract links from all files
        for file in files:
            file.extract_links()

        return {
            "vault_path": str(vault_path),
            "analysis_timestamp": self._get_timestamp(),
            "file_statistics": self._calculate_file_statistics(files),
            "frontmatter_statistics": self._calculate_frontmatter_statistics(files),
            "link_statistics": self._calculate_link_statistics(files),
            "content_statistics": self._calculate_content_statistics(files),
        }

    def _calculate_file_statistics(self, files: list[MarkdownFile]) -> dict[str, Any]:
        """Calculate basic file statistics."""
        total_files = len(files)
        files_with_frontmatter = sum(1 for f in files if self._has_frontmatter(f))
        files_with_id = sum(1 for f in files if f.file_id)
        files_by_extension = self._count_by_extension(files)

        return {
            "total_files": total_files,
            "files_with_frontmatter": files_with_frontmatter,
            "files_with_id": files_with_id,
            "files_by_extension": files_by_extension,
        }

    def _calculate_frontmatter_statistics(
        self, files: list[MarkdownFile]
    ) -> dict[str, Any]:
        """Calculate frontmatter field distribution statistics."""
        frontmatter_fields: Counter[str] = Counter()
        for file in files:
            if self._has_frontmatter(file):
                frontmatter_dict = file.frontmatter.model_dump(exclude_unset=True)
                for field in frontmatter_dict:
                    frontmatter_fields[field] += 1

        return {
            "field_distribution": dict(frontmatter_fields),
            "most_common_fields": frontmatter_fields.most_common(10),
            "total_unique_fields": len(frontmatter_fields),
        }

    def _calculate_link_statistics(self, files: list[MarkdownFile]) -> dict[str, Any]:
        """Calculate link statistics for all types of links."""
        total_files = len(files)

        # Count links by type
        total_wiki_links = sum(len(f.wiki_links) for f in files)
        total_regular_links = sum(len(f.regular_links) for f in files)
        total_link_ref_defs = sum(len(f.link_reference_definitions) for f in files)

        # Count files with links
        files_with_wiki_links = sum(1 for f in files if f.wiki_links)
        files_with_regular_links = sum(1 for f in files if f.regular_links)
        files_with_link_ref_defs = sum(1 for f in files if f.link_reference_definitions)

        return {
            "wiki_links": {
                "total_count": total_wiki_links,
                "files_with_links": files_with_wiki_links,
                "average_per_file": total_wiki_links / total_files
                if total_files > 0
                else 0,
            },
            "regular_links": {
                "total_count": total_regular_links,
                "files_with_links": files_with_regular_links,
                "average_per_file": total_regular_links / total_files
                if total_files > 0
                else 0,
            },
            "link_reference_definitions": {
                "total_count": total_link_ref_defs,
                "files_with_definitions": files_with_link_ref_defs,
                "average_per_file": total_link_ref_defs / total_files
                if total_files > 0
                else 0,
            },
            "total_links": total_wiki_links + total_regular_links + total_link_ref_defs,
        }

    def _calculate_content_statistics(
        self, files: list[MarkdownFile]
    ) -> dict[str, Any]:
        """Calculate content-related statistics."""
        total_files = len(files)
        total_content_length = sum(len(f.content) for f in files)
        average_content_length = (
            total_content_length / total_files if total_files > 0 else 0
        )

        return {
            "total_content_length": total_content_length,
            "average_content_length": round(average_content_length, 2),
            "largest_file_size": max((len(f.content) for f in files), default=0),
            "smallest_file_size": min((len(f.content) for f in files), default=0),
        }

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now().isoformat()

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

"""Dead link detection use case for identifying broken links in markdown files."""

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from ..domain.models import MarkdownFile
from ..domain.services.link_analysis_service import DeadLink, LinkAnalysisService
from ..infrastructure.config import ProcessingConfig
from ..infrastructure.file_repository import FileRepository


@dataclass
class DeadLinkDetectionRequest:
    """Request for dead link detection operation."""

    vault_path: Path
    include_patterns: list[str] | None = None
    exclude_patterns: list[str] | None = None
    check_external_links: bool = False


class DeadLinkDetectionResult(BaseModel):
    """Result of dead link detection operation."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    vault_path: str
    total_files_scanned: int
    files_with_dead_links: int
    total_dead_links: int
    dead_links_by_type: dict[str, int]
    dead_links: list[DeadLink]
    summary: dict[str, int | str]


class DeadLinkDetectionUseCase:
    """Use case for detecting dead links in markdown files."""

    def __init__(
        self,
        file_repository: FileRepository,
        link_analysis_service: LinkAnalysisService,
        config: ProcessingConfig,
    ):
        """Initialize the dead link detection use case.

        Args:
            file_repository: Repository for loading markdown files
            link_analysis_service: Service for analyzing links
            config: Processing configuration
        """
        self.file_repository = file_repository
        self.link_analysis_service = link_analysis_service
        self.config = config

    def execute(self, request: DeadLinkDetectionRequest) -> DeadLinkDetectionResult:
        """Execute dead link detection.

        Args:
            request: Dead link detection request

        Returns:
            DeadLinkDetectionResult with detected dead links and statistics

        Raises:
            ValueError: If vault path doesn't exist or is invalid
            FileNotFoundError: If vault path is not found
        """
        if not request.vault_path.exists():
            raise FileNotFoundError(f"Vault path does not exist: {request.vault_path}")

        if not request.vault_path.is_dir():
            raise ValueError(f"Vault path is not a directory: {request.vault_path}")

        # Update config with request parameters
        config = self._prepare_config(request)

        # Update the repository config and load all markdown files
        original_config = self.file_repository.config
        self.file_repository.config = config
        try:
            files = self.file_repository.load_vault(request.vault_path)
        finally:
            # Restore original config
            self.file_repository.config = original_config

        # Build file registry for link validation
        file_registry = self._build_file_registry(files)

        # Detect dead links
        dead_links = self.link_analysis_service.detect_dead_links(files, file_registry)

        # Calculate statistics
        return self._build_result(request, files, dead_links)

    def _prepare_config(self, request: DeadLinkDetectionRequest) -> ProcessingConfig:
        """Prepare processing configuration from request."""
        # Create a copy of the current config
        config = ProcessingConfig(
            include_patterns=self.config.include_patterns.copy(),
            exclude_patterns=self.config.exclude_patterns.copy(),
            frontmatter_schema=self.config.frontmatter_schema.copy(),
            exclude_tables_from_linking=self.config.exclude_tables_from_linking,
            max_links_per_file=self.config.max_links_per_file,
            backup_enabled=self.config.backup_enabled,
            template_directories=self.config.template_directories.copy(),
            directory_template_mappings=self.config.directory_template_mappings.copy(),
            fallback_template=self.config.fallback_template,
        )

        if request.include_patterns:
            config.include_patterns = request.include_patterns

        if request.exclude_patterns:
            config.exclude_patterns.extend(request.exclude_patterns)

        return config

    def _build_file_registry(
        self, files: list[MarkdownFile]
    ) -> dict[str, MarkdownFile]:
        """Build a registry mapping file IDs to MarkdownFile objects."""
        registry = {}
        for file in files:
            if file.file_id:
                registry[file.file_id] = file
        return registry

    def _build_result(
        self,
        request: DeadLinkDetectionRequest,
        files: list[MarkdownFile],
        dead_links: list[DeadLink],
    ) -> DeadLinkDetectionResult:
        """Build the result object with statistics."""
        # Count dead links by type
        dead_links_by_type = {}
        for dead_link in dead_links:
            link_type = dead_link.link_type
            dead_links_by_type[link_type] = dead_links_by_type.get(link_type, 0) + 1

        # Count files with dead links
        files_with_dead_links = len({dl.source_file for dl in dead_links})

        # Build summary
        summary = {
            "total_files": len(files),
            "files_with_dead_links": files_with_dead_links,
            "total_dead_links": len(dead_links),
            "wikilink_dead_links": dead_links_by_type.get("wikilink", 0),
            "regular_link_dead_links": dead_links_by_type.get("regular_link", 0),
            "link_ref_def_dead_links": dead_links_by_type.get("link_ref_def", 0),
            "vault_path": str(request.vault_path),
        }

        return DeadLinkDetectionResult(
            vault_path=str(request.vault_path),
            total_files_scanned=len(files),
            files_with_dead_links=files_with_dead_links,
            total_dead_links=len(dead_links),
            dead_links_by_type=dead_links_by_type,
            dead_links=dead_links,
            summary=summary,
        )

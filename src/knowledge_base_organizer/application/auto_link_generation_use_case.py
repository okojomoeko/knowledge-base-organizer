"""Use case for automatic WikiLink generation from plain text mentions."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from ..domain.models import MarkdownFile
from ..domain.services.content_processing_service import (
    ContentProcessingResult,
    ContentProcessingService,
    LinkReplacement,
)
from ..domain.services.link_analysis_service import LinkAnalysisService
from ..infrastructure.config import ProcessingConfig
from ..infrastructure.file_repository import FileRepository


class AutoLinkGenerationRequest(BaseModel):
    """Request for automatic link generation."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    vault_path: Path
    dry_run: bool = True
    exclude_tables: bool = False
    max_links_per_file: int = 50
    include_patterns: list[str] | None = None
    exclude_patterns: list[str] | None = None
    target_files: list[str] | None = None  # Specific files to process


class FileUpdate(BaseModel):
    """Represents an update to be made to a file."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    file_path: Path
    update_type: str  # "add_wikilink", "add_alias"
    original_content: str | None = None
    new_content: str | None = None
    frontmatter_changes: dict[str, Any] | None = None
    applied_replacements: list[LinkReplacement] | None = None


class AutoLinkGenerationResult(BaseModel):
    """Result of automatic link generation operation."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    vault_path: str
    total_files_processed: int
    total_links_created: int
    total_aliases_added: int
    file_updates: list[FileUpdate]
    processing_results: list[ContentProcessingResult]
    skipped_files: list[str]
    errors: list[str]
    summary: dict[str, Any]


class AutoLinkGenerationUseCase:
    """Use case for orchestrating automatic WikiLink creation."""

    def __init__(
        self,
        file_repository: FileRepository,
        link_analysis_service: LinkAnalysisService,
        content_processing_service: ContentProcessingService,
        config: ProcessingConfig,
    ) -> None:
        """Initialize auto-link generation use case."""
        self.file_repository = file_repository
        self.link_analysis_service = link_analysis_service
        self.content_processing_service = content_processing_service
        self.config = config

    def execute(self, request: AutoLinkGenerationRequest) -> AutoLinkGenerationResult:
        """Execute automatic link generation."""
        # 1. Load all markdown files from vault
        files = self.file_repository.load_vault(request.vault_path)

        if not files:
            return AutoLinkGenerationResult(
                vault_path=str(request.vault_path),
                total_files_processed=0,
                total_links_created=0,
                total_aliases_added=0,
                file_updates=[],
                processing_results=[],
                skipped_files=[],
                errors=["No markdown files found in vault"],
                summary={"error": "No files to process"},
            )

        # 2. Build file registry (id -> file mapping)
        file_registry = self._build_file_registry(files)

        # 3. Filter files to process if specific targets are provided
        if request.target_files:
            files_to_process = [f for f in files if str(f.path) in request.target_files]
        else:
            files_to_process = files

        # 4. Process each file for link generation
        file_updates = []
        processing_results = []
        skipped_files = []
        errors = []
        total_links_created = 0
        total_aliases_added = 0

        # Configure content processing service
        self.content_processing_service.max_links_per_file = request.max_links_per_file

        for file in files_to_process:
            try:
                # Extract exclusion zones
                exclusion_zones = self.link_analysis_service.extract_exclusion_zones(
                    file.content
                )

                # Configure table exclusion
                if request.exclude_tables:
                    self.link_analysis_service.exclude_tables = True

                # Find link candidates
                candidates = self.content_processing_service.find_link_candidates(
                    file.content, file_registry, exclusion_zones
                )

                if not candidates:
                    skipped_files.append(f"No link candidates found: {file.path}")
                    continue

                # Process candidates and generate replacements
                processing_result = (
                    self.content_processing_service.apply_link_replacements(
                        file.content, candidates
                    )
                )

                processing_results.append(processing_result)

                # Generate bidirectional updates
                bidirectional_updates = self._generate_bidirectional_updates(
                    file, processing_result, file_registry
                )

                file_updates.extend(bidirectional_updates)

                # Count links and aliases
                links_in_file = len(processing_result.applied_replacements)
                total_links_created += links_in_file

                # Count aliases that will be added
                aliases_in_file = sum(
                    1
                    for update in bidirectional_updates
                    if update.update_type == "add_alias"
                )
                total_aliases_added += aliases_in_file

            except Exception as e:
                error_msg = f"Error processing {file.path}: {e!s}"
                errors.append(error_msg)
                continue

        # 5. Apply updates if not dry-run
        if not request.dry_run:
            self._apply_file_updates(file_updates)

        # 6. Generate summary
        summary = self._generate_summary(
            files_to_process, file_updates, processing_results, errors
        )

        return AutoLinkGenerationResult(
            vault_path=str(request.vault_path),
            total_files_processed=len(files_to_process) - len(skipped_files),
            total_links_created=total_links_created,
            total_aliases_added=total_aliases_added,
            file_updates=file_updates,
            processing_results=processing_results,
            skipped_files=skipped_files,
            errors=errors,
            summary=summary,
        )

    def _build_file_registry(
        self, files: list[MarkdownFile]
    ) -> dict[str, MarkdownFile]:
        """Build a registry mapping file IDs to MarkdownFile objects."""
        registry = {}

        for file in files:
            # Extract file ID from frontmatter or filename
            file_id = file.extract_file_id()
            if file_id:
                registry[file_id] = file

        return registry

    def _generate_bidirectional_updates(
        self,
        source_file: MarkdownFile,
        processing_result: ContentProcessingResult,
        file_registry: dict[str, MarkdownFile],
    ) -> list[FileUpdate]:
        """Generate updates for both source and target files."""
        updates = []

        # 1. Update source file with new WikiLinks
        if processing_result.applied_replacements:
            source_update = FileUpdate(
                file_path=source_file.path,
                update_type="add_wikilink",
                original_content=processing_result.original_content,
                new_content=processing_result.processed_content,
                applied_replacements=processing_result.applied_replacements,
            )
            updates.append(source_update)

        # 2. Update target files with new aliases
        alias_updates = self._generate_alias_updates(
            processing_result.applied_replacements, file_registry
        )
        updates.extend(alias_updates)

        return updates

    def _generate_alias_updates(
        self,
        replacements: list[LinkReplacement],
        file_registry: dict[str, MarkdownFile],
    ) -> list[FileUpdate]:
        """Generate alias updates for target files."""
        updates = []
        alias_additions = {}  # file_id -> set of aliases to add

        for replacement in replacements:
            target_file_id = replacement.target_file_id
            target_file = file_registry.get(target_file_id)

            if not target_file:
                continue

            # Extract alias from the replacement text
            # Format: [[file_id|alias]] or [[file_id]]
            if "|" in replacement.replacement_text:
                # Extract alias from [[file_id|alias]]
                alias_part = replacement.replacement_text.split("|")[1]
                # Remove closing brackets
                if alias_part.endswith("]]"):
                    alias_part = alias_part[:-2]
                alias_to_add = alias_part.strip()

                # Check if this alias is already in the target file
                existing_aliases = [
                    alias.lower() for alias in target_file.frontmatter.aliases
                ]
                title_lower = (
                    target_file.frontmatter.title.lower()
                    if target_file.frontmatter.title
                    else ""
                )

                # Only add if it's not already present
                if (
                    alias_to_add.lower() not in existing_aliases
                    and alias_to_add.lower() != title_lower
                ):
                    if target_file_id not in alias_additions:
                        alias_additions[target_file_id] = set()
                    alias_additions[target_file_id].add(alias_to_add)

        # Create FileUpdate objects for alias additions
        for file_id, aliases_to_add in alias_additions.items():
            target_file = file_registry[file_id]
            new_aliases = list(target_file.frontmatter.aliases) + list(aliases_to_add)

            update = FileUpdate(
                file_path=target_file.path,
                update_type="add_alias",
                frontmatter_changes={"aliases": new_aliases},
            )
            updates.append(update)

        return updates

    def _apply_file_updates(self, file_updates: list[FileUpdate]) -> None:
        """Apply file updates to the actual files."""
        for update in file_updates:
            try:
                if update.update_type == "add_wikilink":
                    # Update file content with new WikiLinks
                    if update.new_content:
                        self.file_repository.save_file_content(
                            update.file_path, update.new_content
                        )

                elif update.update_type == "add_alias" and update.frontmatter_changes:
                    # Update frontmatter with new aliases
                    self.file_repository.update_frontmatter(
                        update.file_path, update.frontmatter_changes
                    )

            except Exception as e:
                # Log error but continue with other updates
                print(f"Error applying update to {update.file_path}: {e}")

    def _generate_summary(
        self,
        files_processed: list[MarkdownFile],
        file_updates: list[FileUpdate],
        processing_results: list[ContentProcessingResult],
        errors: list[str],
    ) -> dict[str, Any]:
        """Generate summary statistics."""
        # Count different types of updates
        wikilink_updates = sum(
            1 for update in file_updates if update.update_type == "add_wikilink"
        )
        alias_updates = sum(
            1 for update in file_updates if update.update_type == "add_alias"
        )

        # Count conflicts resolved
        total_conflicts = sum(
            len(result.conflicts_resolved) for result in processing_results
        )

        # Count skipped candidates
        total_skipped = sum(
            len(result.skipped_candidates) for result in processing_results
        )

        # Files with links added
        files_with_links = len(
            {
                update.file_path
                for update in file_updates
                if update.update_type == "add_wikilink"
            }
        )

        # Files with aliases added
        files_with_aliases = len(
            {
                update.file_path
                for update in file_updates
                if update.update_type == "add_alias"
            }
        )

        return {
            "files_processed": len(files_processed),
            "files_with_links_added": files_with_links,
            "files_with_aliases_added": files_with_aliases,
            "wikilink_updates": wikilink_updates,
            "alias_updates": alias_updates,
            "conflicts_resolved": total_conflicts,
            "candidates_skipped": total_skipped,
            "errors_encountered": len(errors),
            "success_rate": (
                f"{((len(files_processed) - len(errors)) / len(files_processed) * 100):.1f}%"  # noqa: E501
                if files_processed
                else "0%"
            ),
        }

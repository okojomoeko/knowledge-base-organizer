"""Use case for automatic WikiLink generation from plain text mentions."""

import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from ..domain.models import MarkdownFile
from ..domain.services.ai_services import EmbeddingService, SearchResult, VectorStore
from ..domain.services.content_processing_service import (
    ContentProcessingResult,
    ContentProcessingService,
    LinkReplacement,
)
from ..domain.services.link_analysis_service import LinkAnalysisService, TextRange
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
    max_files_to_process: int | None = None  # Maximum number of files to process
    exclude_content_patterns: list[str] | None = (
        None  # Content patterns to exclude from linking
    )
    preserve_frontmatter: bool = True  # Preserve original frontmatter format
    # Semantic enhancement options
    enable_semantic: bool = False  # Enable semantic similarity search
    semantic_threshold: float = 0.7  # Minimum similarity threshold for semantic links
    semantic_max_candidates: int = 5  # Maximum semantic candidates per context


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
        embedding_service: EmbeddingService | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        """Initialize auto-link generation use case."""
        self.file_repository = file_repository
        self.link_analysis_service = link_analysis_service
        self.content_processing_service = content_processing_service
        self.config = config
        self.embedding_service = embedding_service
        self.vector_store = vector_store

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

        # 4. Limit number of files to process if specified (useful for large vaults)
        if (
            request.max_files_to_process
            and len(files_to_process) > request.max_files_to_process
        ):
            files_to_process = files_to_process[: request.max_files_to_process]

        # 5. Process each file for link generation
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

                # Add custom content pattern exclusions if specified
                if request.exclude_content_patterns:
                    custom_exclusions = self._extract_custom_exclusion_zones(
                        file.content, request.exclude_content_patterns
                    )
                    exclusion_zones.extend(custom_exclusions)

                # Configure table exclusion
                if request.exclude_tables:
                    self.link_analysis_service.exclude_tables = True

                # Find link candidates
                candidates = self.link_analysis_service.find_link_candidates(
                    file.content,
                    file_registry,
                    exclusion_zones,
                    current_file_id=file.extract_file_id(),
                )

                # Add semantic candidates if enabled
                if request.enable_semantic and self._semantic_services_available():
                    semantic_candidates = self._find_semantic_candidates(
                        file,
                        file_registry,
                        exclusion_zones,
                        request.semantic_threshold,
                        request.semantic_max_candidates,
                    )
                    candidates.extend(semantic_candidates)

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

        # 6. Apply updates if not dry-run
        if not request.dry_run:
            self._apply_file_updates(file_updates, request.preserve_frontmatter)

        # 7. Generate summary
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

    def _apply_file_updates(
        self, file_updates: list[FileUpdate], preserve_frontmatter: bool = True
    ) -> None:
        """Apply file updates to the actual files."""
        for update in file_updates:
            try:
                # Load the full MarkdownFile object to ensure we have all its parts
                markdown_file = self.file_repository.load_file(update.file_path)

                if update.update_type == "add_wikilink" and update.new_content:
                    # Update the content of the MarkdownFile object
                    markdown_file.content = update.new_content
                    # Save the entire file, using the preserve_frontmatter setting
                    self.file_repository.save_file(
                        markdown_file,
                        backup=True,
                        preserve_frontmatter=preserve_frontmatter,
                    )

                elif update.update_type == "add_alias" and update.frontmatter_changes:
                    # Update frontmatter with new aliases
                    self.file_repository.update_frontmatter(
                        update.file_path,
                        update.frontmatter_changes,
                        backup=True,
                        preserve_frontmatter=preserve_frontmatter,
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

    def _extract_custom_exclusion_zones(
        self, content: str, patterns: list[str]
    ) -> list:
        """Extract custom exclusion zones based on regex patterns.

        Args:
            content: The markdown content to analyze
            patterns: List of regex patterns to exclude from auto-linking

        Returns:
            List of TextRange objects representing exclusion zones
        """

        exclusion_zones = []
        lines = content.split("\n")

        for pattern in patterns:
            try:
                regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                for line_num, line in enumerate(lines, 1):
                    for match in regex.finditer(line):
                        exclusion_zones.append(
                            TextRange(
                                start_line=line_num,
                                end_line=line_num,
                                start_column=match.start(),
                                end_column=match.end(),
                            )
                        )
            except re.error:
                # Skip invalid regex patterns
                continue

        return exclusion_zones

    def _semantic_services_available(self) -> bool:
        """Check if semantic services are available."""
        return self.embedding_service is not None and self.vector_store is not None

    def _find_semantic_candidates(
        self,
        source_file: MarkdownFile,
        file_registry: dict[str, MarkdownFile],
        exclusion_zones: list[TextRange],  # noqa: ARG002
        threshold: float,
        max_candidates: int,
    ) -> list:
        """
        Find semantic link candidates using vector similarity search.

        Args:
            source_file: The file to find candidates for
            file_registry: Registry of all files
            exclusion_zones: Areas to exclude from linking
            threshold: Minimum similarity threshold
            max_candidates: Maximum number of candidates to return

        Returns:
            List of semantic link candidates
        """
        if not self._semantic_services_available():
            return []

        try:
            # Prepare content for embedding (similar to indexing)
            content_for_embedding = self._prepare_content_for_semantic_search(
                source_file
            )

            # Generate embedding for source content
            embedding_result = self.embedding_service.create_embedding(
                content_for_embedding
            )

            # Search for similar documents
            search_results = self.vector_store.search(
                query_vector=embedding_result.vector,
                k=max_candidates * 2,  # Get more results to filter
                threshold=threshold,
            )

            # Convert search results to link candidates
            semantic_candidates = []
            for result in search_results[:max_candidates]:
                candidate = self._create_semantic_link_candidate(
                    result, source_file, file_registry
                )
                if candidate:
                    semantic_candidates.append(candidate)

            return semantic_candidates

        except Exception as e:
            # Log error but don't fail the entire process
            print(f"Error finding semantic candidates for {source_file.path}: {e}")
            return []

    def _prepare_content_for_semantic_search(self, file: MarkdownFile) -> str:
        """
        Prepare file content for semantic search embedding.

        Args:
            file: MarkdownFile to prepare

        Returns:
            Prepared content string
        """
        parts = []

        # Add title if available
        title = file.frontmatter.get("title")
        if title:
            parts.append(f"Title: {title}")

        # Add tags if available
        tags = file.frontmatter.get("tags", [])
        if tags:
            parts.append(f"Tags: {', '.join(tags)}")

        # Add main content (limit to first 1000 characters for context)
        content = file.content.strip()
        if content:
            # Remove frontmatter from content if present
            if content.startswith("---"):
                lines = content.split("\n")
                frontmatter_end = -1
                for i, line in enumerate(lines[1:], 1):
                    if line.strip() == "---":
                        frontmatter_end = i
                        break
                if frontmatter_end > 0:
                    content = "\n".join(lines[frontmatter_end + 1 :]).strip()

            # Limit content length for context
            if len(content) > 1000:
                content = content[:1000] + "..."

            parts.append(content)

        return "\n\n".join(parts)

    def _create_semantic_link_candidate(
        self,
        search_result: SearchResult,
        source_file: MarkdownFile,
        file_registry: dict[str, MarkdownFile],
    ):
        """
        Create a link candidate from a semantic search result.

        Args:
            search_result: Result from vector search
            source_file: Source file for the link
            file_registry: Registry of all files

        Returns:
            Link candidate object or None if not suitable
        """
        # Get target file from search result
        target_file_path = search_result.metadata.get("file_path")
        if not target_file_path:
            return None

        # Find target file in registry
        target_file = None
        for file in file_registry.values():
            if str(file.path) == target_file_path:
                target_file = file
                break

        if not target_file:
            return None

        # Don't link to self
        if target_file.path == source_file.path:
            return None

        # Create a semantic link candidate
        # This is a simplified version - in a full implementation,
        # you would create proper LinkCandidate objects that integrate
        # with the existing link analysis system

        # For now, we'll create a basic candidate structure
        # that can be processed by the content processing service
        target_title = target_file.frontmatter.get("title", target_file.path.stem)
        target_id = target_file.extract_file_id()

        if not target_id:
            return None

        # Create a candidate that represents a semantic relationship
        # This would need to be integrated with the existing LinkCandidate system
        return {
            "text": target_title,
            "target_file_id": target_id,
            "similarity_score": search_result.similarity_score,
            "candidate_type": "semantic",
            "position": None,  # Semantic links don't have specific positions
        }

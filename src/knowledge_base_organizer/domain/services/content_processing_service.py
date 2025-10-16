"Content processing service for safe text replacement and link generation."

import re

from pydantic import BaseModel, ConfigDict

from ..models import MarkdownFile, TextPosition, TextRange
from .link_analysis_service import LinkCandidate


class LinkReplacement(BaseModel):
    """Represents a text replacement for creating a WikiLink."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    original_text: str
    replacement_text: str
    position: TextPosition
    target_file_id: str
    priority: int = 0  # Higher priority replacements are applied first


class ConflictResolution(BaseModel):
    """Represents a conflict between overlapping link candidates."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    conflicting_candidates: list[LinkCandidate]
    resolved_candidate: LinkCandidate | None
    resolution_reason: str


class ContentProcessingResult(BaseModel):
    """Result of content processing operations."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    original_content: str
    processed_content: str
    applied_replacements: list[LinkReplacement]
    conflicts_resolved: list[ConflictResolution]
    skipped_candidates: list[LinkCandidate]


class ContentProcessingService:
    """Service for safe text replacement and link candidate processing."""

    def __init__(self, max_links_per_file: int = 50):
        """Initialize the content processing service.

        Args:
            max_links_per_file: Maximum number of links to create per file
        """
        self.max_links_per_file = max_links_per_file

    def resolve_conflicts(
        self, candidates: list[LinkCandidate]
    ) -> list[ConflictResolution]:
        """Resolve conflicts between overlapping link candidates.

        Args:
            candidates: List of link candidates to check for conflicts

        Returns:
            List of ConflictResolution objects
        """
        conflicts = []
        processed_positions = set()

        # Group candidates by overlapping positions
        for i, candidate in enumerate(candidates):
            if i in processed_positions:
                continue

            overlapping = [candidate]
            current_range = self._get_text_range(
                candidate.position, len(candidate.text)
            )

            # Find all candidates that overlap with current candidate
            for j, other_candidate in enumerate(candidates[i + 1 :], i + 1):
                if j in processed_positions:
                    continue

                other_range = self._get_text_range(
                    other_candidate.position, len(other_candidate.text)
                )

                if self._ranges_overlap(current_range, other_range):
                    overlapping.append(other_candidate)
                    processed_positions.add(j)

            # If we have overlapping candidates, resolve the conflict
            if len(overlapping) > 1:
                resolved = self._resolve_single_conflict(overlapping)
                conflicts.append(resolved)
                processed_positions.add(i)

        return conflicts

    def apply_link_replacements(
        self,
        content: str,
        candidates: list[LinkCandidate],
        conflicts: list[ConflictResolution] | None = None,
    ) -> ContentProcessingResult:
        """Apply WikiLink replacements to content safely.

        Args:
            content: Original markdown content
            candidates: Link candidates to apply
            conflicts: Resolved conflicts (if any)

        Returns:
            ContentProcessingResult with processed content and metadata
        """
        if conflicts is None:
            conflicts = self.resolve_conflicts(candidates)

        # Filter candidates based on conflict resolution
        valid_candidates = self._filter_valid_candidates(candidates, conflicts)

        # Limit the number of links per file
        if len(valid_candidates) > self.max_links_per_file:
            valid_candidates = valid_candidates[: self.max_links_per_file]
            skipped_candidates = candidates[self.max_links_per_file :]
        else:
            skipped_candidates = []

        # Create replacements
        replacements = []
        for candidate in valid_candidates:
            replacement_text = self._create_wikilink_text(candidate)
            replacement = LinkReplacement(
                original_text=candidate.text,
                replacement_text=replacement_text,
                position=candidate.position,
                target_file_id=candidate.target_file_id,
            )
            replacements.append(replacement)

        # Apply replacements in reverse order (from end to beginning)
        # to maintain position accuracy
        replacements.sort(
            key=lambda r: (r.position.line_number, r.position.column_start),
            reverse=True,
        )

        processed_content = self._apply_replacements_to_content(content, replacements)

        return ContentProcessingResult(
            original_content=content,
            processed_content=processed_content,
            applied_replacements=replacements,
            conflicts_resolved=conflicts,
            skipped_candidates=skipped_candidates,
        )

    def _find_text_matches(
        self,
        target_text: str,
        file_id: str,
        lines: list[str],
        exclusion_zones: list[TextRange],
        file_registry: dict[str, MarkdownFile],
    ) -> list[LinkCandidate]:
        """Find exact matches for a target text in the content."""
        candidates = []

        # Use word boundaries for exact matching
        pattern = re.compile(r"\b" + re.escape(target_text) + r"\b", re.IGNORECASE)

        for line_num, line in enumerate(lines, 1):
            for match in pattern.finditer(line):
                position = TextPosition(
                    line_number=line_num,
                    column_start=match.start(),
                    column_end=match.end(),
                )

                # Check if this position is in an exclusion zone
                if self._is_in_exclusion_zone(position, exclusion_zones):
                    continue

                # Determine the best alias to use
                matched_text = match.group()
                target_file = file_registry[file_id]
                suggested_alias = self._determine_best_alias(matched_text, target_file)

                candidate = LinkCandidate(
                    text=matched_text,
                    target_file_id=file_id,
                    suggested_alias=suggested_alias,
                    position=position,
                )
                candidates.append(candidate)

        return candidates

    def _is_in_exclusion_zone(
        self,
        position: TextPosition,
        exclusion_zones: list[TextRange],
    ) -> bool:
        """Check if a position falls within any exclusion zone."""
        for zone in exclusion_zones:
            if zone.start_line <= position.line_number <= zone.end_line:
                # Single line zone
                if zone.start_line == zone.end_line:
                    if zone.start_column <= position.column_start < zone.end_column:
                        return True
                # Multi-line zone
                elif (
                    (
                        position.line_number == zone.start_line
                        and position.column_start >= zone.start_column
                    )
                    or (
                        position.line_number == zone.end_line
                        and position.column_start < zone.end_column
                    )
                    or (zone.start_line < position.line_number < zone.end_line)
                ):
                    return True

        return False

    def _determine_best_alias(
        self,
        matched_text: str,
        target_file: MarkdownFile,
    ) -> str | None:
        """Determine the best alias to use for a WikiLink."""
        # If the matched text is the same as the title, no alias needed
        if (
            target_file.frontmatter.title
            and matched_text.lower() == target_file.frontmatter.title.lower()
        ):
            return None

        # If the matched text is in the aliases, use it as alias
        for alias in target_file.frontmatter.aliases:
            if matched_text.lower() == alias.lower():
                return matched_text

        # Otherwise, use the matched text as alias
        return matched_text

    def _get_text_range(
        self,
        position: TextPosition,
        text_length: int,
    ) -> tuple[int, int, int]:
        """Get a text range tuple for overlap checking."""
        return (
            position.line_number,
            position.column_start,
            position.column_start + text_length,
        )

    def _ranges_overlap(
        self,
        range1: tuple[int, int, int],
        range2: tuple[int, int, int],
    ) -> bool:
        """Check if two text ranges overlap."""
        line1, start1, end1 = range1
        line2, start2, end2 = range2

        # Different lines don't overlap
        if line1 != line2:
            return False

        # Check column overlap
        return not (end1 <= start2 or end2 <= start1)

    def _resolve_single_conflict(
        self,
        overlapping_candidates: list[LinkCandidate],
    ) -> ConflictResolution:
        """Resolve a single conflict between overlapping candidates."""
        # Priority rules for conflict resolution:
        # 1. Longer text matches have higher priority
        # 2. Exact title matches have higher priority than alias matches
        # 3. Higher confidence scores have higher priority

        best_candidate = None
        best_score = -1.0

        for candidate in overlapping_candidates:
            score = self._calculate_candidate_priority(candidate)
            if score > best_score:
                best_score = score
                best_candidate = candidate

        reason = (
            f"Selected longest/highest priority match from "
            f"{len(overlapping_candidates)} overlapping candidates"
        )

        return ConflictResolution(
            conflicting_candidates=overlapping_candidates,
            resolved_candidate=best_candidate,
            resolution_reason=reason,
        )

    def _calculate_candidate_priority(self, candidate: LinkCandidate) -> float:
        """Calculate priority score for a candidate."""
        score = 0.0

        # Longer text gets higher priority
        score += len(candidate.text) * 10

        # No alias (exact title match) gets bonus
        if candidate.suggested_alias is None:
            score += 50

        # Confidence score
        score += candidate.confidence * 20

        return score

    def _filter_valid_candidates(
        self,
        candidates: list[LinkCandidate],
        conflicts: list[ConflictResolution],
    ) -> list[LinkCandidate]:
        """Filter candidates based on conflict resolution."""
        # Get all candidates that were involved in conflicts
        conflicted_candidates = set()
        resolved_candidates = []

        for conflict in conflicts:
            for candidate in conflict.conflicting_candidates:
                conflicted_candidates.add(id(candidate))

            if conflict.resolved_candidate:
                resolved_candidates.append(conflict.resolved_candidate)

        # Keep non-conflicted candidates and resolved candidates
        valid_candidates = []

        for candidate in candidates:
            if id(candidate) not in conflicted_candidates:
                valid_candidates.append(candidate)

        valid_candidates.extend(resolved_candidates)

        return valid_candidates

    def _create_wikilink_text(self, candidate: LinkCandidate) -> str:
        """Create WikiLink text from a candidate."""
        if candidate.suggested_alias:
            return f"[[{candidate.target_file_id}|{candidate.suggested_alias}]]"
        return f"[[{candidate.target_file_id}]]"

    def _apply_replacements_to_content(
        self,
        content: str,
        replacements: list[LinkReplacement],
    ) -> str:
        """Apply text replacements to content."""
        lines = content.split("\n")

        # Apply replacements in reverse order to maintain position accuracy
        for replacement in replacements:
            line_idx = replacement.position.line_number - 1
            if 0 <= line_idx < len(lines):
                line = lines[line_idx]
                start = replacement.position.column_start
                end = replacement.position.column_end

                # Verify the text matches what we expect
                if line[start:end] == replacement.original_text:
                    lines[line_idx] = (
                        line[:start] + replacement.replacement_text + line[end:]
                    )

        return "\n".join(lines)

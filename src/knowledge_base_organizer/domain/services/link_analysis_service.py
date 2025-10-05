"""Link analysis service for detecting and analyzing links in markdown content."""

import re

from pydantic import BaseModel, ConfigDict

from ..models import MarkdownFile, TextPosition


class TextRange(BaseModel):
    """Represents a range of text that should be excluded from link processing."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    start_line: int
    start_column: int
    end_line: int
    end_column: int
    zone_type: str  # "frontmatter", "wikilink", "regular_link", "link_ref_def", "table", "template_variable"


class LinkCandidate(BaseModel):
    """Represents a potential link candidate found in text."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    text: str
    target_file_id: str
    suggested_alias: str | None
    position: TextPosition
    confidence: float = 1.0


class DeadLink(BaseModel):
    """Represents a broken link found in content."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    source_file: str
    link_text: str
    link_type: str  # "wikilink", "regular_link", "link_ref_def"
    line_number: int
    target: str
    suggested_fixes: list[str] = []


class LinkDensityMetrics(BaseModel):
    """Metrics about link density in a file."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    total_words: int
    total_links: int
    wiki_links: int
    regular_links: int
    link_ref_defs: int
    link_density: float  # links per 100 words
    unique_targets: int


class LinkAnalysisService:
    """Service for analyzing and processing links in markdown content."""

    def __init__(self, exclude_tables: bool = False):
        """Initialize the link analysis service.

        Args:
            exclude_tables: Whether to exclude table content from link processing
        """
        self.exclude_tables = exclude_tables

    def extract_exclusion_zones(self, content: str) -> list[TextRange]:
        """Extract areas where auto-linking should be avoided.

        This includes:
        - Frontmatter sections (--- ... ---)
        - Existing WikiLinks ([[...]])
        - Regular markdown links ([...](...))
        - Link Reference Definitions ([id|alias]: path "title")
        - Tables (if configured)

        Args:
            content: The markdown content to analyze

        Returns:
            List of TextRange objects representing exclusion zones
        """
        exclusion_zones = []
        lines = content.split("\n")

        # Track frontmatter boundaries
        frontmatter_start = None
        frontmatter_end = None
        in_frontmatter = False

        for line_num, line in enumerate(lines, 1):
            # Detect frontmatter boundaries
            if line.strip() == "---":
                if frontmatter_start is None:
                    frontmatter_start = line_num
                    in_frontmatter = True
                elif in_frontmatter:
                    frontmatter_end = line_num
                    in_frontmatter = False
                    # Add frontmatter exclusion zone
                    exclusion_zones.append(
                        TextRange(
                            start_line=frontmatter_start,
                            start_column=0,
                            end_line=frontmatter_end,
                            end_column=len(line),
                            zone_type="frontmatter",
                        )
                    )

            # Skip processing if we're in frontmatter
            if in_frontmatter:
                continue

            # Detect WikiLinks: [[...]]
            wiki_pattern = re.compile(r"\[\[([^\]]+)\]\]")
            for match in wiki_pattern.finditer(line):
                exclusion_zones.append(
                    TextRange(
                        start_line=line_num,
                        start_column=match.start(),
                        end_line=line_num,
                        end_column=match.end(),
                        zone_type="wikilink",
                    )
                )

            # Detect regular markdown links: [text](url)
            regular_link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
            for match in regular_link_pattern.finditer(line):
                exclusion_zones.append(
                    TextRange(
                        start_line=line_num,
                        start_column=match.start(),
                        end_line=line_num,
                        end_column=match.end(),
                        zone_type="regular_link",
                    )
                )

            # Detect Link Reference Definitions: [id|alias]: path "title"
            link_ref_pattern = re.compile(
                r"^\[([^|\]]+)\|([^\]]+)\]:\s*([^\s]+)(?:\s+\"([^\"]+)\")?"
            )
            if link_ref_pattern.match(line.strip()):
                exclusion_zones.append(
                    TextRange(
                        start_line=line_num,
                        start_column=0,
                        end_line=line_num,
                        end_column=len(line),
                        zone_type="link_ref_def",
                    )
                )

            # Detect table rows (if configured to exclude)
            if self.exclude_tables and self._is_table_row(line):
                exclusion_zones.append(
                    TextRange(
                        start_line=line_num,
                        start_column=0,
                        end_line=line_num,
                        end_column=len(line),
                        zone_type="table",
                    )
                )

            # Detect template variables and template blocks
            # Template variables: ${...}, {{...}}, <% ... %>
            template_patterns = [
                re.compile(r"\$\{[^}]*\}"),  # ${variable}
                re.compile(r"\{\{[^}]*\}\}"),  # {{variable}}
                re.compile(r"<%[^%]*%>"),  # <% template %>
                re.compile(r"<%\*[^*]*\*%>"),  # <%* template *%>
            ]

            for pattern in template_patterns:
                for match in pattern.finditer(line):
                    exclusion_zones.append(
                        TextRange(
                            start_line=line_num,
                            start_column=match.start(),
                            end_line=line_num,
                            end_column=match.end(),
                            zone_type="template_variable",
                        )
                    )

        return exclusion_zones

    def find_link_candidates(
        self,
        content: str,
        file_registry: dict[str, MarkdownFile],
        exclusion_zones: list[TextRange] | None = None,
    ) -> list[LinkCandidate]:
        """Find text that could be converted to WikiLinks.

        Args:
            content: The markdown content to analyze
            file_registry: Dictionary mapping file IDs to MarkdownFile objects
            exclusion_zones: Areas to exclude from link detection

        Returns:
            List of LinkCandidate objects
        """
        if exclusion_zones is None:
            exclusion_zones = self.extract_exclusion_zones(content)

        candidates = []
        lines = content.split("\n")

        # Build a lookup of titles and aliases to file IDs
        title_to_file = {}
        alias_to_file = {}

        for file_id, file in file_registry.items():
            # Map title to file ID
            if file.frontmatter.title:
                title_to_file[file.frontmatter.title.lower()] = file_id

            # Map aliases to file ID
            for alias in file.frontmatter.aliases:
                alias_to_file[alias.lower()] = file_id

        # Combine all possible link targets
        all_targets = {**title_to_file, **alias_to_file}

        for line_num, line in enumerate(lines, 1):
            # Find potential matches for each target
            for target_text, file_id in all_targets.items():
                # Use word boundaries to find exact matches
                pattern = re.compile(
                    r"\b" + re.escape(target_text) + r"\b", re.IGNORECASE
                )

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
                    suggested_alias = self._determine_best_alias(
                        matched_text, file_registry[file_id]
                    )

                    candidate = LinkCandidate(
                        text=matched_text,
                        target_file_id=file_id,
                        suggested_alias=suggested_alias,
                        position=position,
                    )
                    candidates.append(candidate)

        return candidates

    def detect_dead_links(
        self,
        files: list[MarkdownFile],
        file_registry: dict[str, MarkdownFile],
    ) -> list[DeadLink]:
        """Detect WikiLinks and regular links that are broken.

        Args:
            files: List of MarkdownFile objects to check
            file_registry: Dictionary mapping file IDs to MarkdownFile objects

        Returns:
            List of DeadLink objects
        """
        dead_links = []

        for file in files:
            # Check WikiLinks
            for wiki_link in file.wiki_links:
                if wiki_link.target_id not in file_registry:
                    # Try to find similar file IDs for suggestions
                    suggestions = self._find_similar_file_ids(
                        wiki_link.target_id, file_registry
                    )

                    dead_link = DeadLink(
                        source_file=str(file.path),
                        link_text=str(wiki_link),
                        link_type="wikilink",
                        line_number=wiki_link.line_number,
                        target=wiki_link.target_id,
                        suggested_fixes=suggestions,
                    )
                    dead_links.append(dead_link)

            # Check regular links for empty or invalid targets
            for regular_link in file.regular_links:
                if not regular_link.url or not regular_link.url.strip():
                    dead_link = DeadLink(
                        source_file=str(file.path),
                        link_text=f"[{regular_link.text}]({regular_link.url})",
                        link_type="regular_link",
                        line_number=regular_link.line_number,
                        target=regular_link.url,
                        suggested_fixes=["Remove empty link or add valid URL"],
                    )
                    dead_links.append(dead_link)

            # Check Link Reference Definitions
            for link_ref in file.link_reference_definitions:
                # For now, we'll just check if the path is empty
                # More sophisticated validation could check if the path exists
                if not link_ref.path or not link_ref.path.strip():
                    dead_link = DeadLink(
                        source_file=str(file.path),
                        link_text=f"[{link_ref.id}|{link_ref.alias}]: {link_ref.path}",
                        link_type="link_ref_def",
                        line_number=link_ref.line_number,
                        target=link_ref.path,
                        suggested_fixes=["Add valid path to Link Reference Definition"],
                    )
                    dead_links.append(dead_link)

        return dead_links

    def calculate_link_density(self, file: MarkdownFile) -> LinkDensityMetrics:
        """Calculate various link metrics for a file.

        Args:
            file: The MarkdownFile to analyze

        Returns:
            LinkDensityMetrics object with calculated metrics
        """
        # Count words in content (excluding frontmatter)
        content_without_frontmatter = self._extract_body_content(file.content)
        words = len(content_without_frontmatter.split())

        # Count different types of links
        wiki_links_count = len(file.wiki_links)
        regular_links_count = len(file.regular_links)
        link_ref_defs_count = len(file.link_reference_definitions)
        total_links = wiki_links_count + regular_links_count + link_ref_defs_count

        # Calculate link density (links per 100 words)
        link_density = (total_links / words * 100) if words > 0 else 0

        # Count unique targets
        unique_targets = set()
        for wiki_link in file.wiki_links:
            unique_targets.add(wiki_link.target_id)
        for regular_link in file.regular_links:
            unique_targets.add(regular_link.url)
        for link_ref in file.link_reference_definitions:
            unique_targets.add(link_ref.path)

        return LinkDensityMetrics(
            total_words=words,
            total_links=total_links,
            wiki_links=wiki_links_count,
            regular_links=regular_links_count,
            link_ref_defs=link_ref_defs_count,
            link_density=link_density,
            unique_targets=len(unique_targets),
        )

    def _is_table_row(self, line: str) -> bool:
        """Check if a line is part of a markdown table."""
        stripped = line.strip()
        return stripped.startswith("|") and stripped.endswith("|")

    def _is_in_exclusion_zone(
        self, position: TextPosition, exclusion_zones: list[TextRange]
    ) -> bool:
        """Check if a position falls within any exclusion zone."""
        for zone in exclusion_zones:
            # Check if position is within the zone
            if zone.start_line <= position.line_number <= zone.end_line:
                # If it's a single line zone, check column positions
                if zone.start_line == zone.end_line:
                    if zone.start_column <= position.column_start < zone.end_column:
                        return True
                # If it's a multi-line zone
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
        self, matched_text: str, target_file: MarkdownFile
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

    def _find_similar_file_ids(
        self, target_id: str, file_registry: dict[str, MarkdownFile]
    ) -> list[str]:
        """Find file IDs similar to the target ID for suggestions."""
        suggestions = []

        # Simple similarity check - look for IDs that start with the same prefix
        if len(target_id) >= 4:
            prefix = target_id[:4]
            for file_id in file_registry:
                if file_id.startswith(prefix) and file_id != target_id:
                    suggestions.append(f"Did you mean '{file_id}'?")

        # Limit suggestions to avoid overwhelming output
        return suggestions[:3]

    def _extract_body_content(self, content: str) -> str:
        """Extract body content excluding frontmatter."""
        lines = content.split("\n")
        in_frontmatter = False
        frontmatter_ended = False
        body_lines = []

        for line in lines:
            if line.strip() == "---":
                if not in_frontmatter and not frontmatter_ended:
                    in_frontmatter = True
                elif in_frontmatter:
                    in_frontmatter = False
                    frontmatter_ended = True
                continue

            if not in_frontmatter:
                body_lines.append(line)

        return "\n".join(body_lines)

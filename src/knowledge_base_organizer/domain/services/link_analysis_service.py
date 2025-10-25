"""Link analysis service for detecting and analyzing links in markdown content."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from ..models import MarkdownFile, TextPosition, TextRange
from .keyword_extraction_manager import KeywordExtractionManager
from .tag_pattern_manager import TagPatternManager


@dataclass
class CodeBlockState:
    """State for tracking code block boundaries."""

    in_code_block: bool = False
    start_line: int = 0


@dataclass
class FrontmatterState:
    """State for tracking frontmatter boundaries."""

    start_line: int | None = None
    in_frontmatter: bool = False
    frontmatter_processed: bool = False  # Track if frontmatter has been processed


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
    variation_type: str | None = None  # "katakana_variation", "english_japanese", etc.


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


class OrphanedNote(BaseModel):
    """Represents an orphaned note with connection suggestions."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    file_path: str
    file_id: str
    title: str | None
    tags: list[str]
    incoming_links: int
    outgoing_links: int
    connection_suggestions: list["ConnectionSuggestion"]
    isolation_score: float  # 0.0 (well-connected) to 1.0 (completely isolated)


class ConnectionSuggestion(BaseModel):
    """Represents a suggested connection to another note."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    target_file_id: str
    target_title: str | None
    connection_type: str  # "tag_similarity", "keyword_match", "content_similarity"
    confidence: float  # 0.0 to 1.0
    reason: str
    suggested_link_text: str | None = None


class LinkAnalysisService:
    """Service for analyzing and processing links in markdown content."""

    def __init__(self, exclude_tables: bool = False, config_dir: Path | None = None):
        """Initialize the link analysis service.

        Args:
            exclude_tables: Whether to exclude table content from link processing
            config_dir: Configuration directory for Japanese processing patterns
        """
        self.exclude_tables = exclude_tables
        # Initialize Japanese processing capabilities
        self.tag_pattern_manager = TagPatternManager(config_dir)
        self.japanese_enabled = True
        # Initialize keyword extraction manager
        self.keyword_manager = KeywordExtractionManager(config_dir)

    def extract_exclusion_zones(self, content: str) -> list[TextRange]:
        """Extract areas where auto-linking should be avoided.

        This includes:
        - Frontmatter sections (--- ... ---)
        - Existing WikiLinks ([[...]])
        - Regular markdown links ([...](...))
        - Link Reference Definitions ([id|alias]: path "title")
        - Tables (if configured)
        - H1 headers (# ...)
        - HTML tags (<a>...</a>)
        - Code blocks (```...``` and `...`)
        - URLs (http://... or https://...)

        Args:
            content: The markdown content to analyze

        Returns:
            List of TextRange objects representing exclusion zones
        """
        exclusion_zones = []
        lines = content.split("\n")
        patterns = self._compile_exclusion_patterns()

        # Track frontmatter and code block boundaries
        code_state = CodeBlockState()
        frontmatter_state = FrontmatterState()

        for line_num, line in enumerate(lines, 1):
            # Handle code blocks
            if self._handle_code_blocks(line, line_num, code_state, exclusion_zones):
                self._update_code_block_state(line, line_num, code_state)
                continue

            if code_state.in_code_block:
                continue

            # Handle frontmatter
            self._handle_frontmatter(line, line_num, frontmatter_state, exclusion_zones)
            # Skip processing if we're in frontmatter
            if frontmatter_state.in_frontmatter:
                continue

            # Process line-level exclusions
            self._process_line_exclusions(line, line_num, patterns, exclusion_zones)

        return exclusion_zones

    def _compile_exclusion_patterns(self) -> dict[str, re.Pattern]:
        """Compile regex patterns for exclusion zone detection."""
        return {
            "html_a_tag": re.compile(r"<a[^>]*>.*?</a>"),
            "inline_code": re.compile(r"`.*?`"),
            "wiki": re.compile(r"\[\[([^\]]+)\]\]"),
            # Improved pattern to handle nested brackets in link text
            "regular_link": re.compile(
                r"\[(?:[^\[\]]*(?:\[[^\]]*\][^\[\]]*)*)\]\([^)]+\)"
            ),
            "link_ref": re.compile(
                r"\[([^|\]]+)\|([^\]]+)\]:\s*([^\s]+)(?:\s+\"([^\"]+)\")?"
            ),
            "url": re.compile(r"https?://[^\s)]+"),
            "template_var": re.compile(r"\$\{[^}]*\}"),
            "template_block": re.compile(r"\{\{[^}]*\}\}"),
            "template_asp": re.compile(r"<%[^%]*%>"),
            "template_asp_comment": re.compile(r"<%\*[^*]*\*%>"),
        }

    def _handle_code_blocks(
        self,
        line: str,
        line_num: int,
        code_state: CodeBlockState,
        exclusion_zones: list[TextRange],
    ) -> bool:
        """Handle code block detection and zone creation."""
        if line.strip().startswith("```"):
            if not code_state.in_code_block:
                return True  # Starting code block
            # Ending code block
            exclusion_zones.append(
                TextRange(
                    start_line=code_state.start_line,
                    start_column=0,
                    end_line=line_num,
                    end_column=len(line),
                    zone_type="code_block",
                )
            )
            return True
        return False

    def _update_code_block_state(
        self, line: str, line_num: int, code_state: CodeBlockState
    ) -> None:
        """Update code block state."""
        if line.strip().startswith("```"):
            if not code_state.in_code_block:
                code_state.in_code_block = True
                code_state.start_line = line_num
            else:
                code_state.in_code_block = False
                code_state.start_line = 0

    def _handle_frontmatter(
        self,
        line: str,
        line_num: int,
        frontmatter_state: FrontmatterState,
        exclusion_zones: list[TextRange],
    ) -> None:
        """Handle frontmatter detection and zone creation.

        Frontmatter should only be detected at the beginning of the file.
        Subsequent '---' lines are treated as horizontal rules, not frontmatter.
        """
        if line.strip() == "---":
            # Only detect frontmatter if we're at line 1 and haven't processed any yet
            if (
                line_num == 1
                and frontmatter_state.start_line is None
                and not frontmatter_state.frontmatter_processed
            ):
                # Start frontmatter (only at the very beginning)
                frontmatter_state.start_line = line_num
                frontmatter_state.in_frontmatter = True
            elif frontmatter_state.in_frontmatter:
                # End frontmatter
                exclusion_zones.append(
                    TextRange(
                        start_line=frontmatter_state.start_line,
                        start_column=0,
                        end_line=line_num,
                        end_column=len(line),
                        zone_type="frontmatter",
                    )
                )
                frontmatter_state.start_line = None
                frontmatter_state.in_frontmatter = False
                frontmatter_state.frontmatter_processed = True
            # All other '---' lines are treated as horizontal rules, not frontmatter

    def _process_line_exclusions(
        self,
        line: str,
        line_num: int,
        patterns: dict[str, re.Pattern],
        exclusion_zones: list[TextRange],
    ) -> None:
        """Process line-level exclusion patterns."""
        # H1 headers
        if line.strip().startswith("# "):
            exclusion_zones.append(
                TextRange(
                    start_line=line_num,
                    start_column=0,
                    end_line=line_num,
                    end_column=len(line),
                    zone_type="h1_header",
                )
            )

        # Link Reference Definitions - use finditer to catch all LRDs in a line
        for match in patterns["link_ref"].finditer(line):
            exclusion_zones.append(
                TextRange(
                    start_line=line_num,
                    start_column=match.start(),
                    end_line=line_num,
                    end_column=match.end(),
                    zone_type="link_ref_def",
                )
            )

        # Table rows
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

        # Pattern-based exclusions
        pattern_types = [
            ("url", "url"),
            ("html_a_tag", "html_tag"),
            ("inline_code", "inline_code"),
            ("wiki", "wikilink"),
            ("regular_link", "regular_link"),
            ("template_var", "template_variable"),
            ("template_block", "template_variable"),
            ("template_asp", "template_variable"),
            ("template_asp_comment", "template_variable"),
        ]

        for pattern_key, zone_type in pattern_types:
            for match in patterns[pattern_key].finditer(line):
                exclusion_zones.append(
                    TextRange(
                        start_line=line_num,
                        start_column=match.start(),
                        end_line=line_num,
                        end_column=match.end(),
                        zone_type=zone_type,
                    )
                )

    def find_link_candidates(
        self,
        content: str,
        file_registry: dict[str, MarkdownFile],
        exclusion_zones: list[TextRange] | None = None,
        current_file_id: str | None = None,
    ) -> list[LinkCandidate]:
        """Find text that could be converted to WikiLinks with Japanese variations.

        Args:
            content: The markdown content to analyze
            file_registry: Dictionary mapping file IDs to MarkdownFile objects
            exclusion_zones: Areas to exclude from link detection
            current_file_id: The ID of the file being processed, to avoid self-linking

        Returns:
            List of LinkCandidate objects
        """
        if exclusion_zones is None:
            exclusion_zones = self.extract_exclusion_zones(content)

        candidates = []
        lines = content.split("\n")

        # Build enhanced lookup with Japanese variations
        enhanced_targets = self._build_enhanced_target_lookup(file_registry)

        # Track positions to avoid duplicates
        seen_positions = set()

        for line_num, line in enumerate(lines, 1):
            # Find potential matches for each target
            for target_info in enhanced_targets:
                # Avoid self-linking
                if current_file_id and target_info["file_id"] == current_file_id:
                    continue

                # Use word boundaries to find exact matches
                pattern = re.compile(
                    r"\b" + re.escape(target_info["text"]) + r"\b", re.IGNORECASE
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

                    # Create position key for deduplication
                    position_key = (
                        line_num,
                        match.start(),
                        match.end(),
                        target_info["file_id"],
                    )
                    if position_key in seen_positions:
                        continue
                    seen_positions.add(position_key)

                    # Determine the best alias to use
                    matched_text = match.group()
                    target_file = file_registry[target_info["file_id"]]
                    suggested_alias = self._determine_best_alias_with_japanese(
                        matched_text, target_file, target_info
                    )

                    candidate = LinkCandidate(
                        text=matched_text,
                        target_file_id=target_info["file_id"],
                        suggested_alias=suggested_alias,
                        position=position,
                        confidence=target_info.get("confidence", 1.0),
                        variation_type=target_info.get("source_type"),
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

    def _build_enhanced_target_lookup(
        self, file_registry: dict[str, MarkdownFile]
    ) -> list[dict[str, Any]]:
        """Build enhanced target lookup with Japanese variations and cross-language.

        Returns:
            List of target dictionaries with text, file_id, source_type, and confidence
        """
        enhanced_targets = []

        for file_id, file in file_registry.items():
            # Add title as target
            if file.frontmatter.title:
                enhanced_targets.append(
                    {
                        "text": file.frontmatter.title.lower(),
                        "file_id": file_id,
                        "source_type": "title",
                        "confidence": 1.0,
                        "original_text": file.frontmatter.title,
                    }
                )

                # Add Japanese variations of title if Japanese processing is enabled
                if self.japanese_enabled:
                    title_variations = (
                        self.tag_pattern_manager.find_japanese_variations(
                            file.frontmatter.title
                        )
                    )
                    for variation in title_variations:
                        if variation.lower() != file.frontmatter.title.lower():
                            enhanced_targets.append(
                                {
                                    "text": variation.lower(),
                                    "file_id": file_id,
                                    "source_type": "title_variation",
                                    "confidence": 0.9,
                                    "original_text": variation,
                                    "variation_of": file.frontmatter.title,
                                }
                            )

            # Add aliases as targets
            for alias in file.frontmatter.aliases:
                enhanced_targets.append(
                    {
                        "text": alias.lower(),
                        "file_id": file_id,
                        "source_type": "alias",
                        "confidence": 1.0,
                        "original_text": alias,
                    }
                )

                # Add Japanese variations of aliases
                if self.japanese_enabled:
                    alias_variations = (
                        self.tag_pattern_manager.find_japanese_variations(alias)
                    )
                    for variation in alias_variations:
                        if variation.lower() != alias.lower():
                            enhanced_targets.append(
                                {
                                    "text": variation.lower(),
                                    "file_id": file_id,
                                    "source_type": "alias_variation",
                                    "confidence": 0.9,
                                    "original_text": variation,
                                    "variation_of": alias,
                                }
                            )

        return enhanced_targets

    def _determine_best_alias_with_japanese(
        self,
        matched_text: str,
        target_file: MarkdownFile,  # noqa: ARG002
        target_info: dict[str, Any],  # noqa: ARG002
    ) -> str | None:
        """Determine the best alias to use for a WikiLink with Japanese variations.

        Always include alias for better readability and consistency.
        """
        # Always use the matched text as alias for better readability
        # This ensures that [[file_id|readable_text]] format is used consistently
        return matched_text

    def suggest_bidirectional_aliases(
        self, file_registry: dict[str, MarkdownFile]
    ) -> dict[str, list[str]]:
        """Suggest bidirectional aliases based on Japanese variations.

        Returns:
            Dictionary mapping file_id to list of suggested aliases
        """
        suggestions = {}

        if not self.japanese_enabled:
            return suggestions

        for file_id, file in file_registry.items():
            suggested_aliases = []

            # Check title for cross-language opportunities
            if file.frontmatter.title:
                title_variations = self.tag_pattern_manager.find_japanese_variations(
                    file.frontmatter.title
                )
                for variation in title_variations:
                    if (
                        variation not in file.frontmatter.aliases
                        and variation.lower() != file.frontmatter.title.lower()
                    ):
                        suggested_aliases.append(variation)

            # Check existing aliases for additional variations
            for alias in file.frontmatter.aliases:
                alias_variations = self.tag_pattern_manager.find_japanese_variations(
                    alias
                )
                for variation in alias_variations:
                    if (
                        variation not in file.frontmatter.aliases
                        and variation not in suggested_aliases
                        and variation.lower() != file.frontmatter.title.lower()
                    ):
                        suggested_aliases.append(variation)

            # Check content for English-Japanese matches
            content_matches = self._find_english_japanese_content_matches(file)
            for match in content_matches:
                if (
                    match not in file.frontmatter.aliases
                    and match not in suggested_aliases
                    and match.lower() != file.frontmatter.title.lower()
                ):
                    suggested_aliases.append(match)

            if suggested_aliases:
                suggestions[file_id] = suggested_aliases

        return suggestions

    def _find_english_japanese_content_matches(self, file: MarkdownFile) -> list[str]:
        """Find English-Japanese term matches in file content."""
        matches = []
        content = file.content

        # Process English-Japanese pairs
        english_japanese_matches = self._process_english_japanese_pairs(content)
        matches.extend(english_japanese_matches)

        # Process abbreviation expansions
        abbreviation_matches = self._process_abbreviation_expansions(content)
        matches.extend(abbreviation_matches)

        return list(set(matches))  # Remove duplicates

    def _process_english_japanese_pairs(self, content: str) -> list[str]:
        """Process English-Japanese pairs for content matches."""
        matches = []
        english_japanese_pairs = self.tag_pattern_manager.japanese_variations.get(
            "english_japanese_pairs", {}
        )

        for english, data in english_japanese_pairs.items():
            pair_matches = self._extract_pair_matches(english, data, content)
            matches.extend(pair_matches)

        return matches

    def _extract_pair_matches(self, english: str, data: Any, content: str) -> list[str]:
        """Extract matches for a single English-Japanese pair."""
        matches = []
        english_lower = english.lower()

        # Handle new YAML structure with japanese and aliases
        if isinstance(data, dict):
            japanese_terms = data.get("japanese", [])
            aliases = data.get("aliases", [])
            all_terms = japanese_terms + aliases
        else:
            # Fallback for old format
            all_terms = data if isinstance(data, list) else [data]

        # Check for English term in content
        if english_lower in content.lower():
            for term in japanese_terms if isinstance(data, dict) else all_terms:
                if isinstance(term, str):
                    matches.append(term)

        # Check for Japanese/alias terms in content
        for term in all_terms:
            if isinstance(term, str) and term in content:
                matches.append(english)

        return matches

    def _process_abbreviation_expansions(self, content: str) -> list[str]:
        """Process abbreviation expansions for content matches."""
        matches = []
        abbreviations = self.tag_pattern_manager.japanese_variations.get(
            "abbreviation_expansions", {}
        )

        for abbrev, expansion_data in abbreviations.items():
            if isinstance(expansion_data, dict):
                abbrev_matches = self._extract_abbreviation_matches(
                    abbrev, expansion_data, content
                )
                matches.extend(abbrev_matches)

        return matches

    def _extract_abbreviation_matches(
        self, abbrev: str, expansion_data: dict[str, Any], content: str
    ) -> list[str]:
        """Extract matches for a single abbreviation expansion."""
        matches = []
        full_form = expansion_data.get("full_form", "")
        english_form = expansion_data.get("english", "")
        variations = expansion_data.get("variations", [])

        # Check for abbreviation in content
        if abbrev.lower() in content.lower():
            if full_form:
                matches.append(full_form)
            if english_form:
                matches.append(english_form)

        # Check for variations in content
        for variation in variations:
            if variation.lower() in content.lower():
                if full_form:
                    matches.append(full_form)
                if english_form:
                    matches.append(english_form)

        return matches

    def analyze_japanese_linking_opportunities(
        self, files: list[MarkdownFile]
    ) -> dict[str, Any]:
        """Analyze Japanese linking opportunities across the vault.

        Returns:
            Analysis report with Japanese-specific linking statistics and opportunities
        """
        if not self.japanese_enabled:
            return {"error": "Japanese processing is not enabled"}

        analysis = {
            "total_files": len(files),
            "files_with_japanese_content": 0,
            "katakana_variation_opportunities": 0,
            "english_japanese_cross_references": 0,
            "bidirectional_alias_suggestions": 0,
            "mixed_language_files": 0,
            "technical_term_opportunities": 0,
        }

        # Build file registry for analysis
        file_registry = {
            file.frontmatter.id: file for file in files if file.frontmatter.id
        }

        # Analyze each file
        for file in files:
            content = file.content

            # Detect Japanese content
            japanese_chars = len(
                re.findall(r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]", content)
            )
            english_words = len(re.findall(r"\b[a-zA-Z]+\b", content))

            if japanese_chars > 0:
                analysis["files_with_japanese_content"] += 1

            if japanese_chars > 0 and english_words > 0:
                analysis["mixed_language_files"] += 1

            # Check for katakana variation opportunities
            katakana_matches = re.findall(r"[\u30A0-\u30FF]+", content)
            for katakana in katakana_matches:
                variations = self.tag_pattern_manager.find_japanese_variations(katakana)
                if len(variations) > 1:  # Has variations
                    analysis["katakana_variation_opportunities"] += 1

            # Check for English-Japanese cross-reference opportunities
            content_matches = self._find_english_japanese_content_matches(file)
            if content_matches:
                analysis["english_japanese_cross_references"] += len(content_matches)

            # Check for technical term opportunities
            english_japanese_pairs = self.tag_pattern_manager.japanese_variations.get(
                "english_japanese_pairs", {}
            )
            for english, _data in english_japanese_pairs.items():
                if english.lower() in content.lower():
                    analysis["technical_term_opportunities"] += 1

        # Get bidirectional alias suggestions
        alias_suggestions = self.suggest_bidirectional_aliases(file_registry)
        analysis["bidirectional_alias_suggestions"] = sum(
            len(suggestions) for suggestions in alias_suggestions.values()
        )

        # Calculate percentages
        if analysis["total_files"] > 0:
            analysis["japanese_content_percentage"] = (
                analysis["files_with_japanese_content"] / analysis["total_files"] * 100
            )
            analysis["mixed_language_percentage"] = (
                analysis["mixed_language_files"] / analysis["total_files"] * 100
            )

        return analysis

    def detect_orphaned_notes(self, files: list[MarkdownFile]) -> list[OrphanedNote]:
        """Detect orphaned notes and suggest connections.

        Args:
            files: List of MarkdownFile objects to analyze

        Returns:
            List of OrphanedNote objects with connection suggestions
        """
        # Build file registry for analysis
        file_registry = {
            file.frontmatter.id: file for file in files if file.frontmatter.id
        }

        # Build link graph to identify incoming/outgoing links
        link_graph = self._build_link_graph(files, file_registry)

        orphaned_notes = []

        for file in files:
            file_id = file.frontmatter.id
            if not file_id:
                continue

            # Count incoming and outgoing links
            incoming_count = len(link_graph.get("incoming", {}).get(file_id, []))
            outgoing_count = len(link_graph.get("outgoing", {}).get(file_id, []))

            # Calculate isolation score (higher = more isolated)
            isolation_score = self._calculate_isolation_score(
                incoming_count, outgoing_count, len(files)
            )

            # Consider a note orphaned if it has very few connections
            # and high isolation score
            is_orphaned = (
                (incoming_count + outgoing_count) <= 1 and isolation_score >= 0.7
            ) or (incoming_count == 0 and outgoing_count == 0)

            if is_orphaned:
                # Generate connection suggestions
                connection_suggestions = self._suggest_connections(
                    file, files, file_registry, link_graph
                )

                orphaned_note = OrphanedNote(
                    file_path=str(file.path),
                    file_id=file_id,
                    title=file.frontmatter.title,
                    tags=file.frontmatter.tags or [],
                    incoming_links=incoming_count,
                    outgoing_links=outgoing_count,
                    connection_suggestions=connection_suggestions,
                    isolation_score=isolation_score,
                )
                orphaned_notes.append(orphaned_note)

        # Sort by isolation score (most isolated first)
        orphaned_notes.sort(key=lambda x: x.isolation_score, reverse=True)

        return orphaned_notes

    def _build_link_graph(
        self, files: list[MarkdownFile], file_registry: dict[str, MarkdownFile]
    ) -> dict[str, dict[str, list[str]]]:
        """Build a graph of incoming and outgoing links between files."""
        link_graph = {"incoming": {}, "outgoing": {}}

        # Initialize all files in the graph
        for file in files:
            if file.frontmatter.id:
                link_graph["incoming"][file.frontmatter.id] = []
                link_graph["outgoing"][file.frontmatter.id] = []

        # Process WikiLinks to build the graph
        for file in files:
            source_id = file.frontmatter.id
            if not source_id:
                continue

            for wiki_link in file.wiki_links:
                target_id = wiki_link.target_id
                if target_id in file_registry:
                    # Add outgoing link from source
                    link_graph["outgoing"][source_id].append(target_id)
                    # Add incoming link to target
                    link_graph["incoming"][target_id].append(source_id)

        return link_graph

    def _calculate_isolation_score(
        self, incoming_count: int, outgoing_count: int, total_files: int
    ) -> float:
        """Calculate isolation score for a note.

        Args:
            incoming_count: Number of incoming links
            outgoing_count: Number of outgoing links
            total_files: Total number of files in the vault

        Returns:
            Isolation score from 0.0 (well-connected) to 1.0 (completely isolated)
        """
        total_connections = incoming_count + outgoing_count

        if total_connections == 0:
            return 1.0  # Completely isolated

        # Calculate expected connections based on vault size
        # Larger vaults should have more connections per note
        expected_connections = max(2, total_files * 0.05)  # 5% of vault size, min 2

        # Normalize the connection count
        connection_ratio = min(1.0, total_connections / expected_connections)

        # Isolation score is inverse of connection ratio
        return 1.0 - connection_ratio

    def _suggest_connections(
        self,
        orphaned_file: MarkdownFile,
        all_files: list[MarkdownFile],
        file_registry: dict[str, MarkdownFile],  # noqa: ARG002
        link_graph: dict[str, dict[str, list[str]]],
    ) -> list[ConnectionSuggestion]:
        """Suggest connections for an orphaned note.

        Args:
            orphaned_file: The orphaned file to find connections for
            all_files: All files in the vault
            file_registry: Registry of files by ID
            link_graph: Graph of existing links

        Returns:
            List of ConnectionSuggestion objects
        """
        suggestions = []
        orphaned_id = orphaned_file.frontmatter.id

        if not orphaned_id:
            return suggestions

        # Get existing connections to avoid suggesting duplicates
        existing_outgoing = set(link_graph["outgoing"].get(orphaned_id, []))

        for candidate_file in all_files:
            candidate_id = candidate_file.frontmatter.id
            if not candidate_id or candidate_id == orphaned_id:
                continue

            # Skip if already connected
            if candidate_id in existing_outgoing:
                continue

            # Check for tag similarity
            tag_suggestion = self._check_tag_similarity(orphaned_file, candidate_file)
            if tag_suggestion:
                suggestions.append(tag_suggestion)

            # Check for keyword matches in content
            keyword_suggestion = self._check_keyword_similarity(
                orphaned_file, candidate_file
            )
            if keyword_suggestion:
                suggestions.append(keyword_suggestion)

            # Check for title/alias matches
            title_suggestion = self._check_title_similarity(
                orphaned_file, candidate_file
            )
            if title_suggestion:
                suggestions.append(title_suggestion)

        # Sort by confidence and limit to top suggestions
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        return suggestions[:5]  # Limit to top 5 suggestions

    def _check_tag_similarity(
        self, orphaned_file: MarkdownFile, candidate_file: MarkdownFile
    ) -> ConnectionSuggestion | None:
        """Check for tag-based similarity between files."""
        orphaned_tags = set(orphaned_file.frontmatter.tags or [])
        candidate_tags = set(candidate_file.frontmatter.tags or [])

        if not orphaned_tags or not candidate_tags:
            return None

        # Calculate tag overlap
        common_tags = orphaned_tags.intersection(candidate_tags)
        if not common_tags:
            return None

        # Calculate confidence based on tag overlap
        total_unique_tags = len(orphaned_tags.union(candidate_tags))
        confidence = (
            len(common_tags) / total_unique_tags if total_unique_tags > 0 else 0
        )

        # Only suggest if confidence is reasonable
        if confidence < 0.3:
            return None

        return ConnectionSuggestion(
            target_file_id=candidate_file.frontmatter.id or "",
            target_title=candidate_file.frontmatter.title,
            connection_type="tag_similarity",
            confidence=confidence,
            reason=(
                f"Shares {len(common_tags)} tag(s): {', '.join(sorted(common_tags))}"
            ),
            suggested_link_text=candidate_file.frontmatter.title,
        )

    def _check_keyword_similarity(
        self, orphaned_file: MarkdownFile, candidate_file: MarkdownFile
    ) -> ConnectionSuggestion | None:
        """Check for keyword-based similarity between file contents."""
        # Extract keywords from both files
        orphaned_keywords = self._extract_keywords(orphaned_file.content)
        candidate_keywords = self._extract_keywords(candidate_file.content)

        if not orphaned_keywords or not candidate_keywords:
            return None

        # Find common keywords
        common_keywords = orphaned_keywords.intersection(candidate_keywords)
        if len(common_keywords) < 2:  # Require at least 2 common keywords
            return None

        # Calculate confidence based on keyword overlap
        total_unique_keywords = len(orphaned_keywords.union(candidate_keywords))
        confidence = (
            len(common_keywords) / total_unique_keywords
            if total_unique_keywords > 0
            else 0
        )

        # Boost confidence for technical terms and proper nouns
        technical_keywords = {
            kw for kw in common_keywords if len(kw) > 4 and kw[0].isupper()
        }
        if technical_keywords:
            confidence = min(1.0, confidence * 1.2)

        # Only suggest if confidence is reasonable
        if confidence < 0.2:
            return None

        return ConnectionSuggestion(
            target_file_id=candidate_file.frontmatter.id or "",
            target_title=candidate_file.frontmatter.title,
            connection_type="keyword_match",
            confidence=confidence,
            reason=(
                f"Shares {len(common_keywords)} keyword(s): "
                f"{', '.join(sorted(list(common_keywords)[:3]))}"
            ),
            suggested_link_text=candidate_file.frontmatter.title,
        )

    def _check_title_similarity(
        self, orphaned_file: MarkdownFile, candidate_file: MarkdownFile
    ) -> ConnectionSuggestion | None:
        """Check for title/alias similarity between files."""
        orphaned_title = orphaned_file.frontmatter.title
        candidate_title = candidate_file.frontmatter.title

        if not orphaned_title or not candidate_title:
            return None

        # Check if orphaned file's title appears in candidate's content
        candidate_content_lower = candidate_file.content.lower()
        orphaned_title_lower = orphaned_title.lower()

        # Look for title mentions in content
        if orphaned_title_lower in candidate_content_lower:
            # Calculate confidence based on how prominently the title appears
            title_mentions = candidate_content_lower.count(orphaned_title_lower)
            content_length = len(candidate_content_lower.split())
            mention_density = (
                title_mentions / content_length if content_length > 0 else 0
            )

            confidence = min(0.8, mention_density * 100)  # Scale and cap at 0.8

            if confidence > 0.1:
                return ConnectionSuggestion(
                    target_file_id=candidate_file.frontmatter.id or "",
                    target_title=candidate_file.frontmatter.title,
                    connection_type="content_similarity",
                    confidence=confidence,
                    reason=(
                        f"'{orphaned_title}' mentioned {title_mentions} "
                        f"time(s) in content"
                    ),
                    suggested_link_text=orphaned_title,
                )

        # Check if candidate's title appears in orphaned file's content
        orphaned_content_lower = orphaned_file.content.lower()
        candidate_title_lower = candidate_title.lower()

        if candidate_title_lower in orphaned_content_lower:
            title_mentions = orphaned_content_lower.count(candidate_title_lower)
            content_length = len(orphaned_content_lower.split())
            mention_density = (
                title_mentions / content_length if content_length > 0 else 0
            )

            confidence = min(0.8, mention_density * 100)

            if confidence > 0.1:
                return ConnectionSuggestion(
                    target_file_id=candidate_file.frontmatter.id or "",
                    target_title=candidate_file.frontmatter.title,
                    connection_type="content_similarity",
                    confidence=confidence,
                    reason=(
                        f"'{candidate_title}' mentioned {title_mentions} "
                        f"time(s) in orphaned file"
                    ),
                    suggested_link_text=candidate_title,
                )

        return None

    def _extract_keywords(self, content: str) -> set[str]:
        """Extract meaningful keywords from content using configurable extraction.

        Args:
            content: The content to extract keywords from

        Returns:
            Set of keywords found in the content
        """
        return self.keyword_manager.extract_keywords(content)

    def generate_auto_link_suggestions(
        self, orphaned_notes: list[OrphanedNote]
    ) -> dict[str, list[dict[str, Any]]]:
        """Generate automatic WikiLink creation suggestions for orphaned notes.

        Args:
            orphaned_notes: List of orphaned notes with connection suggestions

        Returns:
            Dictionary mapping file_id to list of auto-link suggestions
        """
        auto_link_suggestions = {}

        for orphaned_note in orphaned_notes:
            suggestions = []

            # Convert high-confidence connection suggestions to auto-link suggestions
            for connection in orphaned_note.connection_suggestions:
                if connection.confidence >= 0.6:  # High confidence threshold
                    suggestion = {
                        "target_file_id": connection.target_file_id,
                        "suggested_text": connection.suggested_link_text
                        or connection.target_title,
                        "confidence": connection.confidence,
                        "reason": connection.reason,
                        "connection_type": connection.connection_type,
                        "auto_link_format": self._format_auto_link(
                            connection.target_file_id,
                            connection.suggested_link_text or connection.target_title,
                        ),
                    }
                    suggestions.append(suggestion)

            if suggestions:
                auto_link_suggestions[orphaned_note.file_id] = suggestions

        return auto_link_suggestions

    def _format_auto_link(self, target_file_id: str, link_text: str) -> str:
        """Format an auto-link in WikiLink format.

        Args:
            target_file_id: The target file ID
            link_text: The text to display for the link

        Returns:
            Formatted WikiLink string
        """
        return f"[[{target_file_id}|{link_text}]]"

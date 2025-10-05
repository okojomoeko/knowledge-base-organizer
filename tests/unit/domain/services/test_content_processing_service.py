"""Tests for ContentProcessingService."""

import pytest

from knowledge_base_organizer.domain.models import (
    Frontmatter,
    MarkdownFile,
    TextPosition,
)
from knowledge_base_organizer.domain.services.content_processing_service import (
    ContentProcessingService,
    LinkCandidate,
)
from knowledge_base_organizer.domain.services.link_analysis_service import TextRange


class TestContentProcessingService:
    """Test cases for ContentProcessingService."""

    @pytest.fixture
    def service(self):
        """Create a ContentProcessingService instance."""
        return ContentProcessingService(max_links_per_file=10)

    @pytest.fixture
    def sample_files(self, tmp_path):
        """Create sample markdown files for testing."""
        files = {}

        # Create actual files to satisfy validation
        file1_path = tmp_path / "20230101120000.md"
        file1_path.write_text("# Interface Design\n\nThis is about interface design.")

        file2_path = tmp_path / "20230101130000.md"
        file2_path.write_text("# Database Schema\n\nThis covers database design.")

        # File 1: Interface Design
        file1 = MarkdownFile(
            path=file1_path,
            file_id="20230101120000",
            frontmatter=Frontmatter(
                title="Interface Design",
                aliases=["UI Design", "User Interface"],
                id="20230101120000",
            ),
            content="# Interface Design\n\nThis is about interface design.",
        )
        files["20230101120000"] = file1

        # File 2: Database Schema
        file2 = MarkdownFile(
            path=file2_path,
            file_id="20230101130000",
            frontmatter=Frontmatter(
                title="Database Schema",
                aliases=["DB Schema"],
                id="20230101130000",
            ),
            content="# Database Schema\n\nThis covers database design.",
        )
        files["20230101130000"] = file2

        return files

    def test_find_link_candidates_exact_title_match(self, service, sample_files):
        """Test finding link candidates with exact title matches."""
        content = """# My Document

This document discusses Interface Design and how it relates to
the overall system architecture.
"""

        candidates = service.find_link_candidates(content, sample_files)

        assert len(candidates) == 1
        candidate = candidates[0]
        assert candidate.text == "Interface Design"
        assert candidate.target_file_id == "20230101120000"
        assert candidate.suggested_alias is None  # Exact title match
        assert candidate.position.line_number == 3
        assert candidate.position.column_start == 24

    def test_find_link_candidates_alias_match(self, service, sample_files):
        """Test finding link candidates with alias matches."""
        content = """# My Document

We need to work on UI Design for the application.
"""

        candidates = service.find_link_candidates(content, sample_files)

        assert len(candidates) == 1
        candidate = candidates[0]
        assert candidate.text == "UI Design"
        assert candidate.target_file_id == "20230101120000"
        assert candidate.suggested_alias == "UI Design"
        assert candidate.position.line_number == 3

    def test_find_link_candidates_multiple_matches(self, service, sample_files):
        """Test finding multiple link candidates in content."""
        content = """# My Document

The Interface Design should work well with the Database Schema.
Both UI Design and DB Schema are important components.
"""

        candidates = service.find_link_candidates(content, sample_files)

        assert len(candidates) == 4

        # Check that candidates are sorted by position
        assert candidates[0].text == "Interface Design"
        assert candidates[1].text == "Database Schema"
        assert candidates[2].text == "UI Design"
        assert candidates[3].text == "DB Schema"

    def test_find_link_candidates_excludes_frontmatter(self, service, sample_files):
        """Test that frontmatter is excluded from link detection."""
        content = """---
title: Interface Design
tags: [UI Design, Database Schema]
---

# My Document

This discusses Interface Design concepts.
"""

        candidates = service.find_link_candidates(content, sample_files)

        # Should only find the one in the body, not in frontmatter
        assert len(candidates) == 1
        assert candidates[0].position.line_number == 8

    def test_find_link_candidates_excludes_existing_wikilinks(
        self, service, sample_files
    ):
        """Test that existing WikiLinks are excluded."""
        content = """# My Document

This discusses [[20230101120000|Interface Design]] and how it works.
We also need to consider UI Design for the project.
"""

        candidates = service.find_link_candidates(content, sample_files)

        # Should only find "UI Design", not "Interface Design" in the WikiLink
        assert len(candidates) == 1
        assert candidates[0].text == "UI Design"

    def test_find_link_candidates_excludes_regular_links(self, service, sample_files):
        """Test that regular markdown links are excluded."""
        content = """# My Document

Check out this [Interface Design](https://example.com) resource.
We also need to work on UI Design.
"""

        candidates = service.find_link_candidates(content, sample_files)

        # Should only find "UI Design", not "Interface Design" in the regular link
        assert len(candidates) == 1
        assert candidates[0].text == "UI Design"

    def test_find_link_candidates_excludes_template_variables(
        self, service, sample_files
    ):
        """Test that template variables are excluded."""
        content = """# My Document

Template: {{Interface Design}} and <% UI Design %>
But we do need to discuss Interface Design in general.
"""

        candidates = service.find_link_candidates(content, sample_files)

        # Should only find the one outside template variables
        assert len(candidates) == 1
        assert candidates[0].position.line_number == 4

    def test_resolve_conflicts_overlapping_candidates(self, service):
        """Test conflict resolution for overlapping candidates."""
        # Create overlapping candidates
        candidates = [
            LinkCandidate(
                text="Design",
                target_file_id="file1",
                suggested_alias="Design",
                position=TextPosition(line_number=1, column_start=10, column_end=16),
            ),
            LinkCandidate(
                text="Interface Design",
                target_file_id="file2",
                suggested_alias=None,
                position=TextPosition(line_number=1, column_start=0, column_end=16),
            ),
        ]

        conflicts = service.resolve_conflicts(candidates)

        assert len(conflicts) == 1
        conflict = conflicts[0]
        assert len(conflict.conflicting_candidates) == 2
        # Longer text should win
        assert conflict.resolved_candidate.text == "Interface Design"

    def test_apply_link_replacements_basic(self, service):
        """Test basic link replacement functionality."""
        content = """# My Document

This discusses Interface Design concepts.
"""

        candidates = [
            LinkCandidate(
                text="Interface Design",
                target_file_id="20230101120000",
                suggested_alias=None,
                position=TextPosition(line_number=3, column_start=15, column_end=31),
            )
        ]

        result = service.apply_link_replacements(content, candidates)

        expected_content = """# My Document

This discusses [[20230101120000]] concepts.
"""

        assert result.processed_content == expected_content
        assert len(result.applied_replacements) == 1
        assert result.applied_replacements[0].replacement_text == "[[20230101120000]]"

    def test_apply_link_replacements_with_alias(self, service):
        """Test link replacement with alias."""
        content = """# My Document

We need better UI Design.
"""

        candidates = [
            LinkCandidate(
                text="UI Design",
                target_file_id="20230101120000",
                suggested_alias="UI Design",
                position=TextPosition(line_number=3, column_start=15, column_end=24),
            )
        ]

        result = service.apply_link_replacements(content, candidates)

        expected_content = """# My Document

We need better [[20230101120000|UI Design]].
"""

        assert result.processed_content == expected_content
        assert (
            result.applied_replacements[0].replacement_text
            == "[[20230101120000|UI Design]]"
        )

    def test_apply_link_replacements_multiple_on_same_line(self, service):
        """Test multiple replacements on the same line."""
        content = """# My Document

Interface Design and Database Schema are both important.
"""

        candidates = [
            LinkCandidate(
                text="Interface Design",
                target_file_id="file1",
                suggested_alias=None,
                position=TextPosition(line_number=3, column_start=0, column_end=16),
            ),
            LinkCandidate(
                text="Database Schema",
                target_file_id="file2",
                suggested_alias=None,
                position=TextPosition(line_number=3, column_start=21, column_end=36),
            ),
        ]

        result = service.apply_link_replacements(content, candidates)

        expected_content = """# My Document

[[file1]] and [[file2]] are both important.
"""

        assert result.processed_content == expected_content
        assert len(result.applied_replacements) == 2

    def test_apply_link_replacements_respects_max_links(self, service):
        """Test that max_links_per_file is respected."""
        service.max_links_per_file = 2

        content = """# My Document

Interface Design, Database Schema, and UI Design are important.
"""

        candidates = [
            LinkCandidate(
                text="Interface Design",
                target_file_id="file1",
                suggested_alias=None,
                position=TextPosition(line_number=3, column_start=0, column_end=16),
            ),
            LinkCandidate(
                text="Database Schema",
                target_file_id="file2",
                suggested_alias=None,
                position=TextPosition(line_number=3, column_start=18, column_end=33),
            ),
            LinkCandidate(
                text="UI Design",
                target_file_id="file3",
                suggested_alias=None,
                position=TextPosition(line_number=3, column_start=39, column_end=48),
            ),
        ]

        result = service.apply_link_replacements(content, candidates)

        # Should only apply first 2 replacements
        assert len(result.applied_replacements) == 2
        assert len(result.skipped_candidates) == 1

    def test_extract_exclusion_zones_frontmatter(self, service):
        """Test extraction of frontmatter exclusion zones."""
        content = """---
title: Test
tags: [Interface Design]
---

# Content

Interface Design is important.
"""

        zones = service._extract_exclusion_zones(content)

        frontmatter_zones = [z for z in zones if z.zone_type == "frontmatter"]
        assert len(frontmatter_zones) == 1
        assert frontmatter_zones[0].start_line == 1
        assert frontmatter_zones[0].end_line == 4

    def test_extract_exclusion_zones_wikilinks(self, service):
        """Test extraction of WikiLink exclusion zones."""
        content = """# Content

This mentions [[20230101120000|Interface Design]] in a link.
"""

        zones = service._extract_exclusion_zones(content)

        wikilink_zones = [z for z in zones if z.zone_type == "wikilink"]
        assert len(wikilink_zones) == 1
        assert wikilink_zones[0].start_line == 3
        assert wikilink_zones[0].start_column == 14
        assert wikilink_zones[0].end_column == 49

    def test_extract_exclusion_zones_regular_links(self, service):
        """Test extraction of regular link exclusion zones."""
        content = """# Content

Check [Interface Design](https://example.com) for details.
"""

        zones = service._extract_exclusion_zones(content)

        regular_link_zones = [z for z in zones if z.zone_type == "regular_link"]
        assert len(regular_link_zones) == 1
        assert regular_link_zones[0].start_line == 3

    def test_extract_exclusion_zones_template_variables(self, service):
        """Test extraction of template variable exclusion zones."""
        content = """# Content

Template: {{Interface Design}} and <% UI Design %>
Also: ${Database Schema} variable.
"""

        zones = service._extract_exclusion_zones(content)

        template_zones = [z for z in zones if z.zone_type == "template_variable"]
        assert len(template_zones) == 3

    def test_is_in_exclusion_zone(self, service):
        """Test position checking against exclusion zones."""
        zones = [
            TextRange(
                start_line=1,
                start_column=10,
                end_line=1,
                end_column=20,
                zone_type="test",
            )
        ]

        # Position inside zone
        pos_inside = TextPosition(line_number=1, column_start=15, column_end=18)
        assert service._is_in_exclusion_zone(pos_inside, zones)

        # Position outside zone
        pos_outside = TextPosition(line_number=1, column_start=25, column_end=30)
        assert not service._is_in_exclusion_zone(pos_outside, zones)

        # Position on different line
        pos_different_line = TextPosition(line_number=2, column_start=15, column_end=18)
        assert not service._is_in_exclusion_zone(pos_different_line, zones)

    def test_determine_best_alias_exact_title(self, service, sample_files):
        """Test alias determination for exact title matches."""
        file = sample_files["20230101120000"]
        alias = service._determine_best_alias("Interface Design", file)
        assert alias is None  # No alias needed for exact title match

    def test_determine_best_alias_alias_match(self, service, sample_files):
        """Test alias determination for alias matches."""
        file = sample_files["20230101120000"]
        alias = service._determine_best_alias("UI Design", file)
        assert alias == "UI Design"

    def test_determine_best_alias_other_text(self, service, sample_files):
        """Test alias determination for other text."""
        file = sample_files["20230101120000"]
        alias = service._determine_best_alias("Some Other Text", file)
        assert alias == "Some Other Text"

    def test_ranges_overlap(self, service):
        """Test range overlap detection."""
        range1 = (1, 10, 20)  # line 1, columns 10-20
        range2 = (1, 15, 25)  # line 1, columns 15-25
        range3 = (1, 25, 35)  # line 1, columns 25-35
        range4 = (2, 10, 20)  # line 2, columns 10-20

        assert service._ranges_overlap(range1, range2)  # Overlapping
        assert not service._ranges_overlap(range1, range3)  # Adjacent, no overlap
        assert not service._ranges_overlap(range1, range4)  # Different lines

    def test_calculate_candidate_priority(self, service):
        """Test candidate priority calculation."""
        candidate1 = LinkCandidate(
            text="Short",
            target_file_id="file1",
            suggested_alias="Short",
            position=TextPosition(line_number=1, column_start=0, column_end=5),
            confidence=0.8,
        )

        candidate2 = LinkCandidate(
            text="Much Longer Text",
            target_file_id="file2",
            suggested_alias=None,  # Exact title match
            position=TextPosition(line_number=1, column_start=0, column_end=16),
            confidence=0.9,
        )

        priority1 = service._calculate_candidate_priority(candidate1)
        priority2 = service._calculate_candidate_priority(candidate2)

        # Longer text with exact title match should have higher priority
        assert priority2 > priority1

    def test_create_wikilink_text(self, service):
        """Test WikiLink text creation."""
        # Without alias
        candidate1 = LinkCandidate(
            text="Interface Design",
            target_file_id="20230101120000",
            suggested_alias=None,
            position=TextPosition(line_number=1, column_start=0, column_end=16),
        )

        link_text1 = service._create_wikilink_text(candidate1)
        assert link_text1 == "[[20230101120000]]"

        # With alias
        candidate2 = LinkCandidate(
            text="UI Design",
            target_file_id="20230101120000",
            suggested_alias="UI Design",
            position=TextPosition(line_number=1, column_start=0, column_end=9),
        )

        link_text2 = service._create_wikilink_text(candidate2)
        assert link_text2 == "[[20230101120000|UI Design]]"

    def test_word_boundary_matching(self, service, sample_files):
        """Test that word boundaries are respected in matching."""
        content = """# My Document

The word "design" appears in Interface Design but not in "designed".
"""

        candidates = service.find_link_candidates(content, sample_files)

        # Should find "Interface Design" but not "design" or "designed"
        assert len(candidates) == 1
        assert candidates[0].text == "Interface Design"

    def test_case_insensitive_matching(self, service, sample_files):
        """Test case-insensitive matching."""
        content = """# My Document

We need better interface design and INTERFACE DESIGN.
"""

        candidates = service.find_link_candidates(content, sample_files)

        # Should find both matches despite different cases
        assert len(candidates) == 2
        assert all(c.target_file_id == "20230101120000" for c in candidates)

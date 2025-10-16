"""Tests for LinkAnalysisService."""

from pathlib import Path

import pytest

from knowledge_base_organizer.domain.models import (
    Frontmatter,
    LinkRefDef,
    MarkdownFile,
    RegularLink,
    WikiLink,
)
from knowledge_base_organizer.domain.services.link_analysis_service import (
    LinkAnalysisService,
    TextPosition,
    TextRange,
)


class TestLinkAnalysisService:
    """Test cases for LinkAnalysisService."""

    @pytest.fixture
    def service(self):
        """Create a LinkAnalysisService instance."""
        return LinkAnalysisService()

    @pytest.fixture
    def service_exclude_tables(self):
        """Create a LinkAnalysisService instance that excludes tables."""
        return LinkAnalysisService(exclude_tables=True)

    @pytest.fixture
    def sample_content(self):
        """Sample markdown content for testing."""
        return """---
title: Test File
tags: [test]
---

# Test Content

This is a [[20230101120000|test link]] and a [regular link](https://example.com).

Here's a Link Reference Definition:
[test-id|Test Alias]: /path/to/file "Test Title"

| Table | Content |
|-------|---------|
| Cell  | Data    |

Some plain text that mentions Interface Design and Database Management.
"""

    @pytest.fixture
    def file_registry(self):
        """Sample file registry for testing."""
        file1 = MarkdownFile(
            path=Path("test.md"),  # Use the special test path that's allowed
            file_id="20230101120000",
            frontmatter=Frontmatter(
                title="Interface Design",
                aliases=["UI Design", "User Interface"],
                id="20230101120000",
            ),
            content="# Interface Design\n\nContent about interfaces.",
        )

        file2 = MarkdownFile(
            path=Path("test.md"),  # Use the special test path that's allowed
            file_id="20230101120001",
            frontmatter=Frontmatter(
                title="Database Management",
                aliases=["DB Management"],
                id="20230101120001",
            ),
            content="# Database Management\n\nContent about databases.",
        )

        return {
            "20230101120000": file1,
            "20230101120001": file2,
        }

    def test_extract_exclusion_zones_frontmatter(self, service, sample_content):
        """Test extraction of frontmatter exclusion zones."""
        zones = service.extract_exclusion_zones(sample_content)

        # Find frontmatter zone
        frontmatter_zones = [z for z in zones if z.zone_type == "frontmatter"]
        assert len(frontmatter_zones) == 1

        zone = frontmatter_zones[0]
        assert zone.start_line == 1
        assert zone.end_line == 4  # Includes the closing ---

    def test_extract_exclusion_zones_wikilinks(self, service, sample_content):
        """Test extraction of WikiLink exclusion zones."""
        zones = service.extract_exclusion_zones(sample_content)

        # Find WikiLink zones
        wikilink_zones = [z for z in zones if z.zone_type == "wikilink"]
        assert len(wikilink_zones) == 1

        zone = wikilink_zones[0]
        assert zone.start_line == 8  # Line with the WikiLink
        assert zone.zone_type == "wikilink"

    def test_extract_exclusion_zones_regular_links(self, service, sample_content):
        """Test extraction of regular link exclusion zones."""
        zones = service.extract_exclusion_zones(sample_content)

        # Find regular link zones
        regular_zones = [z for z in zones if z.zone_type == "regular_link"]
        assert len(regular_zones) == 1

        zone = regular_zones[0]
        assert zone.start_line == 8  # Line with the regular link
        assert zone.zone_type == "regular_link"

    def test_extract_exclusion_zones_link_ref_def(self, service, sample_content):
        """Test extraction of Link Reference Definition exclusion zones."""
        zones = service.extract_exclusion_zones(sample_content)

        # Find Link Reference Definition zones
        link_ref_zones = [z for z in zones if z.zone_type == "link_ref_def"]
        assert len(link_ref_zones) == 1

        zone = link_ref_zones[0]
        assert zone.start_line == 11  # Line with the Link Reference Definition
        assert zone.zone_type == "link_ref_def"

    def test_extract_exclusion_zones_tables(
        self, service_exclude_tables, sample_content
    ):
        """Test extraction of table exclusion zones when enabled."""
        zones = service_exclude_tables.extract_exclusion_zones(sample_content)

        # Find table zones
        table_zones = [z for z in zones if z.zone_type == "table"]
        assert len(table_zones) == 3  # Header, separator, and data row

    def test_extract_exclusion_zones_no_tables(self, service, sample_content):
        """Test that tables are not excluded by default."""
        zones = service.extract_exclusion_zones(sample_content)

        # Should not find table zones
        table_zones = [z for z in zones if z.zone_type == "table"]
        assert len(table_zones) == 0

    def test_find_link_candidates(self, service, file_registry):
        """Test finding link candidates in content."""
        content = """# Test Content

This document discusses Interface Design and Database Management.
It also mentions UI Design and DB Management.
"""

        candidates = service.find_link_candidates(content, file_registry)

        # Should find candidates for both titles and aliases
        assert len(candidates) >= 4

        # Check that we found the expected targets
        target_ids = {c.target_file_id for c in candidates}
        assert "20230101120000" in target_ids  # Interface Design file
        assert "20230101120001" in target_ids  # Database Management file

    def test_find_link_candidates_respects_exclusion_zones(
        self, service, file_registry
    ):
        """Test that link candidates respect exclusion zones."""
        content = """---
title: Interface Design  # This should be excluded
---

# Test Content

This document discusses Interface Design.  # This should be found
"""

        candidates = service.find_link_candidates(content, file_registry)

        # Should only find one candidate (not the one in frontmatter)
        interface_candidates = [
            c for c in candidates if c.target_file_id == "20230101120000"
        ]
        assert len(interface_candidates) == 1
        assert interface_candidates[0].position.line_number > 5  # Not in frontmatter

    def test_detect_dead_links(self, service):
        """Test detection of dead links."""
        # Create a file with dead links
        file_with_dead_links = MarkdownFile(
            path=Path("test.md"),
            file_id="20230101120000",
            frontmatter=Frontmatter(title="Test File"),
            content="# Test",
            wiki_links=[
                WikiLink(
                    target_id="nonexistent",
                    line_number=1,
                    column_start=0,
                    column_end=10,
                )
            ],
            regular_links=[RegularLink(text="empty link", url="", line_number=2)],
            link_reference_definitions=[
                LinkRefDef(
                    id="test",
                    alias="Test",
                    path="",
                    title="Test",
                    line_number=3,
                )
            ],
        )

        dead_links = service.detect_dead_links([file_with_dead_links], {})

        assert len(dead_links) == 3  # One of each type

        # Check WikiLink dead link
        wiki_dead = next(dl for dl in dead_links if dl.link_type == "wikilink")
        assert wiki_dead.target == "nonexistent"
        assert wiki_dead.line_number == 1

        # Check regular link dead link
        regular_dead = next(dl for dl in dead_links if dl.link_type == "regular_link")
        assert not regular_dead.target
        assert regular_dead.line_number == 2

        # Check Link Reference Definition dead link
        link_ref_dead = next(dl for dl in dead_links if dl.link_type == "link_ref_def")
        assert not link_ref_dead.target
        assert link_ref_dead.line_number == 3

    def test_calculate_link_density(self, service):
        """Test calculation of link density metrics."""
        file = MarkdownFile(
            path=Path("test.md"),
            file_id="20230101120000",
            frontmatter=Frontmatter(title="Test File"),
            content="""---
title: Test File
---

# Test Content

This is a test file with some content. It has multiple words.
There are [[link1]] and [[link2|alias]] WikiLinks.
Also a [regular link](https://example.com).
And a Link Reference Definition below.

[ref|Reference]: /path/to/file "Title"
""",
            wiki_links=[
                WikiLink(
                    target_id="link1", line_number=8, column_start=10, column_end=19
                ),
                WikiLink(
                    target_id="link2",
                    alias="alias",
                    line_number=8,
                    column_start=24,
                    column_end=39,
                ),
            ],
            regular_links=[
                RegularLink(
                    text="regular link", url="https://example.com", line_number=9
                )
            ],
            link_reference_definitions=[
                LinkRefDef(
                    id="ref",
                    alias="Reference",
                    path="/path/to/file",
                    title="Title",
                    line_number=12,
                )
            ],
        )

        metrics = service.calculate_link_density(file)

        assert metrics.total_links == 4  # 2 wiki + 1 regular + 1 ref def
        assert metrics.wiki_links == 2
        assert metrics.regular_links == 1
        assert metrics.link_ref_defs == 1
        assert metrics.unique_targets == 4  # All different targets
        assert metrics.total_words > 0
        assert metrics.link_density > 0

    def test_is_in_exclusion_zone(self, service):
        """Test checking if a position is in an exclusion zone."""
        zones = [
            TextRange(
                start_line=1,
                start_column=0,
                end_line=1,
                end_column=10,
                zone_type="test",
            )
        ]

        # Position inside zone
        pos_inside = TextPosition(line_number=1, column_start=5, column_end=8)
        assert service._is_in_exclusion_zone(pos_inside, zones)

        # Position outside zone
        pos_outside = TextPosition(line_number=1, column_start=15, column_end=20)
        assert not service._is_in_exclusion_zone(pos_outside, zones)

        # Position on different line
        pos_different_line = TextPosition(line_number=2, column_start=5, column_end=8)
        assert not service._is_in_exclusion_zone(pos_different_line, zones)

    def test_determine_best_alias(self, service, file_registry):
        """Test determining the best alias for a WikiLink."""
        file = file_registry["20230101120000"]  # Interface Design file

        # Exact title match - no alias needed
        alias = service._determine_best_alias("Interface Design", file)
        assert alias is None

        # Alias match - use the matched text
        alias = service._determine_best_alias("UI Design", file)
        assert alias == "UI Design"

        # Different text - use as alias
        alias = service._determine_best_alias("Interface", file)
        assert alias == "Interface"

    def test_find_similar_file_ids(self, service, file_registry):
        """Test finding similar file IDs for suggestions."""
        suggestions = service._find_similar_file_ids("20230101999999", file_registry)

        # Should find suggestions based on prefix matching
        assert len(suggestions) > 0
        assert any("20230101120000" in s for s in suggestions)

    def test_extract_body_content(self, service):
        """Test extracting body content excluding frontmatter."""
        content = """---
title: Test
tags: [test]
---

# Body Content

This is the body.
"""

        body = service._extract_body_content(content)
        assert "title: Test" not in body
        assert "# Body Content" in body
        assert "This is the body." in body

    def test_is_table_row(self, service):
        """Test table row detection."""
        assert service._is_table_row("| Column 1 | Column 2 |")
        assert service._is_table_row("|---|---|")
        assert not service._is_table_row("Regular text")
        assert not service._is_table_row("| Not closed")

    def test_find_link_candidates_excludes_existing_wikilinks(
        self, service, file_registry
    ):
        """Test that existing WikiLinks are excluded."""
        content = """# My Document

This discusses [[20230101120000|Interface Design]] and how it works.
We also need to consider UI Design for the project.
"""

        candidates = service.find_link_candidates(content, file_registry)

        # Should only find "UI Design", not "Interface Design" in the WikiLink
        assert len(candidates) == 1
        assert candidates[0].text == "UI Design"

    def test_find_link_candidates_excludes_regular_links(self, service, file_registry):
        """Test that regular markdown links are excluded."""
        content = """# My Document

Check out this [Interface Design](https://example.com) resource.
We also need to work on UI Design.
"""

        candidates = service.find_link_candidates(content, file_registry)

        # Should only find "UI Design", not "Interface Design" in the regular link
        assert len(candidates) == 1
        assert candidates[0].text == "UI Design"

    def test_find_link_candidates_excludes_template_variables(
        self, service, file_registry
    ):
        """Test that template variables are excluded."""
        content = """# My Document

Template: {{Interface Design}} and <% UI Design %>
But we do need to discuss Interface Design in general.
"""

        candidates = service.find_link_candidates(content, file_registry)

        # Should only find the one outside template variables
        assert len(candidates) == 1
        assert candidates[0].position.line_number == 4

    def test_word_boundary_matching(self, service, file_registry):
        """Test that word boundaries are respected in matching."""
        content = """# My Document

The word "design" appears in Interface Design but not in "designed".
"""

        candidates = service.find_link_candidates(content, file_registry)

        # Should find "Interface Design" but not "design" or "designed"
        assert len(candidates) == 1
        assert candidates[0].text == "Interface Design"

    def test_case_insensitive_matching(self, service, file_registry):
        """Test case-insensitive matching."""
        content = """# My Document

We need better interface design and INTERFACE DESIGN.
"""

        candidates = service.find_link_candidates(content, file_registry)

        # Should find both matches despite different cases
        assert len(candidates) == 2
        assert all(c.target_file_id == "20230101120000" for c in candidates)

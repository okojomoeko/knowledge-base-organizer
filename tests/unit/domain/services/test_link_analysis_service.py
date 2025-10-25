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
        return LinkAnalysisService(config_dir=None)

    @pytest.fixture
    def test_vault_path(self):
        """Path to test vault with real data."""
        return (
            Path(__file__).parent.parent.parent.parent
            / "test-data"
            / "vaults"
            / "test-myvault"
        )

    @pytest.fixture
    def real_test_files(self, test_vault_path):
        """Load real test files from test-myvault."""
        from knowledge_base_organizer.infrastructure.config import Config
        from knowledge_base_organizer.infrastructure.file_repository import (
            FileRepository,
        )

        config = Config()
        file_repo = FileRepository(config)
        files = []

        # Load specific test files that we know exist
        test_file_paths = [
            test_vault_path / "101_PermanentNotes" / "20230624175527.md",  # CloudWatch
            test_vault_path
            / "101_PermanentNotes"
            / "20230709211042.md",  # AWS Organizations
            test_vault_path / "101_PermanentNotes" / "20230730200042.md",  # API Gateway
        ]

        for file_path in test_file_paths:
            if file_path.exists():
                try:
                    file = file_repo.load_file(file_path)
                    files.append(file)
                except Exception:
                    # Skip files that can't be loaded
                    pass

        return files

    @pytest.fixture
    def service_exclude_tables(self):
        """Create a LinkAnalysisService instance that excludes tables."""
        return LinkAnalysisService(exclude_tables=True, config_dir=None)

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

    def test_lrd_exclusion_with_frontmatter_boundary(self, service):
        """Test that LRDs are correctly excluded even after frontmatter processing."""
        content = """---
title: Test LRD Exclusion
id: 20250123000001
tags: [test, lrd]
---

# Test LRD Exclusion

This file mentions EC2 and ELB which should NOT be linked.

---

[20230727234718|EC2]: 20230727234718 "Amazon Elastic Compute Cloud (Amazon EC2)"
[20230730201034|ELB]: 20230730201034 "Elastic Load Balancing"
"""

        zones = service.extract_exclusion_zones(content)

        # Find LRD zones
        lrd_zones = [z for z in zones if z.zone_type == "link_ref_def"]
        assert len(lrd_zones) == 2, f"Expected 2 LRD zones, got {len(lrd_zones)}"

        # Verify LRD zones are correctly positioned
        # Debug: print actual line numbers
        for i, zone in enumerate(lrd_zones):
            print(f"LRD zone {i + 1}: Line {zone.start_line}")

        # The LRDs should be on lines 13 and 14 (after frontmatter and content)
        ec2_zone = next(z for z in lrd_zones if z.start_line == 13)  # EC2 LRD line
        elb_zone = next(z for z in lrd_zones if z.start_line == 14)  # ELB LRD line

        assert ec2_zone.start_column == 0
        assert ec2_zone.end_column == 80  # Length of EC2 LRD
        assert elb_zone.start_column == 0
        assert elb_zone.end_column == 61  # Length of ELB LRD

    def test_frontmatter_boundary_detection(self, service):
        """Test that frontmatter boundaries are correctly detected and subsequent --- lines ignored."""
        content = """---
title: Test File
id: 20250123000001
---

# Content

Some content here.

---

This is a horizontal rule, not frontmatter.
More content after the rule.
"""

        zones = service.extract_exclusion_zones(content)

        # Should only have one frontmatter zone
        frontmatter_zones = [z for z in zones if z.zone_type == "frontmatter"]
        assert len(frontmatter_zones) == 1, (
            f"Expected 1 frontmatter zone, got {len(frontmatter_zones)}"
        )

        zone = frontmatter_zones[0]
        assert zone.start_line == 1
        assert zone.end_line == 4  # Should end at the first closing ---

    def test_alias_always_included(self, service, file_registry):
        """Test that aliases are always included for better readability."""
        file = file_registry["20230101120000"]  # Interface Design file
        target_info = {
            "text": "interface design",
            "file_id": "20230101120000",
            "source_type": "title",
            "confidence": 1.0,
            "original_text": "Interface Design",
        }

        # Test with exact title match - should still include alias
        alias = service._determine_best_alias_with_japanese(
            "Interface Design", file, target_info
        )
        assert alias == "Interface Design", (
            "Should always include alias for readability"
        )

        # Test with alias match - should include the matched text as alias
        alias = service._determine_best_alias_with_japanese(
            "UI Design", file, target_info
        )
        assert alias == "UI Design", "Should use matched text as alias"

    def test_multiple_lrds_on_same_line(self, service):
        """Test handling of multiple LRDs on the same line."""
        content = """---
title: Test Multiple LRDs
---

# Content

[20230727234718|EC2]: 20230727234718 "Title1" [20230730201034|ELB]: 20230730201034 "Title2"
"""

        zones = service.extract_exclusion_zones(content)

        # Find LRD zones
        lrd_zones = [z for z in zones if z.zone_type == "link_ref_def"]
        assert len(lrd_zones) == 2, (
            f"Expected 2 LRD zones on same line, got {len(lrd_zones)}"
        )

        # Verify both LRDs are on the same line but different columns
        assert all(z.start_line == 7 for z in lrd_zones), (
            "Both LRDs should be on line 7"
        )
        assert lrd_zones[0].start_column != lrd_zones[1].start_column, (
            "LRDs should have different column positions"
        )

    def test_detect_orphaned_notes_completely_isolated(self, service):
        """Test detection of completely isolated notes (no links)."""
        # Create files with no links between them
        orphaned_file = MarkdownFile(
            path=Path("test.md"),
            file_id="20230101120000",
            frontmatter=Frontmatter(
                title="Orphaned Note",
                tags=["isolated"],
                id="20230101120000",
            ),
            content="# Orphaned Note\n\nThis note has no connections.",
        )

        connected_file = MarkdownFile(
            path=Path("test.md"),
            file_id="20230101120001",
            frontmatter=Frontmatter(
                title="Connected Note",
                tags=["connected"],
                id="20230101120001",
            ),
            content="# Connected Note\n\nThis note mentions something.",
        )

        files = [orphaned_file, connected_file]
        orphaned_notes = service.detect_orphaned_notes(files)

        # Both files should be detected as orphaned since they have no connections
        assert len(orphaned_notes) == 2

        # Find the specific orphaned note
        orphaned = next(n for n in orphaned_notes if n.file_id == "20230101120000")
        assert orphaned.incoming_links == 0
        assert orphaned.outgoing_links == 0
        assert orphaned.isolation_score == 1.0  # Completely isolated

    def test_detect_orphaned_notes_with_connections(self, service):
        """Test that well-connected notes are not detected as orphaned."""
        # Create files with links between them
        source_file = MarkdownFile(
            path=Path("test.md"),
            file_id="20230101120000",
            frontmatter=Frontmatter(
                title="Source Note",
                id="20230101120000",
            ),
            content="# Source Note\n\nThis links to [[20230101120001|Target Note]].",
            wiki_links=[
                WikiLink(
                    target_id="20230101120001",
                    alias="Target Note",
                    line_number=3,
                    column_start=17,
                    column_end=45,
                )
            ],
        )

        target_file = MarkdownFile(
            path=Path("test.md"),
            file_id="20230101120001",
            frontmatter=Frontmatter(
                title="Target Note",
                id="20230101120001",
            ),
            content="# Target Note\n\nThis is referenced by the source.",
        )

        files = [source_file, target_file]
        orphaned_notes = service.detect_orphaned_notes(files)

        # Neither file should be orphaned since they are connected
        assert len(orphaned_notes) == 0

    def test_suggest_connections_tag_similarity(self, service):
        """Test connection suggestions based on tag similarity."""
        orphaned_file = MarkdownFile(
            path=Path("test.md"),
            file_id="20230101120000",
            frontmatter=Frontmatter(
                title="Orphaned Note",
                tags=["programming", "python"],
                id="20230101120000",
            ),
            content="# Orphaned Note\n\nContent about programming.",
        )

        similar_file = MarkdownFile(
            path=Path("test.md"),
            file_id="20230101120001",
            frontmatter=Frontmatter(
                title="Similar Note",
                tags=["programming", "javascript"],
                id="20230101120001",
            ),
            content="# Similar Note\n\nContent about programming.",
        )

        different_file = MarkdownFile(
            path=Path("test.md"),
            file_id="20230101120002",
            frontmatter=Frontmatter(
                title="Different Note",
                tags=["cooking", "recipes"],
                id="20230101120002",
            ),
            content="# Different Note\n\nContent about cooking.",
        )

        files = [orphaned_file, similar_file, different_file]
        file_registry = {f.frontmatter.id: f for f in files}
        link_graph = {
            "incoming": {f.frontmatter.id: [] for f in files},
            "outgoing": {f.frontmatter.id: [] for f in files},
        }

        suggestions = service._suggest_connections(
            orphaned_file, files, file_registry, link_graph
        )

        # Should suggest connection to similar_file based on shared "programming" tag
        assert len(suggestions) >= 1
        tag_suggestions = [
            s for s in suggestions if s.connection_type == "tag_similarity"
        ]
        assert len(tag_suggestions) >= 1

        tag_suggestion = tag_suggestions[0]
        assert tag_suggestion.target_file_id == "20230101120001"
        assert "programming" in tag_suggestion.reason

    def test_suggest_connections_keyword_similarity(self, service):
        """Test connection suggestions based on keyword similarity."""
        orphaned_file = MarkdownFile(
            path=Path("test.md"),
            file_id="20230101120000",
            frontmatter=Frontmatter(
                title="Orphaned Note",
                id="20230101120000",
            ),
            content="# Orphaned Note\n\nThis discusses Machine Learning algorithms and Neural Networks.",
        )

        similar_file = MarkdownFile(
            path=Path("test.md"),
            file_id="20230101120001",
            frontmatter=Frontmatter(
                title="Similar Note",
                id="20230101120001",
            ),
            content="# Similar Note\n\nContent about Machine Learning and Deep Learning algorithms.",
        )

        files = [orphaned_file, similar_file]
        file_registry = {f.frontmatter.id: f for f in files}
        link_graph = {
            "incoming": {f.frontmatter.id: [] for f in files},
            "outgoing": {f.frontmatter.id: [] for f in files},
        }

        suggestions = service._suggest_connections(
            orphaned_file, files, file_registry, link_graph
        )

        # Should suggest connection based on shared keywords
        keyword_suggestions = [
            s for s in suggestions if s.connection_type == "keyword_match"
        ]
        assert len(keyword_suggestions) >= 1

        keyword_suggestion = keyword_suggestions[0]
        assert keyword_suggestion.target_file_id == "20230101120001"
        assert (
            "Machine" in keyword_suggestion.reason
            or "Learning" in keyword_suggestion.reason
        )

    def test_suggest_connections_title_mentions(self, service):
        """Test connection suggestions based on title mentions in content."""
        orphaned_file = MarkdownFile(
            path=Path("test.md"),
            file_id="20230101120000",
            frontmatter=Frontmatter(
                title="Orphaned Note",
                id="20230101120000",
            ),
            content="# Orphaned Note\n\nThis note discusses Database Design patterns.",
        )

        mentioned_file = MarkdownFile(
            path=Path("test.md"),
            file_id="20230101120001",
            frontmatter=Frontmatter(
                title="Database Design",
                id="20230101120001",
            ),
            content="# Database Design\n\nContent about database design.",
        )

        files = [orphaned_file, mentioned_file]
        file_registry = {f.frontmatter.id: f for f in files}
        link_graph = {
            "incoming": {f.frontmatter.id: [] for f in files},
            "outgoing": {f.frontmatter.id: [] for f in files},
        }

        suggestions = service._suggest_connections(
            orphaned_file, files, file_registry, link_graph
        )

        # Should suggest connection based on title mention
        content_suggestions = [
            s for s in suggestions if s.connection_type == "content_similarity"
        ]
        assert len(content_suggestions) >= 1

        content_suggestion = content_suggestions[0]
        assert content_suggestion.target_file_id == "20230101120001"
        assert "Database Design" in content_suggestion.reason

    def test_generate_auto_link_suggestions(self, service):
        """Test generation of auto-link suggestions for orphaned notes."""
        # Create orphaned note with high-confidence connection suggestions
        from knowledge_base_organizer.domain.services.link_analysis_service import (
            ConnectionSuggestion,
            OrphanedNote,
        )

        orphaned_note = OrphanedNote(
            file_path="test.md",
            file_id="20230101120000",
            title="Orphaned Note",
            tags=["test"],
            incoming_links=0,
            outgoing_links=0,
            connection_suggestions=[
                ConnectionSuggestion(
                    target_file_id="20230101120001",
                    target_title="Target Note",
                    connection_type="tag_similarity",
                    confidence=0.8,  # High confidence
                    reason="Shares programming tag",
                    suggested_link_text="Target Note",
                ),
                ConnectionSuggestion(
                    target_file_id="20230101120002",
                    target_title="Another Note",
                    connection_type="keyword_match",
                    confidence=0.4,  # Low confidence
                    reason="Shares some keywords",
                    suggested_link_text="Another Note",
                ),
            ],
            isolation_score=1.0,
        )

        suggestions = service.generate_auto_link_suggestions([orphaned_note])

        # Should only include high-confidence suggestions
        assert "20230101120000" in suggestions
        file_suggestions = suggestions["20230101120000"]
        assert len(file_suggestions) == 1  # Only the high-confidence one

        suggestion = file_suggestions[0]
        assert suggestion["target_file_id"] == "20230101120001"
        assert suggestion["confidence"] == 0.8
        assert "[[20230101120001|Target Note]]" in suggestion["auto_link_format"]

    def test_extract_keywords(self, service):
        """Test keyword extraction from content."""
        content = """---
title: Test File
---

# Machine Learning Algorithms

This document discusses various Machine Learning algorithms including
Neural Networks, Decision Trees, and Support Vector Machines.
The implementation uses Python and TensorFlow for deep learning.
"""

        keywords = service._extract_keywords(content)

        # Should extract meaningful keywords
        expected_keywords = {
            "Machine",
            "Learning",
            "Algorithms",
            "Neural",
            "Networks",
            "Decision",
            "Trees",
            "Support",
            "Vector",
            "Machines",
            "Python",
            "TensorFlow",
            "deep",
            "learning",
        }

        # Check that we found some of the expected keywords
        found_keywords = keywords.intersection(expected_keywords)
        assert len(found_keywords) >= 5, (
            f"Expected at least 5 keywords, found: {found_keywords}"
        )

        # Should not include most common words (but "uses" might slip through as it's 4 chars)
        very_common_words = {"the", "and", "for", "this"}
        assert not keywords.intersection(very_common_words), (
            "Should not include very common words"
        )

    def test_calculate_isolation_score(self, service):
        """Test isolation score calculation."""
        # Completely isolated note
        score = service._calculate_isolation_score(0, 0, 100)
        assert score == 1.0

        # Well-connected note in large vault
        score = service._calculate_isolation_score(5, 5, 100)
        assert score < 0.5

        # Moderately connected note (2 connections in 50-file vault)
        # Expected connections = max(2, 50 * 0.05) = max(2, 2.5) = 2.5
        # Connection ratio = 2 / 2.5 = 0.8
        # Isolation score = 1.0 - 0.8 = 0.2
        score = service._calculate_isolation_score(1, 1, 50)
        assert 0.1 < score < 0.3  # Adjusted expected range

    def test_detect_orphaned_notes_with_realistic_data(self, service):
        """Test orphaned note detection with realistic test data."""
        # Create realistic test files based on actual vault structure
        cloudwatch_file = MarkdownFile(
            path=Path("test.md"),
            file_id="20230624175527",
            frontmatter=Frontmatter(
                title="Amazon CloudWatch",
                aliases=["CloudWatch", "cloudwatch"],
                tags=["aws", "monitoring"],
                id="20230624175527",
            ),
            content="""# Amazon CloudWatch

統合的な運用監視サービス

## 機能
- メトリクス監視
- ログ管理
- アラーム設定

## ユースケース
EC2、ELB、RDSなどで構成された3層構造のwebアプリケーションを考える。
""",
        )

        organizations_file = MarkdownFile(
            path=Path("test.md"),
            file_id="20230709211042",
            frontmatter=Frontmatter(
                title="AWS Organizations",
                aliases=["Organizations"],
                id="20230709211042",
            ),
            content="# AWS Organizations\n\nAWS Organizations is a service for managing multiple AWS accounts.",
        )

        files = [cloudwatch_file, organizations_file]
        orphaned_notes = service.detect_orphaned_notes(files)

        # Both files should be detected as orphaned since they don't link to each other
        assert len(orphaned_notes) == 2

        # Check that orphaned notes have proper structure
        for orphaned in orphaned_notes:
            assert orphaned.file_id
            assert orphaned.file_path
            assert isinstance(orphaned.isolation_score, float)
            assert 0.0 <= orphaned.isolation_score <= 1.0
            assert isinstance(orphaned.connection_suggestions, list)

    def test_keyword_extraction_with_real_data(self, service, real_test_files):
        """Test keyword extraction with real markdown content."""
        if not real_test_files:
            pytest.skip("No real test files available")

        # Test with CloudWatch file (should have technical keywords)
        cloudwatch_file = next(
            (f for f in real_test_files if "CloudWatch" in (f.frontmatter.title or "")),
            None,
        )

        if cloudwatch_file:
            keywords = service._extract_keywords(cloudwatch_file.content)

            # Should extract technical terms from CloudWatch content
            expected_technical_terms = {"CloudWatch", "AWS", "EC2", "ELB", "RDS"}
            found_technical = keywords.intersection(expected_technical_terms)
            assert len(found_technical) >= 2, (
                f"Expected technical terms, found: {found_technical}"
            )

            # Should extract Japanese terms
            expected_japanese = {"メトリクス", "アラーム", "ダッシュボード"}
            found_japanese = keywords.intersection(expected_japanese)
            assert len(found_japanese) >= 1, (
                f"Expected Japanese terms, found: {found_japanese}"
            )

    def test_connection_suggestions_with_real_data(self, service, real_test_files):
        """Test connection suggestions with real test data."""
        if len(real_test_files) < 2:
            pytest.skip("Need at least 2 real test files")

        # Create a file registry
        file_registry = {
            f.frontmatter.id: f for f in real_test_files if f.frontmatter.id
        }
        link_graph = {"incoming": {}, "outgoing": {}}

        # Initialize empty link graph
        for file_id in file_registry:
            link_graph["incoming"][file_id] = []
            link_graph["outgoing"][file_id] = []

        # Test suggestions for the first file
        test_file = real_test_files[0]
        suggestions = service._suggest_connections(
            test_file, real_test_files, file_registry, link_graph
        )

        # Should generate some suggestions
        assert isinstance(suggestions, list)

        # Check suggestion structure
        for suggestion in suggestions:
            assert suggestion.target_file_id in file_registry
            assert suggestion.connection_type in [
                "tag_similarity",
                "keyword_match",
                "content_similarity",
            ]
            assert 0.0 <= suggestion.confidence <= 1.0
            assert suggestion.reason

    def test_keyword_extraction_configuration_loading(self, service):
        """Test that keyword extraction manager loads configuration properly."""
        # Test that the keyword manager is initialized
        assert hasattr(service, "keyword_manager")
        assert service.keyword_manager is not None

        # Test basic keyword extraction
        test_content = """
        # Machine Learning and AI

        This document discusses artificial intelligence, neural networks, and deep learning.
        We also cover データベース and API design patterns.
        """

        keywords = service._extract_keywords(test_content)

        # Should extract both English and Japanese keywords
        assert len(keywords) > 0

        # Should include technical terms
        technical_terms = {"Machine", "Learning", "API", "neural", "networks"}
        found_technical = keywords.intersection(technical_terms)
        assert len(found_technical) >= 2, (
            f"Expected technical terms, found: {found_technical}"
        )

    def test_keyword_extraction_with_japanese_content(self, service):
        """Test keyword extraction with mixed Japanese and English content."""
        japanese_content = """
        # プログラミング言語とフレームワーク

        このドキュメントでは、JavaScript、Python、React について説明します。
        また、データベース設計やAPI開発についても触れます。
        機械学習とディープラーニングの基礎概念も含まれています。
        """

        keywords = service._extract_keywords(japanese_content)

        # Should extract Japanese keywords
        expected_japanese = {
            "プログラミング",
            "データベース",
            "機械学習",
            "ディープラーニング",
        }
        found_japanese = keywords.intersection(expected_japanese)
        assert len(found_japanese) >= 2, (
            f"Expected Japanese keywords, found: {found_japanese}"
        )

        # Should extract English technical terms
        expected_english = {"JavaScript", "Python", "React", "API"}
        found_english = keywords.intersection(expected_english)
        assert len(found_english) >= 2, (
            f"Expected English keywords, found: {found_english}"
        )

    def test_orphaned_note_detection_with_mixed_connections(self, service):
        """Test orphaned note detection with a mix of connected and isolated notes."""
        # Create test files with some connections
        connected_file1 = MarkdownFile(
            path=Path("test.md"),
            file_id="20230101120000",
            frontmatter=Frontmatter(
                title="Connected Note 1",
                tags=["programming", "python"],
                id="20230101120000",
            ),
            content="# Connected Note 1\n\nThis links to [[20230101120001|Connected Note 2]].",
            wiki_links=[
                WikiLink(
                    target_id="20230101120001",
                    alias="Connected Note 2",
                    line_number=3,
                    column_start=17,
                    column_end=45,
                )
            ],
        )

        connected_file2 = MarkdownFile(
            path=Path("test.md"),
            file_id="20230101120001",
            frontmatter=Frontmatter(
                title="Connected Note 2",
                tags=["programming", "javascript"],
                id="20230101120001",
            ),
            content="# Connected Note 2\n\nThis is referenced by Connected Note 1.",
        )

        orphaned_file = MarkdownFile(
            path=Path("test.md"),
            file_id="20230101120002",
            frontmatter=Frontmatter(
                title="Orphaned Note",
                tags=["isolated"],
                id="20230101120002",
            ),
            content="# Orphaned Note\n\nThis note has no connections to other notes.",
        )

        files = [connected_file1, connected_file2, orphaned_file]
        orphaned_notes = service.detect_orphaned_notes(files)

        # Only the orphaned file should be detected
        assert len(orphaned_notes) == 1
        assert orphaned_notes[0].file_id == "20230101120002"
        assert orphaned_notes[0].isolation_score > 0.5  # Should be highly isolated

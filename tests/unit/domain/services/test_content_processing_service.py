"""Tests for ContentProcessingService."""

import pytest

from knowledge_base_organizer.domain.models import (
    TextPosition,
)
from knowledge_base_organizer.domain.services.content_processing_service import (
    ContentProcessingService,
    LinkCandidate,
)


class TestContentProcessingService:
    """Test cases for ContentProcessingService."""

    @pytest.fixture
    def service(self):
        """Create a ContentProcessingService instance."""
        return ContentProcessingService(max_links_per_file=10)

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

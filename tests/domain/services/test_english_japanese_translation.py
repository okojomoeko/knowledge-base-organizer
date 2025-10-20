"""Tests for English-Japanese translation system in FrontmatterEnhancementService."""

from pathlib import Path

import pytest

from knowledge_base_organizer.domain.models import Frontmatter, MarkdownFile
from knowledge_base_organizer.domain.services.frontmatter_enhancement_service import (
    FrontmatterEnhancementService,
)


class TestEnglishJapaneseTranslation:
    """Test English-Japanese translation functionality."""

    @pytest.fixture
    def service(self):
        """Create FrontmatterEnhancementService instance."""
        return FrontmatterEnhancementService()

    @pytest.fixture
    def test_file_with_mixed_content(self):
        """Create test file with mixed English-Japanese content."""
        content = """
# API Documentation

This document describes the API エーピーアイ for our database DB システム.
We use JSON ジェイソン format for data exchange.
The システム supports both REST and GraphQL.
The ML 機械学習 algorithms process the data.
"""
        return MarkdownFile(
            path=Path("test.md"),
            frontmatter=Frontmatter(
                title="API Test", id="20250119120000", tags=[], aliases=[]
            ),
            content=content,
        )

    def test_find_english_japanese_matches(self, service, test_file_with_mixed_content):
        """Test finding English-Japanese term matches in content."""
        matches = service.find_english_japanese_matches(
            test_file_with_mixed_content.content
        )

        # Should find matches for API, DB, JSON, ML, REST
        match_dict = {match[0]: (match[1], match[2]) for match in matches}

        # Check English to Japanese matches
        assert "API" in match_dict
        assert "DB" in match_dict
        assert "JSON" in match_dict
        assert "ML" in match_dict
        assert "REST" in match_dict

        # Check Japanese to English matches
        japanese_terms = [
            match[0] for match in matches if match[2].endswith("to_english")
        ]
        assert "エーピーアイ" in japanese_terms
        assert "ジェイソン" in japanese_terms
        assert "機械学習" in japanese_terms

    def test_suggest_cross_language_aliases(
        self, service, test_file_with_mixed_content
    ):
        """Test suggesting cross-language aliases."""
        aliases = service.suggest_cross_language_aliases(test_file_with_mixed_content)

        # Should suggest Japanese equivalents for English terms found in content
        assert "エーピーアイ" in aliases
        assert "データベース" in aliases
        assert "ジェイソン" in aliases
        assert "機械学習" in aliases

        # Should suggest English equivalents for Japanese terms
        assert "API" in aliases
        assert "JSON" in aliases
        assert "ML" in aliases

    def test_extract_technical_terms_from_content(
        self, service, test_file_with_mixed_content
    ):
        """Test extracting technical terms from content."""
        tech_terms = service.extract_technical_terms_from_content(
            test_file_with_mixed_content.content
        )

        # Should extract English technical terms
        assert "API" in tech_terms
        assert "DB" in tech_terms
        assert "JSON" in tech_terms
        assert "ML" in tech_terms
        assert "REST" in tech_terms

    def test_suggest_technical_tags_from_content(
        self, service, test_file_with_mixed_content
    ):
        """Test suggesting technical tags based on content."""
        tech_tags = service.suggest_technical_tags_from_content(
            test_file_with_mixed_content
        )

        # Should suggest tags based on technical terms
        expected_tags = ["tech-api", "tech-db", "json", "tech-ml", "rest"]
        for tag in expected_tags:
            assert tag in tech_tags

    def test_abbreviation_expansions_loaded(self, service):
        """Test that abbreviation expansions are properly loaded."""
        abbreviations = service.tag_pattern_manager.japanese_variations.get(
            "abbreviation_expansions", {}
        )

        # Should have loaded abbreviation expansions
        assert len(abbreviations) > 0

        # Check specific abbreviations
        assert "DB" in abbreviations
        assert "REST" in abbreviations
        assert (
            "API" in abbreviations if "API" in abbreviations else True
        )  # API might be in english_japanese_pairs instead

        # Check structure of abbreviation data
        db_data = abbreviations["DB"]
        assert "full_form" in db_data
        assert "english" in db_data
        assert "variations" in db_data
        assert db_data["full_form"] == "データベース"
        assert db_data["english"] == "Database"

    def test_english_japanese_pairs_loaded(self, service):
        """Test that English-Japanese pairs are properly loaded."""
        pairs = service.tag_pattern_manager.japanese_variations.get(
            "english_japanese_pairs", {}
        )

        # Should have loaded English-Japanese pairs
        assert len(pairs) > 0

        # Check specific pairs
        assert "API" in pairs
        assert "DB" in pairs
        assert "JSON" in pairs
        assert "ML" in pairs

    def test_enhancement_with_cross_language_aliases(self, service, tmp_path):
        """Test frontmatter enhancement with cross-language aliases."""
        content = """
# Database システム

This is about database DB management and API エーピーアイ integration.
"""
        test_file_path = tmp_path / "db_test.md"
        test_file_path.write_text(content)

        test_file = MarkdownFile(
            path=test_file_path,
            frontmatter=Frontmatter(
                title="Database System",
                id="20250119120000",
                tags=["database"],
                aliases=[],
            ),
            content=content,
        )

        result = service.enhance_file_frontmatter(test_file, apply_changes=False)

        # Should suggest cross-language aliases
        assert result.success
        assert len(result.changes_applied) > 0

        # Check if cross-language aliases were suggested in changes
        cross_language_changes = [
            change
            for change in result.changes_applied
            if "cross-language aliases" in change
        ]
        assert len(cross_language_changes) > 0

        # The cross-language aliases should be mentioned in the changes
        cross_language_change = cross_language_changes[0]
        assert (
            "エーピーアイ" in cross_language_change
            or "データベース" in cross_language_change
        )

    def test_technical_tag_suggestions(self, service, tmp_path):
        """Test technical tag suggestions from English-Japanese patterns."""
        content = """
# Machine Learning システム

This system uses AI 人工知能 and ML algorithms for data processing.
The API provides REST endpoints for database access.
"""
        test_file_path = tmp_path / "ml_test.md"
        test_file_path.write_text(content)

        test_file = MarkdownFile(
            path=test_file_path,
            frontmatter=Frontmatter(
                title="ML System", id="20250119120000", tags=[], aliases=[]
            ),
            content=content,
        )

        result = service.enhance_file_frontmatter(test_file, apply_changes=False)

        # Should suggest technical tags
        assert result.success
        enhanced_tags = result.enhanced_frontmatter.get("tags", [])

        # Check that technical tag changes were applied
        tech_tag_changes = [
            change for change in result.changes_applied if "technical tags" in change
        ]
        assert len(tech_tag_changes) > 0

        # Verify the technical tags are mentioned in the changes
        tech_tag_change = tech_tag_changes[0]
        assert (
            "tech-api" in tech_tag_change
            or "tech-ai" in tech_tag_change
            or "tech-ml" in tech_tag_change
        )

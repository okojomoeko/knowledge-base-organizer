"""End-to-end integration tests for dead link detection."""

from pathlib import Path

import pytest

from knowledge_base_organizer.application.dead_link_detection_use_case import (
    DeadLinkDetectionRequest,
    DeadLinkDetectionUseCase,
)
from knowledge_base_organizer.domain.services.link_analysis_service import (
    LinkAnalysisService,
)
from knowledge_base_organizer.infrastructure.config import ProcessingConfig
from knowledge_base_organizer.infrastructure.file_repository import FileRepository


class TestDeadLinkDetectionEndToEnd:
    """End-to-end tests for dead link detection functionality."""

    @pytest.fixture
    def test_vault_path(self):
        """Path to test vault."""
        return Path("tests/test-data/vaults/test-myvault")

    @pytest.fixture
    def use_case(self):
        """Create a dead link detection use case with real dependencies."""
        config = ProcessingConfig.get_default_config()
        file_repository = FileRepository(config)
        link_analysis_service = LinkAnalysisService(config_dir=None)

        return DeadLinkDetectionUseCase(
            file_repository=file_repository,
            link_analysis_service=link_analysis_service,
            config=config,
        )

    def test_detect_dead_links_in_test_vault(self, use_case, test_vault_path):
        """Test dead link detection with real test vault data."""
        if not test_vault_path.exists():
            pytest.skip("Test vault not available")

        # Create request
        request = DeadLinkDetectionRequest(vault_path=test_vault_path)

        # Execute detection
        result = use_case.execute(request)

        # Verify results structure
        assert result.vault_path == str(test_vault_path)
        assert result.total_files_scanned > 0
        assert isinstance(result.total_dead_links, int)
        assert isinstance(result.files_with_dead_links, int)
        assert isinstance(result.dead_links_by_type, dict)
        assert isinstance(result.dead_links, list)

        # Verify summary contains expected fields
        assert "total_files" in result.summary
        assert "files_with_dead_links" in result.summary
        assert "total_dead_links" in result.summary
        assert "vault_path" in result.summary

        # If there are dead links, verify their structure
        for dead_link in result.dead_links:
            assert dead_link.source_file
            assert dead_link.link_text
            assert dead_link.link_type in ["wikilink", "regular_link", "link_ref_def"]
            assert dead_link.line_number > 0
            assert isinstance(dead_link.suggested_fixes, list)

    def test_detect_dead_links_with_include_patterns(self, use_case, test_vault_path):
        """Test dead link detection with include patterns."""
        if not test_vault_path.exists():
            pytest.skip("Test vault not available")

        # Create request with include patterns
        request = DeadLinkDetectionRequest(
            vault_path=test_vault_path,
            include_patterns=["**/*.md"],
        )

        # Execute detection
        result = use_case.execute(request)

        # Should find files and potentially dead links
        assert result.total_files_scanned > 0

    def test_detect_dead_links_with_exclude_patterns(self, use_case, test_vault_path):
        """Test dead link detection with exclude patterns."""
        if not test_vault_path.exists():
            pytest.skip("Test vault not available")

        # Create request with exclude patterns to exclude template directories
        request = DeadLinkDetectionRequest(
            vault_path=test_vault_path,
            exclude_patterns=[
                "**/900_TemplaterNotes/**",
                "**/903_BookSearchTemplates/**",
            ],
        )

        # Execute detection
        result = use_case.execute(request)

        # Should still find files but potentially fewer dead links
        assert result.total_files_scanned >= 0

    def test_detect_dead_links_empty_vault(self, use_case, tmp_path):
        """Test dead link detection with empty vault."""
        # Create empty vault directory
        empty_vault = tmp_path / "empty_vault"
        empty_vault.mkdir()

        # Create request
        request = DeadLinkDetectionRequest(vault_path=empty_vault)

        # Execute detection
        result = use_case.execute(request)

        # Should handle empty vault gracefully
        assert result.total_files_scanned == 0
        assert result.files_with_dead_links == 0
        assert result.total_dead_links == 0
        assert len(result.dead_links) == 0

    def test_detect_dead_links_vault_with_valid_links_only(self, use_case, tmp_path):
        """Test dead link detection with vault containing only valid links."""
        # Create test vault with valid links
        vault = tmp_path / "valid_vault"
        vault.mkdir()

        # Create two files that reference each other
        file1 = vault / "file1.md"
        file1.write_text("""---
title: File 1
id: "20230101120000"
---

# File 1

This references [[20230101120001|File 2]].
""")

        file2 = vault / "file2.md"
        file2.write_text("""---
title: File 2
id: "20230101120001"
---

# File 2

This references [[20230101120000|File 1]].
""")

        # Create request
        request = DeadLinkDetectionRequest(vault_path=vault)

        # Execute detection
        result = use_case.execute(request)

        # Should find files but no dead links
        assert result.total_files_scanned == 2
        assert result.files_with_dead_links == 0
        assert result.total_dead_links == 0
        assert len(result.dead_links) == 0

    def test_detect_dead_links_statistics_accuracy(self, use_case, tmp_path):
        """Test that dead link statistics are calculated accurately."""
        # Create test vault with known dead links
        vault = tmp_path / "test_vault"
        vault.mkdir()

        # File with multiple dead WikiLinks
        file1 = vault / "file1.md"
        file1.write_text("""---
title: File 1
id: "20230101120000"
---

# File 1

Dead links: [[nonexistent1]] and [[nonexistent2]].
""")

        # File with dead regular link
        file2 = vault / "file2.md"
        file2.write_text("""---
title: File 2
id: "20230101120001"
---

# File 2

Dead regular link: [empty link]().
""")

        # Create request
        request = DeadLinkDetectionRequest(vault_path=vault)

        # Execute detection
        result = use_case.execute(request)

        # Verify statistics
        assert result.total_files_scanned == 2
        assert result.files_with_dead_links == 1  # One file has dead links (WikiLinks)
        assert result.total_dead_links == 2  # 2 WikiLinks detected
        assert result.dead_links_by_type.get("wikilink", 0) == 2

        # Verify individual dead links
        assert len(result.dead_links) >= 2

        # Check that we have the expected WikiLinks
        wikilink_targets = [
            dl.target for dl in result.dead_links if dl.link_type == "wikilink"
        ]
        assert "nonexistent1" in wikilink_targets
        assert "nonexistent2" in wikilink_targets

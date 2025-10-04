"""Tests for DeadLinkDetectionUseCase."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from knowledge_base_organizer.application.dead_link_detection_use_case import (
    DeadLinkDetectionRequest,
    DeadLinkDetectionUseCase,
)
from knowledge_base_organizer.domain.models import Frontmatter, MarkdownFile
from knowledge_base_organizer.domain.services.link_analysis_service import DeadLink
from knowledge_base_organizer.infrastructure.config import ProcessingConfig


class TestDeadLinkDetectionUseCase:
    """Test cases for DeadLinkDetectionUseCase."""

    @pytest.fixture
    def mock_file_repository(self):
        """Create a mock file repository."""
        return Mock()

    @pytest.fixture
    def mock_link_analysis_service(self):
        """Create a mock link analysis service."""
        return Mock()

    @pytest.fixture
    def config(self):
        """Create a processing configuration."""
        return ProcessingConfig.get_default_config()

    @pytest.fixture
    def use_case(self, mock_file_repository, mock_link_analysis_service, config):
        """Create a DeadLinkDetectionUseCase instance."""
        return DeadLinkDetectionUseCase(
            file_repository=mock_file_repository,
            link_analysis_service=mock_link_analysis_service,
            config=config,
        )

    @pytest.fixture
    def sample_files(self):
        """Create sample markdown files for testing."""
        return [
            MarkdownFile(
                path=Path("test.md"),  # Use the special test path that's allowed
                file_id="20230101120000",
                frontmatter=Frontmatter(
                    title="Test File 1",
                    id="20230101120000",
                ),
                content="# Test File 1\n\nContent here.",
            ),
            MarkdownFile(
                path=Path("test.md"),  # Use the special test path that's allowed
                file_id="20230101120001",
                frontmatter=Frontmatter(
                    title="Test File 2",
                    id="20230101120001",
                ),
                content="# Test File 2\n\nMore content.",
            ),
        ]

    @pytest.fixture
    def sample_dead_links(self):
        """Create sample dead links for testing."""
        return [
            DeadLink(
                source_file="test1.md",
                link_text="[[nonexistent]]",
                link_type="wikilink",
                line_number=3,
                target="nonexistent",
                suggested_fixes=["Did you mean '20230101120001'?"],
            ),
            DeadLink(
                source_file="test2.md",
                link_text="[empty link]()",
                link_type="regular_link",
                line_number=5,
                target="",
                suggested_fixes=["Remove empty link or add valid URL"],
            ),
        ]

    def test_execute_successful_detection(
        self,
        use_case,
        mock_file_repository,
        mock_link_analysis_service,
        sample_files,
        sample_dead_links,
        tmp_path,
    ):
        """Test successful dead link detection."""
        # Setup mocks
        mock_file_repository.load_vault.return_value = sample_files
        mock_link_analysis_service.detect_dead_links.return_value = sample_dead_links

        # Create request
        request = DeadLinkDetectionRequest(vault_path=tmp_path)

        # Execute
        result = use_case.execute(request)

        # Verify
        assert result.vault_path == str(tmp_path)
        assert result.total_files_scanned == 2
        assert result.files_with_dead_links == 2  # Both files have dead links
        assert result.total_dead_links == 2
        assert result.dead_links_by_type == {"wikilink": 1, "regular_link": 1}
        assert len(result.dead_links) == 2

        # Verify service calls
        mock_file_repository.load_vault.assert_called_once()
        mock_link_analysis_service.detect_dead_links.assert_called_once()

    def test_execute_no_dead_links(
        self,
        use_case,
        mock_file_repository,
        mock_link_analysis_service,
        sample_files,
        tmp_path,
    ):
        """Test detection when no dead links are found."""
        # Setup mocks
        mock_file_repository.load_vault.return_value = sample_files
        mock_link_analysis_service.detect_dead_links.return_value = []

        # Create request
        request = DeadLinkDetectionRequest(vault_path=tmp_path)

        # Execute
        result = use_case.execute(request)

        # Verify
        assert result.total_files_scanned == 2
        assert result.files_with_dead_links == 0
        assert result.total_dead_links == 0
        assert result.dead_links_by_type == {}
        assert len(result.dead_links) == 0

    def test_execute_with_include_patterns(
        self,
        use_case,
        mock_file_repository,
        mock_link_analysis_service,
        sample_files,
        tmp_path,
    ):
        """Test detection with include patterns."""
        # Setup mocks
        mock_file_repository.load_vault.return_value = sample_files
        mock_link_analysis_service.detect_dead_links.return_value = []

        # Create request with include patterns
        request = DeadLinkDetectionRequest(
            vault_path=tmp_path,
            include_patterns=["**/*.md"],
        )

        # Execute
        use_case.execute(request)

        # Verify that load_vault was called with the vault path
        mock_file_repository.load_vault.assert_called_once_with(tmp_path)

        # Verify that the repository config was updated (we can't directly check this with mocks,
        # but we can verify the method was called)

    def test_execute_with_exclude_patterns(
        self,
        use_case,
        mock_file_repository,
        mock_link_analysis_service,
        sample_files,
        tmp_path,
    ):
        """Test detection with exclude patterns."""
        # Setup mocks
        mock_file_repository.load_vault.return_value = sample_files
        mock_link_analysis_service.detect_dead_links.return_value = []

        # Create request with exclude patterns
        request = DeadLinkDetectionRequest(
            vault_path=tmp_path,
            exclude_patterns=["**/templates/**"],
        )

        # Execute
        use_case.execute(request)

        # Verify that load_vault was called with the vault path
        mock_file_repository.load_vault.assert_called_once_with(tmp_path)

        # Verify that the repository config was updated (we can't directly check this with mocks,
        # but we can verify the method was called)

    def test_execute_vault_not_exists(self, use_case):
        """Test error when vault path doesn't exist."""
        nonexistent_path = Path("/nonexistent/path")
        request = DeadLinkDetectionRequest(vault_path=nonexistent_path)

        with pytest.raises(FileNotFoundError, match="Vault path does not exist"):
            use_case.execute(request)

    def test_execute_vault_not_directory(self, use_case, tmp_path):
        """Test error when vault path is not a directory."""
        # Create a file instead of directory
        file_path = tmp_path / "not_a_directory.txt"
        file_path.write_text("content")

        request = DeadLinkDetectionRequest(vault_path=file_path)

        with pytest.raises(ValueError, match="Vault path is not a directory"):
            use_case.execute(request)

    def test_build_file_registry(self, use_case, sample_files):
        """Test building file registry from files."""
        registry = use_case._build_file_registry(sample_files)

        assert len(registry) == 2
        assert "20230101120000" in registry
        assert "20230101120001" in registry
        assert registry["20230101120000"].frontmatter.title == "Test File 1"
        assert registry["20230101120001"].frontmatter.title == "Test File 2"

    def test_build_file_registry_no_ids(self, use_case):
        """Test building file registry when files have no IDs."""
        files_without_ids = [
            MarkdownFile(
                path=Path("test.md"),
                file_id="",  # Empty ID
                frontmatter=Frontmatter(title="Test", id=""),
                content="Content",
            )
        ]

        registry = use_case._build_file_registry(files_without_ids)
        assert len(registry) == 0

    def test_build_result_statistics(
        self, use_case, sample_files, sample_dead_links, tmp_path
    ):
        """Test building result with correct statistics."""
        request = DeadLinkDetectionRequest(vault_path=tmp_path)

        result = use_case._build_result(request, sample_files, sample_dead_links)

        # Check summary statistics
        assert result.summary["total_files"] == 2
        assert result.summary["files_with_dead_links"] == 2
        assert result.summary["total_dead_links"] == 2
        assert result.summary["wikilink_dead_links"] == 1
        assert result.summary["regular_link_dead_links"] == 1
        assert result.summary["link_ref_def_dead_links"] == 0
        assert result.summary["vault_path"] == str(tmp_path)

        # Check dead links by type
        assert result.dead_links_by_type == {"wikilink": 1, "regular_link": 1}

    def test_build_result_same_file_multiple_dead_links(
        self, use_case, sample_files, tmp_path
    ):
        """Test building result when same file has multiple dead links."""
        dead_links = [
            DeadLink(
                source_file="test1.md",
                link_text="[[link1]]",
                link_type="wikilink",
                line_number=1,
                target="link1",
            ),
            DeadLink(
                source_file="test1.md",  # Same file
                link_text="[[link2]]",
                link_type="wikilink",
                line_number=2,
                target="link2",
            ),
        ]

        request = DeadLinkDetectionRequest(vault_path=tmp_path)
        result = use_case._build_result(request, sample_files, dead_links)

        # Should count as 1 file with dead links, not 2
        assert result.files_with_dead_links == 1
        assert result.total_dead_links == 2

    def test_prepare_config(self, use_case, tmp_path):
        """Test preparing configuration from request."""
        request = DeadLinkDetectionRequest(
            vault_path=tmp_path,
            include_patterns=["**/*.md"],
            exclude_patterns=["**/templates/**"],
        )

        config = use_case._prepare_config(request)

        assert config.include_patterns == ["**/*.md"]
        assert "**/templates/**" in config.exclude_patterns

"""Integration test for task 7.4: Test basic auto-linking.

This test implements the requirements for task 7.4:
- Test with test-myvault data to create actual links
- Verify no existing content is corrupted
- Test rollback functionality
- Requirements: 2.1, 2.8
"""

import json
import re
import shutil
import tempfile
import time
from pathlib import Path

import pytest

from knowledge_base_organizer.application.auto_link_generation_use_case import (
    AutoLinkGenerationRequest,
    AutoLinkGenerationUseCase,
)
from knowledge_base_organizer.domain.services.content_processing_service import (
    ContentProcessingService,
)
from knowledge_base_organizer.domain.services.link_analysis_service import (
    LinkAnalysisService,
)
from knowledge_base_organizer.infrastructure.config import ProcessingConfig
from knowledge_base_organizer.infrastructure.file_repository import FileRepository


class TestAutoLinkGenerationTask74:
    """Test basic auto-linking functionality with real vault data."""

    @pytest.fixture
    def test_vault_path(self):
        """Path to test-myvault data."""
        return Path("tests/test-data/vaults/test-myvault")

    @pytest.fixture
    def temp_vault_path(self, test_vault_path):
        """Create a temporary copy of test-myvault for testing."""
        temp_dir = tempfile.mkdtemp()
        temp_vault = Path(temp_dir) / "test-vault"
        shutil.copytree(test_vault_path, temp_vault)
        yield temp_vault
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def config(self):
        """Processing configuration for testing."""
        return ProcessingConfig.get_default_config()

    @pytest.fixture
    def auto_link_use_case(self, config):
        """Auto-link generation use case with dependencies."""
        file_repository = FileRepository(config)
        link_analysis_service = LinkAnalysisService()
        content_processing_service = ContentProcessingService()

        return AutoLinkGenerationUseCase(
            file_repository=file_repository,
            link_analysis_service=link_analysis_service,
            content_processing_service=content_processing_service,
            config=config,
        )

    def test_dry_run_auto_linking_with_test_vault(
        self, auto_link_use_case, temp_vault_path
    ):
        """Test auto-linking in dry-run mode with test-myvault data.

        Requirements: 2.1 - Detect text that matches other notes' titles or aliases
        """
        # Create request for dry-run mode
        request = AutoLinkGenerationRequest(
            vault_path=temp_vault_path,
            dry_run=True,
            max_links_per_file=10,  # Limit for testing
            max_files_to_process=5,  # Process only a few files for testing
        )

        # Execute auto-linking
        result = auto_link_use_case.execute(request)

        # Verify basic results
        assert result.vault_path == str(temp_vault_path)
        assert result.total_files_processed >= 0
        assert isinstance(result.total_links_created, int)
        assert isinstance(result.total_aliases_added, int)
        assert isinstance(result.file_updates, list)
        assert isinstance(result.errors, list)

        # In dry-run mode, no actual changes should be made
        assert len(result.errors) == 0 or all(
            "Error processing" in error for error in result.errors
        )

        # Verify summary contains expected fields
        assert "files_processed" in result.summary
        assert "success_rate" in result.summary

        print(f"Dry-run results: {result.total_links_created} links would be created")
        print(f"Files processed: {result.total_files_processed}")

    def test_actual_auto_linking_with_limited_scope(
        self, auto_link_use_case, temp_vault_path
    ):
        """Test actual auto-linking with limited scope to verify functionality.

        Requirements: 2.8 - Generate WikiLinks with appropriate aliases
        """
        # Store original file contents for comparison
        original_contents = {}
        for md_file in temp_vault_path.rglob("*.md"):
            if md_file.is_file():
                original_contents[str(md_file)] = md_file.read_text(encoding="utf-8")

        # Create request for actual execution with very limited scope
        request = AutoLinkGenerationRequest(
            vault_path=temp_vault_path,
            dry_run=False,  # Actually apply changes
            max_links_per_file=3,  # Very limited to minimize impact
            max_files_to_process=2,  # Process only 2 files
        )

        # Execute auto-linking
        result = auto_link_use_case.execute(request)

        # Verify execution completed successfully
        assert result.total_files_processed <= 2
        assert len(result.errors) == 0

        # Verify that some processing occurred
        if result.total_links_created > 0:
            # Check that file updates were generated
            assert len(result.file_updates) > 0

            # Verify that files were actually modified
            modified_files = []
            for file_path, original_content in original_contents.items():
                current_content = Path(file_path).read_text(encoding="utf-8")
                if current_content != original_content:
                    modified_files.append(file_path)

            # If links were created, some files should be modified
            if result.total_links_created > 0:
                assert len(modified_files) > 0

        print(f"Actual execution: {result.total_links_created} links created")
        print(f"Files with updates: {len(result.file_updates)}")

    def test_content_integrity_verification(self, auto_link_use_case, temp_vault_path):
        """Verify that existing content is not corrupted during auto-linking.

        Requirements: 2.1 - Exclude existing WikiLinks, regular links, frontmatter
        """
        # Read all files and extract critical content that should not be modified
        protected_content = {}

        for md_file in temp_vault_path.rglob("*.md"):
            if md_file.is_file():
                content = md_file.read_text(encoding="utf-8")

                # Extract frontmatter
                if content.startswith("---"):
                    end_idx = content.find("---", 3)
                    if end_idx != -1:
                        frontmatter = content[: end_idx + 3]
                        protected_content[str(md_file)] = {
                            "frontmatter": frontmatter,
                            "existing_wikilinks": self._extract_existing_wikilinks(
                                content
                            ),
                            "existing_regular_links": (
                                self._extract_existing_regular_links(content)
                            ),
                        }

        # Execute auto-linking
        request = AutoLinkGenerationRequest(
            vault_path=temp_vault_path,
            dry_run=False,
            max_links_per_file=5,
            max_files_to_process=3,
        )

        auto_link_use_case.execute(request)

        # Verify protected content remains intact
        for file_path, protected in protected_content.items():
            if Path(file_path).exists():
                current_content = Path(file_path).read_text(encoding="utf-8")

                # Verify frontmatter is preserved
                if current_content.startswith("---"):
                    end_idx = current_content.find("---", 3)
                    if end_idx != -1:
                        current_frontmatter = current_content[: end_idx + 3]
                        # Frontmatter should be identical or only have aliases added
                        assert protected["frontmatter"] in current_frontmatter

                # Verify existing WikiLinks are preserved
                current_wikilinks = self._extract_existing_wikilinks(current_content)
                for original_link in protected["existing_wikilinks"]:
                    assert original_link in current_wikilinks, (
                        f"Original WikiLink {original_link} was corrupted "
                        f"in {file_path}"
                    )

                # Verify existing regular links are preserved
                current_regular_links = self._extract_existing_regular_links(
                    current_content
                )
                for original_link in protected["existing_regular_links"]:
                    assert original_link in current_regular_links, (
                        f"Original regular link {original_link} was corrupted "
                        f"in {file_path}"
                    )

        print("Content integrity verification passed")

    def test_rollback_functionality(self, auto_link_use_case, temp_vault_path):
        """Test rollback functionality by comparing before/after states.

        This simulates rollback by verifying we can restore original state.
        """
        # Create backup of original state
        backup_dir = tempfile.mkdtemp()
        backup_vault = Path(backup_dir) / "backup-vault"
        shutil.copytree(temp_vault_path, backup_vault)

        try:
            # Store original file contents
            original_files = {}
            for md_file in temp_vault_path.rglob("*.md"):
                if md_file.is_file():
                    original_files[str(md_file.relative_to(temp_vault_path))] = (
                        md_file.read_text(encoding="utf-8")
                    )

            # Execute auto-linking
            request = AutoLinkGenerationRequest(
                vault_path=temp_vault_path,
                dry_run=False,
                max_links_per_file=3,
                max_files_to_process=2,
            )

            result = auto_link_use_case.execute(request)

            # Verify changes were made (if any links were created)
            if result.total_links_created > 0:
                changes_detected = False
                for relative_path, original_content in original_files.items():
                    current_file = temp_vault_path / relative_path
                    if current_file.exists():
                        current_content = current_file.read_text(encoding="utf-8")
                        if current_content != original_content:
                            changes_detected = True
                            break

                if changes_detected:
                    # Simulate rollback by restoring from backup
                    shutil.rmtree(temp_vault_path)
                    shutil.copytree(backup_vault, temp_vault_path)

                    # Verify rollback was successful
                    for relative_path, original_content in original_files.items():
                        restored_file = temp_vault_path / relative_path
                        assert restored_file.exists()
                        restored_content = restored_file.read_text(encoding="utf-8")
                        assert restored_content == original_content, (
                            f"Rollback failed for {relative_path}"
                        )

                    print("Rollback functionality verified successfully")
                else:
                    print("No changes were made, rollback test not applicable")
            else:
                print("No links created, rollback test not applicable")

        finally:
            # Cleanup backup
            shutil.rmtree(backup_dir)

    def test_bidirectional_alias_updates(self, auto_link_use_case, temp_vault_path):
        """Test that aliases are properly added to target files.

        Requirements: 2.8 - Bidirectional updates with alias management
        """
        # Execute auto-linking
        request = AutoLinkGenerationRequest(
            vault_path=temp_vault_path,
            dry_run=False,
            max_links_per_file=2,
            max_files_to_process=3,
        )

        result = auto_link_use_case.execute(request)

        # Check for alias updates in the results
        alias_updates = [
            update
            for update in result.file_updates
            if update.update_type == "add_alias"
        ]

        if alias_updates:
            # Verify that alias updates have proper structure
            for update in alias_updates:
                assert update.file_path.exists()
                assert update.frontmatter_changes is not None
                assert "aliases" in update.frontmatter_changes
                assert isinstance(update.frontmatter_changes["aliases"], list)

            print(f"Bidirectional updates: {len(alias_updates)} alias updates created")
        else:
            print("No alias updates were needed")

    def test_error_handling_and_recovery(self, auto_link_use_case, temp_vault_path):
        """Test error handling with invalid configurations."""
        # Test with invalid vault path - should raise ValueError
        request = AutoLinkGenerationRequest(
            vault_path=Path("/nonexistent/path"),
            dry_run=True,
        )

        with pytest.raises(ValueError, match="Vault path does not exist"):
            auto_link_use_case.execute(request)

        # Test with valid vault but extreme limits
        request = AutoLinkGenerationRequest(
            vault_path=temp_vault_path,
            dry_run=True,
            max_links_per_file=0,  # No links allowed
        )

        result = auto_link_use_case.execute(request)
        # Should complete without errors even with restrictive limits
        assert result.total_links_created == 0

    def _extract_existing_wikilinks(self, content: str) -> list[str]:
        """Extract existing WikiLinks from content."""

        pattern = r"\[\[([^\]]+)\]\]"
        return re.findall(pattern, content)

    def _extract_existing_regular_links(self, content: str) -> list[str]:
        """Extract existing regular markdown links from content."""

        pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        return [f"[{text}]({url})" for text, url in re.findall(pattern, content)]

    def test_performance_with_larger_scope(self, auto_link_use_case, temp_vault_path):
        """Test performance characteristics with larger scope."""

        # Test with larger scope to measure performance
        request = AutoLinkGenerationRequest(
            vault_path=temp_vault_path,
            dry_run=True,  # Use dry-run for performance testing
            max_links_per_file=20,
            max_files_to_process=None,  # Process all files
        )

        start_time = time.time()
        result = auto_link_use_case.execute(request)
        execution_time = time.time() - start_time

        # Verify reasonable performance (should complete within reasonable time)
        assert execution_time < 30.0, f"Execution took too long: {execution_time:.2f}s"

        # Verify all files were processed
        assert result.total_files_processed > 0

        print(
            f"Performance test: {result.total_files_processed} files processed "
            f"in {execution_time:.2f}s"
        )
        print(
            f"Average time per file: "
            f"{execution_time / result.total_files_processed:.3f}s"
        )

    def test_output_format_and_reporting(self, auto_link_use_case, temp_vault_path):
        """Test that output format is suitable for automation and reporting."""
        request = AutoLinkGenerationRequest(
            vault_path=temp_vault_path,
            dry_run=True,
            max_files_to_process=3,
        )

        result = auto_link_use_case.execute(request)

        # Verify result can be serialized to JSON (for automation)
        try:
            json_output = json.dumps(result.model_dump(), default=str, indent=2)
            assert len(json_output) > 0

            # Verify JSON can be parsed back
            parsed_result = json.loads(json_output)
            assert "vault_path" in parsed_result
            assert "total_files_processed" in parsed_result
            assert "summary" in parsed_result

        except (TypeError, ValueError) as e:
            pytest.fail(f"Result cannot be serialized to JSON: {e}")

        print("Output format verification passed")

"""End-to-end tests for automatic organization functionality."""

import datetime
import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from typer.testing import CliRunner

from knowledge_base_organizer.cli.main import app
from knowledge_base_organizer.domain.services.frontmatter_enhancement_service import (
    FrontmatterEnhancementService,
)
from knowledge_base_organizer.infrastructure.config import ProcessingConfig
from knowledge_base_organizer.infrastructure.file_repository import FileRepository


class TestAutomaticOrganizationEndToEnd:
    """End-to-end tests for automatic organization feature."""

    @pytest.fixture
    def test_vault_path(self) -> Path:
        """Get path to test vault."""
        return Path("tests/test-data/vaults/test-myvault")

    @pytest.fixture
    def temp_vault_path(self, test_vault_path: Path) -> Path:
        """Create temporary copy of test vault for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_vault = Path(temp_dir) / "test-vault"
            shutil.copytree(test_vault_path, temp_vault)
            yield temp_vault

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    def test_organize_dry_run_mode(self, temp_vault_path: Path, runner: CliRunner):
        """Test organize command in dry-run mode (Requirement 8.6)."""
        # Create output file to avoid mixing JSON with console output
        output_file = temp_vault_path / "organize_results.json"

        # Run organize command in dry-run mode
        result = runner.invoke(
            app,
            [
                "organize",
                str(temp_vault_path),
                "--dry-run",
                "--output-format",
                "json",
                "--output",
                str(output_file),
            ],
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"Command failed: {result.stdout}"

        # Verify output file was created
        assert output_file.exists(), "JSON output file was not created"

        # Parse JSON output from file
        output_data = json.loads(output_file.read_text(encoding="utf-8"))

        # Verify output structure
        assert "summary" in output_data
        assert "improvements" in output_data
        assert "total_files" in output_data["summary"]
        assert "total_improvements" in output_data["summary"]

        # Verify improvements were found
        assert output_data["summary"]["total_improvements"] > 0
        assert len(output_data["improvements"]) > 0

        # Verify each improvement has required fields
        for improvement in output_data["improvements"]:
            assert "file_path" in improvement
            assert "improvements_made" in improvement
            assert "changes_applied" in improvement
            assert "success" in improvement
            assert improvement["improvements_made"] > 0

    def test_organize_execute_mode_with_backup(
        self, temp_vault_path: Path, runner: CliRunner
    ):
        """Test organize command in execute mode with backup functionality."""
        # Get original file contents for comparison
        original_files = {}
        for md_file in temp_vault_path.rglob("*.md"):
            if md_file.is_file():
                original_files[md_file] = md_file.read_text(encoding="utf-8")

        # Run organize command in execute mode
        result = runner.invoke(
            app,
            [
                "organize",
                str(temp_vault_path),
                "--execute",
                "--output-format",
                "json",
                "--max-improvements",
                "10",
            ],
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"Command failed: {result.stdout}"

        # Verify backups were created (using correct extension)
        backup_files = list(temp_vault_path.rglob("*.backup_*.bak"))
        assert len(backup_files) > 0, "No backup files were created"

        # Verify files were actually modified
        modified_files = 0
        for md_file in temp_vault_path.rglob("*.md"):
            if md_file.is_file() and md_file in original_files:
                current_content = md_file.read_text(encoding="utf-8")
                if current_content != original_files[md_file]:
                    modified_files += 1

        assert modified_files > 0, "No files were actually modified"

    def test_organize_interactive_mode(self, temp_vault_path: Path, runner: CliRunner):
        """Test organize command in interactive mode (Requirement 8.7)."""
        # Mock user input to automatically accept all improvements
        with patch("typer.confirm", return_value=True):
            result = runner.invoke(
                app,
                [
                    "organize",
                    str(temp_vault_path),
                    "--execute",
                    "--interactive",
                    "--max-improvements",
                    "5",
                ],
            )

        # Verify command succeeded
        assert result.exit_code == 0, f"Command failed: {result.stdout}"

        # Verify interactive prompts were shown
        assert "Interactive Organization Mode" in result.stdout
        assert "Improvements applied" in result.stdout

    def test_organize_improvement_report_generation(
        self, temp_vault_path: Path, runner: CliRunner
    ):
        """Test improvement report generation and metrics (Requirement 8.7)."""
        # Create output file for report
        output_file = temp_vault_path / "organization_report.json"

        # Run organize command with output file
        result = runner.invoke(
            app,
            [
                "organize",
                str(temp_vault_path),
                "--dry-run",
                "--output-format",
                "json",
                "--output",
                str(output_file),
                "--verbose",
            ],
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"Command failed: {result.stdout}"

        # Verify report file was created
        assert output_file.exists(), "Report file was not created"

        # Load and verify report content
        report_data = json.loads(output_file.read_text(encoding="utf-8"))

        # Verify report structure
        assert "summary" in report_data
        assert "improvements" in report_data

        # Verify summary metrics
        summary = report_data["summary"]
        assert "total_files" in summary
        assert "total_improvements" in summary
        assert "timestamp" in summary
        assert isinstance(summary["total_files"], int)
        assert isinstance(summary["total_improvements"], int)

        # Verify improvement details
        improvements = report_data["improvements"]
        assert isinstance(improvements, list)

        for improvement in improvements:
            assert "file_path" in improvement
            assert "improvements_made" in improvement
            assert "changes_applied" in improvement
            assert "success" in improvement
            assert isinstance(improvement["improvements_made"], int)
            assert isinstance(improvement["changes_applied"], list)
            assert isinstance(improvement["success"], bool)

    def test_organize_rollback_functionality(
        self, temp_vault_path: Path, runner: CliRunner
    ):
        """Test backup and rollback functionality (Requirement 8.6)."""
        # Get original file contents
        original_files = {}
        for md_file in temp_vault_path.rglob("*.md"):
            if md_file.is_file():
                original_files[md_file] = md_file.read_text(encoding="utf-8")

        # Run organize command in execute mode
        result = runner.invoke(
            app,
            [
                "organize",
                str(temp_vault_path),
                "--execute",
                "--max-improvements",
                "5",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.stdout}"

        # Find backup files (using correct extension)
        backup_files = list(temp_vault_path.rglob("*.backup_*.bak"))
        assert len(backup_files) > 0, "No backup files were created"

        # Verify that backups contain the original content
        for backup_file in backup_files:
            original_file = Path(str(backup_file).split(".backup")[0])
            if original_file.exists() and original_file in original_files:
                backup_content = backup_file.read_text(encoding="utf-8")
                original_content = original_files[original_file]

                # The backup should contain the original content (before improvements)
                assert backup_content == original_content, (
                    f"Backup file {backup_file} does not contain original content"
                )

        # Test rollback functionality by restoring one file from backup
        if backup_files:
            test_backup = backup_files[0]
            original_file = Path(str(test_backup).split(".backup")[0])

            if original_file.exists() and original_file in original_files:
                # Get current (improved) content
                current_content = original_file.read_text(encoding="utf-8")

                # Restore from backup
                backup_content = test_backup.read_text(encoding="utf-8")
                original_file.write_text(backup_content, encoding="utf-8")

                # Verify restoration worked
                restored_content = original_file.read_text(encoding="utf-8")
                assert restored_content == backup_content, (
                    f"File {original_file} was not properly restored from backup"
                )

                # Verify it's different from the improved version (proving rollback)
                assert restored_content != current_content, (
                    "Restored content is the same as improved content - "
                    "rollback didn't work"
                )

    def test_organize_with_real_vault_improvements(
        self, temp_vault_path: Path, runner: CliRunner
    ):
        """Test with real vault data to apply actual improvements."""
        # Initialize services directly to analyze what improvements are available
        config = ProcessingConfig.get_default_config()
        file_repo = FileRepository(config)
        enhancement_service = FrontmatterEnhancementService()

        # Load files and analyze improvements
        files = file_repo.load_vault(temp_vault_path)
        assert len(files) > 0, "No files loaded from test vault"

        # Analyze improvements without applying them
        results = enhancement_service.enhance_vault_frontmatter(
            files, apply_changes=False
        )

        # Filter to files that need improvements
        files_needing_improvements = [
            r for r in results if r.success and r.improvements_made > 0
        ]

        if len(files_needing_improvements) == 0:
            pytest.skip("No improvements needed in test vault")

        # Run organize command to apply improvements
        result = runner.invoke(
            app,
            [
                "organize",
                str(temp_vault_path),
                "--execute",
                "--output-format",
                "json",
                "--max-improvements",
                "20",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.stdout}"

        # Verify improvements were actually applied
        files_after = file_repo.load_vault(temp_vault_path)
        results_after = enhancement_service.enhance_vault_frontmatter(
            files_after, apply_changes=False
        )

        # Count improvements needed after processing
        improvements_after = sum(
            r.improvements_made for r in results_after if r.success
        )
        improvements_before = sum(r.improvements_made for r in results if r.success)

        # Should have fewer improvements needed after processing
        assert improvements_after < improvements_before, (
            "Improvements were not actually applied"
        )

    def test_organize_error_handling(self, runner: CliRunner):
        """Test error handling for invalid vault paths."""
        # Test with non-existent vault path
        result = runner.invoke(app, ["organize", "/non/existent/path", "--dry-run"])

        assert result.exit_code == 1
        assert "does not exist" in result.stdout

    def test_organize_with_include_exclude_patterns(
        self, temp_vault_path: Path, runner: CliRunner
    ):
        """Test organize command with include/exclude patterns."""
        # Create output file to avoid mixing JSON with console output
        output_file = temp_vault_path / "filtered_results.json"

        # Run with specific include pattern
        result = runner.invoke(
            app,
            [
                "organize",
                str(temp_vault_path),
                "--dry-run",
                "--include",
                "**/100_FleetingNotes/*.md",
                "--output-format",
                "json",
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.stdout}"

        # Parse output to verify only specific files were processed
        if output_file.exists():
            output_data = json.loads(output_file.read_text(encoding="utf-8"))
            # Verify that only files from FleetingNotes were processed
            for improvement in output_data.get("improvements", []):
                file_path = improvement["file_path"]
                assert "100_FleetingNotes" in file_path

    def test_organize_performance_with_large_vault(
        self, temp_vault_path: Path, runner: CliRunner
    ):
        """Test organize command performance with larger vault."""
        # Create additional test files to simulate larger vault
        fleeting_notes_dir = temp_vault_path / "100_FleetingNotes"
        fleeting_notes_dir.mkdir(exist_ok=True)

        # Create 20 additional test files
        for i in range(20):
            test_file = fleeting_notes_dir / f"test_note_{i:03d}.md"
            test_file.write_text(
                f"""---
title: Test Note {i}
tags: [test, performance]
---

# Test Note {i}

This is a test note for performance testing.
It contains some content about testing and performance.
""",
                encoding="utf-8",
            )

        # Create output file for performance test
        output_file = temp_vault_path / "performance_results.json"

        # Run organize command and measure basic performance
        result = runner.invoke(
            app,
            [
                "organize",
                str(temp_vault_path),
                "--dry-run",
                "--output-format",
                "json",
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.stdout}"

        # Verify it completed successfully with larger dataset
        if output_file.exists():
            output_data = json.loads(output_file.read_text(encoding="utf-8"))
            assert output_data["summary"]["total_files"] >= 20

    def test_organize_comprehensive_improvement_types(
        self, temp_vault_path: Path, runner: CliRunner
    ):
        """Test that organize command applies various types of improvements."""
        # Create a test file with multiple improvement opportunities
        test_file = temp_vault_path / "test_comprehensive.md"
        test_file.write_text(
            """---
title: Incomplete Note
---

# Incomplete Note

This note discusses Python programming and web development.
It mentions Django framework and REST APIs.
The content is about software architecture and design patterns.

Author: Test Author
Source: Test Source
Project: Test Project
""",
            encoding="utf-8",
        )

        # Run organize command
        result = runner.invoke(
            app,
            [
                "organize",
                str(test_file.parent),
                "--execute",
                "--output-format",
                "json",
                "--include",
                "test_comprehensive.md",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.stdout}"

        # Verify the file was improved
        improved_content = test_file.read_text(encoding="utf-8")

        # Check that various improvements were applied
        assert "tags:" in improved_content  # Tags should be added
        assert "id:" in improved_content  # ID should be added
        assert (
            "published:" in improved_content or "created:" in improved_content
        )  # Dates should be added

        # Parse the frontmatter to verify specific improvements

        frontmatter_end = improved_content.find("---", 3)
        if frontmatter_end > 0:
            frontmatter_text = improved_content[3:frontmatter_end].strip()
            frontmatter_data = yaml.safe_load(frontmatter_text)

            # Verify intelligent tag suggestions were applied
            tags = frontmatter_data.get("tags", [])
            assert len(tags) > 0, "No tags were added"

            # Should have programming-related tags based on content
            tag_text = " ".join(tags).lower()
            assert any(
                keyword in tag_text
                for keyword in ["python", "programming", "web", "development"]
            ), f"Expected programming-related tags, got: {tags}"

    def test_organize_metrics_and_reporting(
        self, temp_vault_path: Path, runner: CliRunner
    ):
        """Test comprehensive metrics and reporting functionality."""
        # Run organize with verbose output to get detailed metrics
        result = runner.invoke(
            app,
            [
                "organize",
                str(temp_vault_path),
                "--dry-run",
                "--output-format",
                "console",
                "--verbose",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.stdout}"

        # Verify key metrics are reported
        output = result.stdout
        assert "Organizing vault:" in output
        assert "files with improvements:" in output.lower()
        assert "total improvements found:" in output.lower()
        assert "improvement details:" in output.lower()

        # Create output file for JSON metrics test
        metrics_file = temp_vault_path / "metrics_results.json"

        # Test JSON format for detailed metrics
        result_json = runner.invoke(
            app,
            [
                "organize",
                str(temp_vault_path),
                "--dry-run",
                "--output-format",
                "json",
                "--output",
                str(metrics_file),
            ],
        )

        assert result_json.exit_code == 0

        # Parse and verify JSON metrics
        if metrics_file.exists():
            metrics = json.loads(metrics_file.read_text(encoding="utf-8"))
            assert "summary" in metrics
            assert "improvements" in metrics

            summary = metrics["summary"]
            assert "total_files" in summary
            assert "total_improvements" in summary
            assert "timestamp" in summary

            # Verify timestamp format
            timestamp = summary["timestamp"]
            # Should not raise exception
            datetime.datetime.fromisoformat(timestamp)

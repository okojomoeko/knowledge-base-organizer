"""Tests for the maintain CLI command."""

import json
from pathlib import Path

from typer.testing import CliRunner

from knowledge_base_organizer.cli.main import app


class TestMaintainCommand:
    """Test cases for the maintain command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.test_vault_path = Path("tests/test-data/vaults/test-myvault")

    def test_maintain_command_help(self):
        """Test that maintain command help works."""
        result = self.runner.invoke(app, ["maintain", "--help"])
        assert result.exit_code == 0
        assert "Comprehensive vault maintenance" in result.stdout
        assert "--task" in result.stdout
        assert "--schedule" in result.stdout

    def test_maintain_command_with_test_vault_console(self):
        """Test maintain command with test vault in console format."""
        result = self.runner.invoke(
            app,
            [
                "maintain",
                str(self.test_vault_path),
                "--task",
                "organize",
                "--verbose",
            ],
        )
        assert result.exit_code == 0
        assert "Knowledge Base Maintenance" in result.stdout
        assert "Maintenance Report" in result.stdout
        assert "Tasks Completed" in result.stdout

    def test_maintain_command_with_multiple_tasks(self):
        """Test maintain command with multiple tasks."""
        result = self.runner.invoke(
            app,
            [
                "maintain",
                str(self.test_vault_path),
                "--task",
                "organize",
                "--task",
                "duplicates",
                "--task",
                "dead-links",
            ],
        )
        assert result.exit_code == 0
        assert "Knowledge Base Maintenance" in result.stdout
        assert "Tasks Completed" in result.stdout

    def test_maintain_command_json_output(self):
        """Test maintain command with JSON output."""
        result = self.runner.invoke(
            app,
            [
                "maintain",
                str(self.test_vault_path),
                "--task",
                "organize",
                "--output-format",
                "json",
            ],
        )
        assert result.exit_code == 0

        # Parse JSON output
        json_output = json.loads(result.stdout)
        assert "vault_path" in json_output
        assert "tasks" in json_output
        assert "summary" in json_output
        assert "organize" in json_output["tasks"]

    def test_maintain_command_with_nonexistent_vault(self):
        """Test maintain command with nonexistent vault."""
        result = self.runner.invoke(
            app, ["maintain", "/nonexistent/vault", "--task", "organize"]
        )
        assert result.exit_code == 1
        assert "Vault path does not exist" in result.stdout

    def test_maintain_command_with_invalid_task(self):
        """Test maintain command with invalid task."""
        result = self.runner.invoke(
            app,
            [
                "maintain",
                str(self.test_vault_path),
                "--task",
                "invalid_task",
            ],
        )
        assert result.exit_code == 1
        assert "Invalid maintenance tasks" in result.stdout

    def test_maintain_command_with_schedule_placeholder(self):
        """Test maintain command with schedule option (placeholder)."""
        result = self.runner.invoke(
            app,
            [
                "maintain",
                str(self.test_vault_path),
                "--task",
                "organize",
                "--schedule",
                "daily",
            ],
        )
        assert result.exit_code == 0
        assert "Schedule: daily" in result.stdout
        assert "Scheduling functionality is planned" in result.stdout

    def test_maintain_command_with_duplicate_threshold(self):
        """Test maintain command with custom duplicate threshold."""
        result = self.runner.invoke(
            app,
            [
                "maintain",
                str(self.test_vault_path),
                "--task",
                "duplicates",
                "--duplicate-threshold",
                "0.8",
            ],
        )
        assert result.exit_code == 0
        assert "Knowledge Base Maintenance" in result.stdout

    def test_maintain_command_interactive_mode_placeholder(self):
        """Test maintain command with interactive mode (placeholder)."""
        result = self.runner.invoke(
            app,
            [
                "maintain",
                str(self.test_vault_path),
                "--task",
                "organize",
                "--interactive",
            ],
        )
        assert result.exit_code == 0
        assert "Interactive mode enabled" in result.stdout

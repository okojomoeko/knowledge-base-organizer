"""Tests for the validate-frontmatter command functionality."""

from typer.testing import CliRunner

from knowledge_base_organizer.cli.main import app


class TestValidateFrontmatterCommand:
    """Test the validate-frontmatter CLI command."""

    def test_validate_frontmatter_command_help(self) -> None:
        """Test that validate-frontmatter command help works."""
        runner = CliRunner()
        result = runner.invoke(app, ["validate-frontmatter", "--help"])
        assert result.exit_code == 0
        assert (
            "Validate and fix frontmatter according to template schemas"
            in result.stdout
        )

    def test_validate_frontmatter_command_with_test_vault_console(self) -> None:
        """Test validate-frontmatter command with test vault in console format."""
        runner = CliRunner()
        vault_path = "tests/test-data/vaults/test-myvault"

        result = runner.invoke(app, ["validate-frontmatter", vault_path, "--dry-run"])

        # Should succeed despite warnings
        assert result.exit_code == 0
        assert "Frontmatter Validation Results" in result.stdout
        assert "Total files:" in result.stdout
        assert "Valid files:" in result.stdout
        assert "Invalid files:" in result.stdout

    def test_validate_frontmatter_command_with_nonexistent_vault(self) -> None:
        """Test validate-frontmatter command with nonexistent vault."""
        runner = CliRunner()
        vault_path = "nonexistent/vault/path"

        result = runner.invoke(app, ["validate-frontmatter", vault_path])

        # Should fail with exit code 1
        assert result.exit_code == 1
        assert "Vault path does not exist" in result.stdout

    def test_validate_frontmatter_command_with_template_filter(self) -> None:
        """Test validate-frontmatter command with specific template filter."""
        runner = CliRunner()
        vault_path = "tests/test-data/vaults/test-myvault"

        result = runner.invoke(
            app,
            [
                "validate-frontmatter",
                vault_path,
                "--template",
                "new-fleeing-note",
                "--dry-run",
            ],
        )

        # Should succeed
        assert result.exit_code == 0
        assert "Frontmatter Validation Results" in result.stdout

    def test_validate_frontmatter_command_verbose(self) -> None:
        """Test validate-frontmatter command with verbose output."""
        runner = CliRunner()
        vault_path = "tests/test-data/vaults/test-myvault"

        result = runner.invoke(
            app, ["validate-frontmatter", vault_path, "--verbose", "--dry-run"]
        )

        # Should succeed and show verbose output
        assert result.exit_code == 0
        assert "Validating frontmatter in:" in result.stdout
        assert "Mode: dry-run" in result.stdout

    def test_validate_frontmatter_command_with_include_patterns(self) -> None:
        """Test validate-frontmatter command with include patterns."""
        runner = CliRunner()
        vault_path = "tests/test-data/vaults/test-myvault"

        result = runner.invoke(
            app,
            [
                "validate-frontmatter",
                vault_path,
                "--include",
                "*.md",
                "--dry-run",
            ],
        )

        # Should succeed
        assert result.exit_code == 0
        assert "Frontmatter Validation Results" in result.stdout

    def test_validate_frontmatter_command_with_exclude_patterns(self) -> None:
        """Test validate-frontmatter command with exclude patterns."""
        runner = CliRunner()
        vault_path = "tests/test-data/vaults/test-myvault"

        result = runner.invoke(
            app,
            [
                "validate-frontmatter",
                vault_path,
                "--exclude",
                "template*",
                "--dry-run",
            ],
        )

        # Should succeed
        assert result.exit_code == 0
        assert "Frontmatter Validation Results" in result.stdout

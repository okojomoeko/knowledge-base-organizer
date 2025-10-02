"""Tests for the analyze command functionality."""

import json

from typer.testing import CliRunner

from knowledge_base_organizer.cli.main import app


class TestAnalyzeCommand:
    """Test the analyze CLI command."""

    def test_analyze_command_help(self):
        """Test that analyze command help works."""
        runner = CliRunner()
        result = runner.invoke(app, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "Analyze vault and report basic statistics" in result.stdout

    def test_analyze_command_with_test_vault_json(self):
        """Test analyze command with test vault in JSON format."""
        runner = CliRunner()
        vault_path = "tests/test-data/vaults/test-myvault"

        result = runner.invoke(app, ["analyze", vault_path, "--output-format", "json"])

        # Should succeed despite warnings
        assert result.exit_code == 0

        # Extract JSON from output (skip warning lines)
        output_lines = result.stdout.strip().split("\n")
        json_lines = []
        in_json = False

        for line in output_lines:
            if line.strip().startswith("{"):
                in_json = True
            if in_json:
                json_lines.append(line)

        json_output = "\n".join(json_lines)

        # Parse and validate JSON structure
        analysis_result = json.loads(json_output)

        # Validate structure
        assert "vault_path" in analysis_result
        assert "analysis_timestamp" in analysis_result
        assert "file_statistics" in analysis_result
        assert "frontmatter_statistics" in analysis_result
        assert "link_statistics" in analysis_result
        assert "content_statistics" in analysis_result

        # Validate file statistics
        file_stats = analysis_result["file_statistics"]
        assert file_stats["total_files"] > 0
        assert "files_with_frontmatter" in file_stats
        assert "files_with_id" in file_stats
        assert "files_by_extension" in file_stats

        # Validate frontmatter statistics
        fm_stats = analysis_result["frontmatter_statistics"]
        assert "field_distribution" in fm_stats
        assert "most_common_fields" in fm_stats
        assert "total_unique_fields" in fm_stats

        # Validate link statistics
        link_stats = analysis_result["link_statistics"]
        assert "wiki_links" in link_stats
        assert "regular_links" in link_stats
        assert "link_reference_definitions" in link_stats
        assert "total_links" in link_stats

    def test_analyze_command_with_test_vault_console(self):
        """Test analyze command with test vault in console format."""
        runner = CliRunner()
        vault_path = "tests/test-data/vaults/test-myvault"

        result = runner.invoke(
            app, ["analyze", vault_path, "--output-format", "console"]
        )

        # Should succeed despite warnings
        assert result.exit_code == 0

        # Check for expected console output sections
        assert "📊 Vault Analysis Results" in result.stdout
        assert "📁 File Statistics" in result.stdout
        assert "📋 Frontmatter Statistics" in result.stdout
        assert "🔗 Link Statistics" in result.stdout
        assert "📝 Content Statistics" in result.stdout

    def test_analyze_command_with_nonexistent_vault(self):
        """Test analyze command with nonexistent vault."""
        runner = CliRunner()
        vault_path = "nonexistent/vault/path"

        result = runner.invoke(app, ["analyze", vault_path])

        # Should fail with exit code 1
        assert result.exit_code == 1
        assert "Error:" in result.stdout

    def test_analyze_command_with_include_patterns(self):
        """Test analyze command with include patterns."""
        runner = CliRunner()
        vault_path = "tests/test-data/vaults/test-myvault"

        result = runner.invoke(
            app, ["analyze", vault_path, "--include", "*.md", "--output-format", "json"]
        )

        # Should succeed
        assert result.exit_code == 0

    def test_analyze_command_with_exclude_patterns(self):
        """Test analyze command with exclude patterns."""
        runner = CliRunner()
        vault_path = "tests/test-data/vaults/test-myvault"

        result = runner.invoke(
            app,
            [
                "analyze",
                vault_path,
                "--exclude",
                "template*",
                "--output-format",
                "json",
            ],
        )

        # Should succeed
        assert result.exit_code == 0

    def test_analyze_command_verbose(self):
        """Test analyze command with verbose output."""
        runner = CliRunner()
        vault_path = "tests/test-data/vaults/test-myvault"

        result = runner.invoke(
            app, ["analyze", vault_path, "--verbose", "--output-format", "console"]
        )

        # Should succeed and show verbose output
        assert result.exit_code == 0
        assert "Analyzing vault:" in result.stdout
        assert "Vault analysis completed" in result.stdout

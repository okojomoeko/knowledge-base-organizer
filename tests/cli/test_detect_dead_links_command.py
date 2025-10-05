"""Tests for the detect-dead-links command functionality."""

from typer.testing import CliRunner

from knowledge_base_organizer.cli.main import app

from .test_utils import cleanup_test_files, extract_json_from_cli_output


class TestDetectDeadLinksCommand:
    """Test the detect-dead-links CLI command."""

    def setup_method(self) -> None:
        """各テストメソッドの前に実行される"""
        cleanup_test_files("test_*.json")
        cleanup_test_files("test_*.csv")

    def teardown_method(self) -> None:
        """各テストメソッドの後に実行される"""
        cleanup_test_files("test_*.json")
        cleanup_test_files("test_*.csv")

    def test_detect_dead_links_command_help(self) -> None:
        """Test that detect-dead-links command help works."""
        runner = CliRunner()
        result = runner.invoke(app, ["detect-dead-links", "--help"])
        assert result.exit_code == 0
        assert "Detect and report dead WikiLinks and regular links" in result.stdout
        assert "--link-type" in result.stdout
        assert "--sort-by" in result.stdout
        assert "--limit" in result.stdout
        assert "--only-with-suggestions" in result.stdout

    def test_detect_dead_links_basic_functionality(self) -> None:
        """Test basic dead link detection functionality."""
        runner = CliRunner()
        vault_path = "tests/test-data/vaults/test-myvault"

        result = runner.invoke(app, ["detect-dead-links", vault_path])

        # Should succeed despite warnings
        assert result.exit_code == 0
        assert "Dead Link Detection Results" in result.stdout
        assert "Files scanned:" in result.stdout

    def test_detect_dead_links_json_output(self) -> None:
        """Test detect-dead-links command with JSON output."""
        runner = CliRunner()
        vault_path = "tests/test-data/vaults/test-myvault"

        result = runner.invoke(
            app, ["detect-dead-links", vault_path, "--output-format", "json"]
        )

        # Should succeed despite warnings
        assert result.exit_code == 0

        # Extract JSON using helper function
        json_output = extract_json_from_cli_output(result.stdout)
        assert "detection_timestamp" in json_output
        assert "vault_path" in json_output
        assert "total_files_scanned" in json_output
        assert "dead_links" in json_output
        assert isinstance(json_output["dead_links"], list)

    def test_detect_dead_links_with_limit(self) -> None:
        """Test detect-dead-links command with limit option."""
        runner = CliRunner()
        vault_path = "tests/test-data/vaults/test-myvault"

        result = runner.invoke(
            app,
            [
                "detect-dead-links",
                vault_path,
                "--output-format",
                "json",
                "--limit",
                "3",
            ],
        )

        assert result.exit_code == 0

        # Extract JSON using helper function
        json_output = extract_json_from_cli_output(result.stdout)

        # Should have at most 3 dead links
        assert len(json_output["dead_links"]) <= 3
        assert json_output["total_dead_links"] <= 3

    def test_detect_dead_links_with_suggestions_filter(self) -> None:
        """Test detect-dead-links command with only-with-suggestions filter."""
        runner = CliRunner()
        vault_path = "tests/test-data/vaults/test-myvault"

        result = runner.invoke(
            app,
            [
                "detect-dead-links",
                vault_path,
                "--output-format",
                "json",
                "--only-with-suggestions",
            ],
        )

        assert result.exit_code == 0

        # Extract JSON using helper function
        json_output = extract_json_from_cli_output(result.stdout)

        # All dead links should have suggestions
        for dead_link in json_output["dead_links"]:
            assert len(dead_link["suggested_fixes"]) > 0

    def test_detect_dead_links_with_link_type_filter(self) -> None:
        """Test detect-dead-links command with link type filter."""
        runner = CliRunner()
        vault_path = "tests/test-data/vaults/test-myvault"

        result = runner.invoke(
            app,
            [
                "detect-dead-links",
                vault_path,
                "--output-format",
                "json",
                "--link-type",
                "wikilink",
            ],
        )

        assert result.exit_code == 0

        # Extract JSON using helper function
        json_output = extract_json_from_cli_output(result.stdout)

        # All dead links should be wikilinks
        for dead_link in json_output["dead_links"]:
            assert dead_link["link_type"] == "wikilink"

    def test_detect_dead_links_invalid_link_type(self) -> None:
        """Test detect-dead-links command with invalid link type."""
        runner = CliRunner()
        vault_path = "tests/test-data/vaults/test-myvault"

        result = runner.invoke(
            app,
            [
                "detect-dead-links",
                vault_path,
                "--link-type",
                "invalid_type",
            ],
        )

        # Should fail with error
        assert result.exit_code != 0

    def test_detect_dead_links_sort_by_target(self) -> None:
        """Test detect-dead-links command with sort by target."""
        runner = CliRunner()
        vault_path = "tests/test-data/vaults/test-myvault"

        result = runner.invoke(
            app,
            [
                "detect-dead-links",
                vault_path,
                "--output-format",
                "json",
                "--sort-by",
                "target",
                "--limit",
                "5",
            ],
        )

        assert result.exit_code == 0

        # Extract JSON using helper function
        json_output = extract_json_from_cli_output(result.stdout)

        # Check that results are sorted by target
        targets = [dl["target"] for dl in json_output["dead_links"]]
        assert targets == sorted(targets)

    def test_detect_dead_links_invalid_sort_option(self) -> None:
        """Test detect-dead-links command with invalid sort option."""
        runner = CliRunner()
        vault_path = "tests/test-data/vaults/test-myvault"

        result = runner.invoke(
            app,
            [
                "detect-dead-links",
                vault_path,
                "--sort-by",
                "invalid_sort",
            ],
        )

        # Should fail with error
        assert result.exit_code != 0

    def test_detect_dead_links_csv_output(self) -> None:
        """Test detect-dead-links command with CSV output."""
        runner = CliRunner()
        vault_path = "tests/test-data/vaults/test-myvault"

        result = runner.invoke(
            app,
            [
                "detect-dead-links",
                vault_path,
                "--output-format",
                "csv",
                "--limit",
                "2",
            ],
        )

        assert result.exit_code == 0

        # Should contain CSV headers
        assert (
            "source_file,link_text,link_type,line_number,target,suggested_fixes"
            in result.stdout
        )

    def test_detect_dead_links_nonexistent_vault(self) -> None:
        """Test detect-dead-links command with nonexistent vault path."""
        runner = CliRunner()

        result = runner.invoke(app, ["detect-dead-links", "/nonexistent/path"])

        # Should fail with error
        assert result.exit_code != 0
        assert "does not exist" in result.stdout

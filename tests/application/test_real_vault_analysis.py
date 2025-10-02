"""Test vault analysis with real test-myvault data."""

import json
import subprocess
import time
from pathlib import Path

import pytest

from knowledge_base_organizer.application.vault_analyzer import VaultAnalyzer
from knowledge_base_organizer.infrastructure.config import ProcessingConfig


class TestRealVaultAnalysis:
    """Test vault analysis with real test-myvault sample data."""

    @pytest.fixture
    def test_vault_path(self) -> Path:
        """Get path to test-myvault."""
        return Path("tests/test-data/vaults/test-myvault")

    @pytest.fixture
    def vault_analyzer(self) -> VaultAnalyzer:
        """Create vault analyzer with default config."""
        config = ProcessingConfig.get_default_config()
        return VaultAnalyzer(config)

    def test_analyze_command_with_test_myvault(
        self, vault_analyzer: VaultAnalyzer, test_vault_path: Path
    ) -> None:
        """Test analysis command with test-myvault sample data."""
        # Verify test vault exists
        assert test_vault_path.exists(), f"Test vault not found: {test_vault_path}"

        # Run detailed analysis
        result = vault_analyzer.analyze_vault_detailed(test_vault_path)

        # Verify basic structure
        assert "vault_path" in result
        assert "analysis_timestamp" in result
        assert "file_statistics" in result
        assert "frontmatter_statistics" in result
        assert "link_statistics" in result
        assert "content_statistics" in result

        # Verify file statistics
        file_stats = result["file_statistics"]
        assert file_stats["total_files"] > 0
        assert file_stats["files_with_frontmatter"] > 0
        assert file_stats["files_with_id"] > 0
        assert ".md" in file_stats["files_by_extension"]

        # Verify frontmatter statistics
        fm_stats = result["frontmatter_statistics"]
        assert fm_stats["total_unique_fields"] > 0
        assert len(fm_stats["most_common_fields"]) > 0
        assert (
            fm_stats["field_distribution"]["title"] > 0
        )  # All files should have title

        # Verify link statistics structure
        link_stats = result["link_statistics"]
        assert "wiki_links" in link_stats
        assert "regular_links" in link_stats
        assert "link_reference_definitions" in link_stats
        assert "total_links" in link_stats

        # Verify content statistics
        content_stats = result["content_statistics"]
        assert content_stats["total_content_length"] > 0
        assert content_stats["average_content_length"] > 0
        assert content_stats["largest_file_size"] >= content_stats["smallest_file_size"]

    def test_frontmatter_parsing_with_various_templates(
        self, vault_analyzer: VaultAnalyzer, test_vault_path: Path
    ) -> None:
        """Verify frontmatter parsing works with various templates."""
        files = vault_analyzer.load_vault_files(test_vault_path)

        # Find files from different template directories
        fleeting_notes = [f for f in files if "100_FleetingNotes" in str(f.path)]
        permanent_notes = [f for f in files if "101_PermanentNotes" in str(f.path)]
        books = [f for f in files if "104_Books" in str(f.path)]
        templates = [f for f in files if "900_TemplaterNotes" in str(f.path)]
        book_templates = [f for f in files if "903_BookSearchTemplates" in str(f.path)]

        # Verify we have files from different directories
        assert len(fleeting_notes) > 0, "Should have fleeting notes"
        assert len(permanent_notes) > 0, "Should have permanent notes"
        assert len(books) > 0, "Should have book files"
        assert len(templates) > 0, "Should have template files"
        assert len(book_templates) > 0, "Should have book template files"

        # Test fleeting notes frontmatter
        for file in fleeting_notes:
            if file.frontmatter:
                fm_dict = file.frontmatter.model_dump(exclude_unset=True)
                # Common fields in fleeting notes (flexible about fields)
                common_fields = {"title", "aliases", "tags", "publish"}
                found_fields = set(fm_dict.keys())
                # At least title should be present
                assert "title" in found_fields, f"Title field missing in {file.path}"
                # Should have some common fields
                overlap = common_fields.intersection(found_fields)
                min_common_fields = 2
                assert len(overlap) >= min_common_fields, (
                    f"Too few common fields in {file.path}. "
                    f"Expected some of: {common_fields}, Found: {found_fields}"
                )

        # Test book files frontmatter
        for file in books:
            if file.frontmatter:
                fm_dict = file.frontmatter.model_dump(exclude_unset=True)
                # Book files should have book-specific fields
                book_fields = {"title", "author", "isbn13", "publishDate"}
                found_fields = set(fm_dict.keys())
                # At least some book fields should be present
                assert len(book_fields.intersection(found_fields)) > 0, (
                    f"No book fields found in {file.path}. "
                    f"Expected some of: {book_fields}, Found: {found_fields}"
                )

        # Test template files (may have templater syntax that can't be parsed)
        template_files = [f for f in templates if f.path.name != "no-template.md"]
        parseable_templates = []
        unparseable_templates = []

        for file in template_files:
            fm_dict = file.frontmatter.model_dump(exclude_unset=True)
            if fm_dict:  # Has parseable frontmatter
                parseable_templates.append(file)
                # Parseable template files should have at least title field
                assert "title" in fm_dict, (
                    f"Parseable template file {file.path} should have title"
                )
            else:  # Has unparseable frontmatter (templater syntax)
                unparseable_templates.append(file)

        # Should have both parseable and unparseable templates (good test data variety)
        assert len(parseable_templates) > 0, "Should have some parseable template files"
        assert len(unparseable_templates) > 0, (
            "Should have some unparseable template files (with templater syntax)"
        )

    def test_error_handling_with_malformed_files(
        self, vault_analyzer: VaultAnalyzer, test_vault_path: Path
    ) -> None:
        """Ensure error handling works with malformed files."""
        # Test with empty file (no-template.md is empty)
        files = vault_analyzer.load_vault_files(test_vault_path)

        # Find the empty file
        empty_files = [f for f in files if f.path.name == "no-template.md"]
        if empty_files:
            empty_file = empty_files[0]
            # Should handle empty file gracefully
            assert not empty_file.content
            # Empty file should have empty frontmatter
            fm_dict = empty_file.frontmatter.model_dump(exclude_unset=True)
            assert len(fm_dict) == 0

        # Test analysis with potentially problematic files
        try:
            result = vault_analyzer.analyze_vault_detailed(test_vault_path)
            # Analysis should complete without errors
            assert result["file_statistics"]["total_files"] > 0
        except (ValueError, FileNotFoundError, RuntimeError) as e:
            pytest.fail(
                f"Analysis should handle malformed files gracefully, but got: {e}"
            )

    def test_specific_frontmatter_field_variations(
        self, vault_analyzer: VaultAnalyzer, test_vault_path: Path
    ) -> None:
        """Test parsing of specific frontmatter field variations found in test data."""
        files = vault_analyzer.load_vault_files(test_vault_path)

        # Test files with different alias formats
        saga_file = None
        cloudwatch_file = None

        for file in files:
            if "Saga Pattern" in str(file.frontmatter.title or ""):
                saga_file = file
            elif "Amazon CloudWatch" in str(file.frontmatter.title or ""):
                cloudwatch_file = file

        # Test Saga Pattern file (has Japanese aliases)
        if saga_file:
            assert saga_file.frontmatter.aliases
            assert "saga" in saga_file.frontmatter.aliases
            assert "sagaパターン" in saga_file.frontmatter.aliases
            assert saga_file.frontmatter.tags
            assert "softwaredevelopment" in saga_file.frontmatter.tags

        # Test CloudWatch file (has WikiLinks in content)
        if cloudwatch_file:
            assert cloudwatch_file.frontmatter.aliases
            assert "CloudWatch" in cloudwatch_file.frontmatter.aliases
            # Should extract links from content
            cloudwatch_file.extract_links()
            assert len(cloudwatch_file.wiki_links) > 0

    def test_link_extraction_from_real_content(
        self, vault_analyzer: VaultAnalyzer, test_vault_path: Path
    ) -> None:
        """Test link extraction from real content in test vault."""
        files = vault_analyzer.load_vault_files(test_vault_path)

        # Extract links from all files
        for file in files:
            file.extract_links()

        # Find files with WikiLinks
        files_with_wiki_links = [f for f in files if f.wiki_links]

        # Should find some files with links
        assert len(files_with_wiki_links) > 0, "Should find files with WikiLinks"

        # Test specific link patterns
        cloudwatch_file = None
        for file in files:
            if "Amazon CloudWatch" in str(file.frontmatter.title or ""):
                cloudwatch_file = file
                break

        if cloudwatch_file:
            # CloudWatch file has many WikiLinks
            min_wiki_links = 5
            assert len(cloudwatch_file.wiki_links) > min_wiki_links

            # Check for specific WikiLink patterns
            wiki_link_texts = [link.target_id for link in cloudwatch_file.wiki_links]
            assert "20230816202421" in wiki_link_texts  # CloudWatch Logs link
            assert "20240314205715" in wiki_link_texts  # CloudWatch Events link

    def test_json_serialization_of_results(
        self, vault_analyzer: VaultAnalyzer, test_vault_path: Path
    ) -> None:
        """Test that analysis results can be properly serialized to JSON."""
        result = vault_analyzer.analyze_vault_detailed(test_vault_path)

        # Should be able to serialize to JSON without errors
        try:
            json_str = json.dumps(result, indent=2, ensure_ascii=False)
            assert len(json_str) > 0

            # Should be able to deserialize back
            deserialized = json.loads(json_str)
            assert (
                deserialized["file_statistics"]["total_files"]
                == result["file_statistics"]["total_files"]
            )

        except (TypeError, ValueError) as e:
            pytest.fail(f"Analysis results should be JSON serializable, but got: {e}")

    def test_performance_with_real_data(
        self, vault_analyzer: VaultAnalyzer, test_vault_path: Path
    ) -> None:
        """Test performance characteristics with real data."""
        start_time = time.time()
        result = vault_analyzer.analyze_vault_detailed(test_vault_path)
        end_time = time.time()

        analysis_time = end_time - start_time
        file_count = result["file_statistics"]["total_files"]

        # Analysis should complete in reasonable time
        max_analysis_time = 10.0
        assert analysis_time < max_analysis_time, (
            f"Analysis took too long: {analysis_time:.2f}s for {file_count} files"
        )

        # Should process at reasonable rate
        if file_count > 0:
            files_per_second = file_count / analysis_time
            assert files_per_second > 1.0, (
                f"Processing rate too slow: {files_per_second:.2f} files/sec"
            )

    def test_requirements_1_1_compliance(
        self, vault_analyzer: VaultAnalyzer, test_vault_path: Path
    ) -> None:
        """Test compliance with Requirement 1.1: vault scanning and parsing."""
        # Requirement 1.1: WHEN I provide a vault directory path THEN the system
        # SHALL scan all markdown files recursively
        result = vault_analyzer.analyze_vault_detailed(test_vault_path)

        # Should scan all markdown files recursively
        min_expected_files = 10  # We know test vault has multiple files
        assert result["file_statistics"]["total_files"] >= min_expected_files

        # Should parse frontmatter metadata (title, aliases, tags, etc.)
        fm_stats = result["frontmatter_statistics"]
        field_dist = fm_stats["field_distribution"]

        # Should find common frontmatter fields
        expected_fields = ["title", "aliases", "tags", "id", "date", "publish"]
        found_fields = list(field_dist.keys())

        # At least some expected fields should be found
        common_fields = set(expected_fields).intersection(set(found_fields))
        min_expected_common_fields = 4
        assert len(common_fields) >= min_expected_common_fields, (
            f"Should find most common frontmatter fields. Found: {found_fields}"
        )

        # Should have files with meaningful frontmatter
        assert result["file_statistics"]["files_with_frontmatter"] > 0
        assert result["file_statistics"]["files_with_id"] > 0

    def test_cli_analyze_command_with_test_myvault(self, test_vault_path: Path) -> None:
        """Test the CLI analyze command with test-myvault data."""
        # Run the CLI analyze command
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-m",
                "knowledge_base_organizer",
                str(test_vault_path),
                "--output-format",
                "json",
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=".",
        )

        # Should complete successfully
        assert result.returncode == 0, f"CLI command failed: {result.stderr}"

        # Should contain expected output elements (even with warnings)
        output = result.stdout
        assert "vault_path" in output, "Should contain vault_path in output"
        assert "file_statistics" in output, "Should contain file_statistics in output"
        assert "frontmatter_statistics" in output, (
            "Should contain frontmatter_statistics in output"
        )
        assert "link_statistics" in output, "Should contain link_statistics in output"
        assert "content_statistics" in output, (
            "Should contain content_statistics in output"
        )

        # Should show that files were found
        assert "total_files" in output, "Should show total_files count"
        assert '"total_files": 15' in output or '"total_files":15' in output, (
            "Should find 15 files in test vault"
        )

    def test_cli_analyze_command_console_output(self, test_vault_path: Path) -> None:
        """Test the CLI analyze command with console output format."""
        # Run the CLI analyze command with console output
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-m",
                "knowledge_base_organizer",
                str(test_vault_path),
                "--output-format",
                "console",
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=".",
        )

        # Should complete successfully
        assert result.returncode == 0, f"CLI command failed: {result.stderr}"

        # Should contain expected console output sections
        output = result.stdout
        assert "📊 Vault Analysis Results" in output
        assert "📁 File Statistics" in output
        assert "📋 Frontmatter Statistics" in output
        assert "🔗 Link Statistics" in output
        assert "📝 Content Statistics" in output

        # Should show file counts
        assert "Total files:" in output
        assert "Files with frontmatter:" in output

    def test_error_handling_with_nonexistent_vault(self) -> None:
        """Test error handling when vault path doesn't exist."""
        nonexistent_path = Path("/nonexistent/vault/path")

        # Run the CLI analyze command with nonexistent path
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "-m",
                "knowledge_base_organizer",
                str(nonexistent_path),
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=".",
        )

        # Should fail gracefully
        assert result.returncode == 1, (
            "Should exit with error code for nonexistent path"
        )
        assert "Error:" in result.stdout or "Error:" in result.stderr

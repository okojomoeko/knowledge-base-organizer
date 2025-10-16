#!/usr/bin/env python3
"""
Integration tests for Task 6.4: Test link detection with real data.

This test suite verifies:
- Test with test-myvault to find actual dead links
- Verify exclusion zones work correctly
- Test performance with large numbers of files
- Requirements: 3.1, 3.2
"""

import json
import re
import subprocess
import time
from pathlib import Path

import pytest


class TestDeadLinkDetectionRealData:
    """Integration tests for dead link detection with real vault data."""

    @pytest.fixture
    def vault_path(self) -> str:
        """Path to test vault."""
        return "tests/test-data/vaults/test-myvault"

    def _run_dead_link_detection(self, vault_path: str, **kwargs) -> dict:
        """Run dead link detection command and return parsed results."""
        cmd = [
            "uv",
            "run",
            "python",
            "-m",
            "knowledge_base_organizer",
            "detect-dead-links",
            vault_path,
            "--output-format",
            "json",
        ]

        # Add optional parameters
        if "limit" in kwargs:
            cmd.extend(["--limit", str(kwargs["limit"])])
        if "link_type" in kwargs:
            cmd.extend(["--link-type", kwargs["link_type"]])
        if "sort_by" in kwargs:
            cmd.extend(["--sort-by", kwargs["sort_by"]])
        if kwargs.get("only_with_suggestions"):
            cmd.append("--only-with-suggestions")

        start_time = time.time()
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        end_time = time.time()

        execution_time = end_time - start_time

        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Extract JSON from output (skip warnings)
        lines = result.stdout.strip().split("\n")
        json_start = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("{"):
                json_start = i
                break

        assert json_start != -1, "No JSON output found"

        json_output = "\n".join(lines[json_start:])

        # Clean control characters and parse JSON
        clean_json = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", json_output)
        data = json.loads(clean_json)
        data["execution_time"] = execution_time
        return data

    def test_basic_dead_link_detection(self, vault_path: str) -> None:
        """Test basic dead link detection functionality with real vault data."""
        result = self._run_dead_link_detection(vault_path)

        # Verify basic structure
        assert "dead_links" in result
        assert "dead_links_by_type" in result
        assert "summary" in result
        assert "total_files_scanned" in result
        assert "total_dead_links" in result

        # Verify we found some dead links in the test vault
        assert result["total_files_scanned"] == 15  # Expected number of files
        assert result["total_dead_links"] > 0  # Should find some dead links
        assert result["files_with_dead_links"] > 0

        # Verify dead links have required fields
        for dead_link in result["dead_links"]:
            assert "source_file" in dead_link
            assert "link_text" in dead_link
            assert "link_type" in dead_link
            assert "line_number" in dead_link
            assert "target" in dead_link
            assert "suggested_fixes" in dead_link

    def test_exclusion_zones_template_variables(self, vault_path: str) -> None:
        """Test that template variables are properly excluded from dead links."""
        result = self._run_dead_link_detection(vault_path)

        # Check that template variables are not detected as dead links
        template_variables_found = []
        for dead_link in result["dead_links"]:
            target = dead_link["target"]
            # Check for common template variable patterns
            if any(pattern in target for pattern in ["${", "<%", "{{", "tp.", "tR +="]):
                template_variables_found.append(dead_link)

        # Should not find any template variables as dead links
        assert len(template_variables_found) == 0, (
            f"Template variables found in dead links: "
            f"{[dl['target'] for dl in template_variables_found]}"
        )

    def test_link_type_filtering(self, vault_path: str) -> None:
        """Test filtering by link type."""
        # Test wikilink filtering
        wikilink_result = self._run_dead_link_detection(
            vault_path, link_type="wikilink"
        )

        # Verify all results are wikilinks
        for dead_link in wikilink_result["dead_links"]:
            assert dead_link["link_type"] == "wikilink"

        # Test regular_link filtering
        regular_result = self._run_dead_link_detection(
            vault_path, link_type="regular_link"
        )

        # Verify all results are regular links
        for dead_link in regular_result["dead_links"]:
            assert dead_link["link_type"] == "regular_link"

    def test_sorting_and_limiting(self, vault_path: str) -> None:
        """Test sorting and limiting functionality."""
        # Test sorting by target with limit
        result = self._run_dead_link_detection(vault_path, sort_by="target", limit=5)

        # Verify sorting
        targets = [dl["target"] for dl in result["dead_links"]]
        assert targets == sorted(targets), "Results not properly sorted by target"

        # Verify limiting
        assert len(result["dead_links"]) <= 5, "Limit not applied correctly"

    def test_performance_characteristics(self, vault_path: str) -> None:
        """Test performance characteristics with the test vault."""
        # Run multiple times to get performance metrics
        execution_times = []
        for _ in range(3):
            result = self._run_dead_link_detection(vault_path)
            execution_times.append(result["execution_time"])

        avg_time = sum(execution_times) / len(execution_times)

        # Performance should be reasonable for test vault size
        assert avg_time < 5.0, f"Performance too slow: {avg_time:.2f}s average"

        # Verify consistent results
        assert max(execution_times) - min(execution_times) < 2.0, (
            "Inconsistent performance"
        )

    def test_suggestion_generation(self, vault_path: str) -> None:
        """Test suggestion generation for dead links."""
        result = self._run_dead_link_detection(vault_path)

        # Count links with and without suggestions
        links_with_suggestions = [
            dl for dl in result["dead_links"] if dl["suggested_fixes"]
        ]
        # links_without_suggestions = [
        #     dl for dl in result["dead_links"] if not dl["suggested_fixes"]
        # ]

        # Should have some links with suggestions (similar file IDs)
        assert len(links_with_suggestions) > 0, "No suggestions generated"

        # Test filtering by suggestions
        suggestions_only = self._run_dead_link_detection(
            vault_path, only_with_suggestions=True
        )

        # Verify all filtered results have suggestions
        for dead_link in suggestions_only["dead_links"]:
            assert len(dead_link["suggested_fixes"]) > 0, (
                "Link without suggestions in filtered results"
            )

    def test_file_coverage(self, vault_path: str) -> None:
        """Test that all markdown files are properly scanned."""
        result = self._run_dead_link_detection(vault_path)

        # Count actual markdown files in vault
        vault_path_obj = Path(vault_path)
        actual_md_files = list(vault_path_obj.rglob("*.md"))

        # Verify file coverage
        assert result["total_files_scanned"] == len(actual_md_files), (
            f"File count mismatch: scanned {result['total_files_scanned']}, "
            f"actual {len(actual_md_files)}"
        )

    def test_dead_link_types_detected(self, vault_path: str) -> None:
        """Test that different types of dead links are detected."""
        result = self._run_dead_link_detection(vault_path)

        # Should detect WikiLinks (most common in test vault)
        assert result["dead_links_by_type"].get("wikilink", 0) > 0, (
            "No WikiLinks detected"
        )

        # Verify dead link structure
        wikilinks = [dl for dl in result["dead_links"] if dl["link_type"] == "wikilink"]
        for wikilink in wikilinks:
            assert wikilink["link_text"].startswith("[["), "Invalid WikiLink format"
            assert wikilink["link_text"].endswith("]]"), "Invalid WikiLink format"

    def test_real_dead_links_found(self, vault_path: str) -> None:
        """Test that actual dead links are found in the test vault."""
        result = self._run_dead_link_detection(vault_path)

        # Should find specific dead links we know exist in test data
        dead_targets = [dl["target"] for dl in result["dead_links"]]

        # These are known dead links in the test vault
        expected_dead_links = [
            "MySQL",
            "PostgreSQL",
            "Oracle Database",
            "Microsoft SQL Server",
        ]

        for expected in expected_dead_links:
            assert expected in dead_targets, (
                f"Expected dead link '{expected}' not found"
            )

    def test_exclusion_zones_comprehensive(self, vault_path: str) -> None:
        """Test comprehensive exclusion zone functionality."""
        result = self._run_dead_link_detection(vault_path)

        # Verify no frontmatter links are detected as dead links
        # (This would require checking line numbers against frontmatter boundaries)

        # Verify no existing WikiLinks are detected as dead links within other WikiLinks
        # (This is handled by the exclusion zone logic)

        # Check that template blocks are excluded
        template_blocks_found = []
        for dead_link in result["dead_links"]:
            if any(
                pattern in dead_link["target"] for pattern in ["<%*", "*%>", "<%", "%>"]
            ):
                template_blocks_found.append(dead_link)

        assert len(template_blocks_found) == 0, (
            f"Template blocks found in dead links: "
            f"{[dl['target'] for dl in template_blocks_found]}"
        )

    def test_error_handling_robustness(self, vault_path: str) -> None:
        """Test that the system handles various file conditions robustly."""
        result = self._run_dead_link_detection(vault_path)

        # Should complete successfully despite warnings about malformed frontmatter
        assert result["total_files_scanned"] > 0
        assert "dead_links" in result

        # Should handle files with various frontmatter issues
        # (The test vault contains files with YAML parsing errors)

        # Should handle template files with special syntax
        # (The test vault contains Templater syntax)

        # Verify the system continues processing despite individual file errors
        assert result["total_files_scanned"] == 15  # All files should be processed


if __name__ == "__main__":
    # Run tests directly for debugging
    test_instance = TestDeadLinkDetectionRealData()
    vault_path = "tests/test-data/vaults/test-myvault"

    print("Running Task 6.4 integration tests...")

    try:
        test_instance.test_basic_dead_link_detection(vault_path)
        print("✅ Basic dead link detection")

        test_instance.test_exclusion_zones_template_variables(vault_path)
        print("✅ Template variable exclusion")

        test_instance.test_link_type_filtering(vault_path)
        print("✅ Link type filtering")

        test_instance.test_sorting_and_limiting(vault_path)
        print("✅ Sorting and limiting")

        test_instance.test_performance_characteristics(vault_path)
        print("✅ Performance characteristics")

        test_instance.test_suggestion_generation(vault_path)
        print("✅ Suggestion generation")

        test_instance.test_file_coverage(vault_path)
        print("✅ File coverage")

        test_instance.test_dead_link_types_detected(vault_path)
        print("✅ Dead link types detection")

        test_instance.test_real_dead_links_found(vault_path)
        print("✅ Real dead links found")

        test_instance.test_exclusion_zones_comprehensive(vault_path)
        print("✅ Comprehensive exclusion zones")

        test_instance.test_error_handling_robustness(vault_path)
        print("✅ Error handling robustness")

        print("\n🎉 All Task 6.4 integration tests passed!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise

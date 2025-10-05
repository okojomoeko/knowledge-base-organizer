#!/usr/bin/env python3
"""
実験: Dead Link Detection with Real Data Testing
日付: 2025-01-05
目的: Task 6.4 - Test link detection with real data
- Test with test-myvault to find actual dead links
- Verify exclusion zones work correctly
- Test performance with large numbers of files
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Any


def run_dead_link_detection(vault_path: str, **kwargs) -> dict[str, Any]:
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

    print(f"Running command: {' '.join(cmd)}")

    start_time = time.time()
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    end_time = time.time()

    execution_time = end_time - start_time

    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        print(f"STDERR: {result.stderr}")
        return {"error": result.stderr, "execution_time": execution_time}

    # Extract JSON from output (skip warnings)
    lines = result.stdout.strip().split("\n")
    json_start = -1
    for i, line in enumerate(lines):
        if line.strip().startswith("{"):
            json_start = i
            break

    if json_start == -1:
        print("No JSON output found")
        return {"error": "No JSON output found", "execution_time": execution_time}

    json_output = "\n".join(lines[json_start:])

    try:
        # Clean the JSON output by removing control characters
        import re

        clean_json = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", json_output)
        data = json.loads(clean_json)
        data["execution_time"] = execution_time
        return data
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        print(f"Raw output: {json_output[:500]}...")
        # Try to save the problematic JSON for debugging
        with open(
            "debug_json_output.txt", "w", encoding="utf-8", errors="replace"
        ) as f:
            f.write(json_output)
        print("Saved problematic JSON to debug_json_output.txt")
        return {"error": f"JSON parsing error: {e}", "execution_time": execution_time}


def test_basic_dead_link_detection():
    """Test basic dead link detection functionality."""
    print("\n=== Test 1: Basic Dead Link Detection ===")

    vault_path = "tests/test-data/vaults/test-myvault"
    result = run_dead_link_detection(vault_path)

    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return False

    print(f"✅ Execution time: {result['execution_time']:.2f}s")
    print(f"✅ Files scanned: {result['total_files_scanned']}")
    print(f"✅ Dead links found: {result['total_dead_links']}")
    print(f"✅ Files with dead links: {result['files_with_dead_links']}")

    # Verify structure
    assert "dead_links" in result
    assert "dead_links_by_type" in result
    assert "summary" in result

    # Show dead links found
    if result["dead_links"]:
        print("\n📋 Dead links found:")
        for i, dead_link in enumerate(result["dead_links"][:5], 1):
            print(
                f"  {i}. {dead_link['link_text']} in {Path(dead_link['source_file']).name}"
            )
            print(
                f"     Type: {dead_link['link_type']}, Line: {dead_link['line_number']}"
            )
            print(f"     Target: {dead_link['target']}")
            if dead_link["suggested_fixes"]:
                print(f"     Suggestions: {', '.join(dead_link['suggested_fixes'])}")

    return True


def test_exclusion_zones():
    """Test that exclusion zones work correctly."""
    print("\n=== Test 2: Exclusion Zones Verification ===")

    # Test with template files that contain template variables
    vault_path = "tests/test-data/vaults/test-myvault"
    result = run_dead_link_detection(vault_path)

    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return False

    # Check if template variables are properly excluded
    template_variables_found = []
    for dead_link in result["dead_links"]:
        target = dead_link["target"]
        # Check for common template variable patterns
        if any(pattern in target for pattern in ["${", "<%", "{{", "tp.", "tR +="]):
            template_variables_found.append(dead_link)

    if template_variables_found:
        print("⚠️  Template variables found in dead links (should be excluded):")
        for dead_link in template_variables_found:
            print(f"  - {dead_link['target']} in {Path(dead_link['source_file']).name}")
        return False
    print("✅ Template variables properly excluded from dead links")

    # Check for frontmatter exclusion
    frontmatter_links_found = []
    for dead_link in result["dead_links"]:
        # If line number is very low (1-10), it might be in frontmatter
        if dead_link["line_number"] <= 10:
            frontmatter_links_found.append(dead_link)

    if frontmatter_links_found:
        print("⚠️  Potential frontmatter links found:")
        for dead_link in frontmatter_links_found:
            print(
                f"  - {dead_link['target']} at line {dead_link['line_number']} in {Path(dead_link['source_file']).name}"
            )
    else:
        print("✅ No frontmatter links detected in dead links")

    return True


def test_link_type_filtering():
    """Test filtering by link type."""
    print("\n=== Test 3: Link Type Filtering ===")

    vault_path = "tests/test-data/vaults/test-myvault"

    # Test wikilink filtering
    wikilink_result = run_dead_link_detection(vault_path, link_type="wikilink")
    if "error" in wikilink_result:
        print(f"❌ Wikilink filter error: {wikilink_result['error']}")
        return False

    # Verify all results are wikilinks
    for dead_link in wikilink_result["dead_links"]:
        if dead_link["link_type"] != "wikilink":
            print(f"❌ Non-wikilink found: {dead_link['link_type']}")
            return False

    print(f"✅ Wikilink filter: {wikilink_result['total_dead_links']} wikilinks found")

    # Test regular_link filtering
    regular_result = run_dead_link_detection(vault_path, link_type="regular_link")
    if "error" in regular_result:
        print(f"❌ Regular link filter error: {regular_result['error']}")
        return False

    print(
        f"✅ Regular link filter: {regular_result['total_dead_links']} regular links found"
    )

    return True


def test_sorting_and_limiting():
    """Test sorting and limiting functionality."""
    print("\n=== Test 4: Sorting and Limiting ===")

    vault_path = "tests/test-data/vaults/test-myvault"

    # Test sorting by target
    sorted_result = run_dead_link_detection(vault_path, sort_by="target", limit=5)
    if "error" in sorted_result:
        print(f"❌ Sorting error: {sorted_result['error']}")
        return False

    # Verify sorting
    targets = [dl["target"] for dl in sorted_result["dead_links"]]
    if targets == sorted(targets):
        print("✅ Results properly sorted by target")
    else:
        print("❌ Results not properly sorted")
        print(f"Expected: {sorted(targets)}")
        print(f"Actual: {targets}")
        return False

    # Verify limiting
    if len(sorted_result["dead_links"]) <= 5:
        print(
            f"✅ Results properly limited to {len(sorted_result['dead_links'])} items"
        )
    else:
        print(
            f"❌ Limit not applied: {len(sorted_result['dead_links'])} items returned"
        )
        return False

    return True


def test_performance_characteristics():
    """Test performance characteristics."""
    print("\n=== Test 5: Performance Characteristics ===")

    vault_path = "tests/test-data/vaults/test-myvault"

    # Run multiple times to get average performance
    execution_times = []
    for i in range(3):
        result = run_dead_link_detection(vault_path)
        if "error" not in result:
            execution_times.append(result["execution_time"])

    if not execution_times:
        print("❌ No successful runs for performance testing")
        return False

    avg_time = sum(execution_times) / len(execution_times)
    min_time = min(execution_times)
    max_time = max(execution_times)

    print("✅ Performance metrics:")
    print(f"   Average execution time: {avg_time:.2f}s")
    print(f"   Min execution time: {min_time:.2f}s")
    print(f"   Max execution time: {max_time:.2f}s")

    # Performance expectations for test vault
    if avg_time < 5.0:  # Should be fast for small test vault
        print("✅ Performance acceptable for test vault size")
    else:
        print("⚠️  Performance slower than expected")

    return True


def test_suggestion_generation():
    """Test suggestion generation for dead links."""
    print("\n=== Test 6: Suggestion Generation ===")

    vault_path = "tests/test-data/vaults/test-myvault"
    result = run_dead_link_detection(vault_path)

    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return False

    # Count links with suggestions
    links_with_suggestions = [
        dl for dl in result["dead_links"] if dl["suggested_fixes"]
    ]
    links_without_suggestions = [
        dl for dl in result["dead_links"] if not dl["suggested_fixes"]
    ]

    print(f"✅ Links with suggestions: {len(links_with_suggestions)}")
    print(f"✅ Links without suggestions: {len(links_without_suggestions)}")

    # Show some examples
    if links_with_suggestions:
        print("\n📋 Examples with suggestions:")
        for dead_link in links_with_suggestions[:3]:
            print(
                f"  - {dead_link['target']}: {', '.join(dead_link['suggested_fixes'])}"
            )

    # Test filtering by suggestions
    suggestions_only = run_dead_link_detection(vault_path, only_with_suggestions=True)
    if "error" not in suggestions_only:
        print(
            f"✅ Suggestions-only filter: {suggestions_only['total_dead_links']} links"
        )

        # Verify all have suggestions
        for dead_link in suggestions_only["dead_links"]:
            if not dead_link["suggested_fixes"]:
                print(
                    f"❌ Link without suggestions found in filtered results: {dead_link['target']}"
                )
                return False
        print("✅ All filtered results have suggestions")

    return True


def test_file_coverage():
    """Test that all file types are properly scanned."""
    print("\n=== Test 7: File Coverage ===")

    vault_path = "tests/test-data/vaults/test-myvault"
    result = run_dead_link_detection(vault_path)

    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return False

    # Check file coverage
    files_scanned = result["total_files_scanned"]

    # Count actual markdown files in vault
    vault_path_obj = Path(vault_path)
    actual_md_files = list(vault_path_obj.rglob("*.md"))

    print(f"✅ Files scanned by tool: {files_scanned}")
    print(f"✅ Actual .md files in vault: {len(actual_md_files)}")

    if files_scanned == len(actual_md_files):
        print("✅ All markdown files scanned")
    else:
        print("⚠️  File count mismatch - some files may be excluded")

        # Show which files might be missing
        scanned_files = set()
        for dead_link in result["dead_links"]:
            scanned_files.add(dead_link["source_file"])

        print(f"   Files with dead links: {len(scanned_files)}")

    return True


def main():
    """Run all dead link detection tests."""
    print("🔗 Dead Link Detection Real Data Testing")
    print("=" * 50)

    tests = [
        ("Basic Dead Link Detection", test_basic_dead_link_detection),
        ("Exclusion Zones Verification", test_exclusion_zones),
        ("Link Type Filtering", test_link_type_filtering),
        ("Sorting and Limiting", test_sorting_and_limiting),
        ("Performance Characteristics", test_performance_characteristics),
        ("Suggestion Generation", test_suggestion_generation),
        ("File Coverage", test_file_coverage),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)

    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1

    print(f"\nOverall: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("🎉 All tests passed! Task 6.4 requirements verified.")
        return True
    print("⚠️  Some tests failed. Review the issues above.")
    return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

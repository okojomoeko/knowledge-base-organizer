#!/usr/bin/env python3
"""Test better pattern matching approaches."""

import fnmatch
from pathlib import Path


def test_improved_pattern_matching():
    """Test improved pattern matching that handles edge cases."""
    test_paths = [
        "temp/file.md",
        "project/temp/file.md",
        ".git/config",
        "project/.git/hooks/file",
        "node_modules/package/file.md",
        "src/node_modules/lib/file.md",
        "notes/file.md",
        "regular/file.md",
        ".obsidian/config.md",
        ".obsidian/plugins/plugin.md",
    ]

    patterns = ["**/temp/**", "**/.git/**", "**/node_modules/**", "**/.obsidian/**"]

    print("Testing improved pattern matching:")
    print("=" * 50)

    def should_exclude(path_str, exclude_patterns):
        """Check if path should be excluded using multiple pattern variations."""
        path_obj = Path(path_str)

        for pattern in exclude_patterns:
            # Try multiple variations of the pattern
            variations = [
                pattern,  # Original pattern
                pattern.replace("**/", ""),  # Remove leading **/
                pattern.replace("/**", "/*"),  # Replace /** with /*
                pattern.replace("**/", "").replace("/**", "/*"),  # Both changes
            ]

            for variation in variations:
                if fnmatch.fnmatch(path_str, variation) or path_obj.match(variation):
                    return True, pattern, variation

        return False, None, None

    for path in test_paths:
        should_be_excluded, matched_pattern, matched_variation = should_exclude(
            path, patterns
        )

        if should_be_excluded:
            print(
                f"❌ {path} -> excluded by {matched_pattern} (using {matched_variation})"
            )
        else:
            print(f"✅ {path} -> included")


def test_path_parts_approach():
    """Test using path parts for pattern matching."""
    test_paths = [
        "temp/file.md",
        "project/temp/file.md",
        ".git/config",
        "project/.git/hooks/file",
        "node_modules/package/file.md",
        "src/node_modules/lib/file.md",
        "notes/file.md",
        "regular/file.md",
        ".obsidian/config.md",
        ".obsidian/plugins/plugin.md",
    ]

    exclude_dirs = ["temp", ".git", "node_modules", ".obsidian"]

    print("\nTesting path parts approach:")
    print("=" * 50)

    def should_exclude_by_parts(path_str, exclude_dirs):
        """Check if any part of the path matches exclude directories."""
        path_obj = Path(path_str)
        path_parts = path_obj.parts

        for part in path_parts:
            if part in exclude_dirs:
                return True, part

        return False, None

    for path in test_paths:
        should_be_excluded, matched_dir = should_exclude_by_parts(path, exclude_dirs)

        if should_be_excluded:
            print(f"❌ {path} -> excluded (contains '{matched_dir}')")
        else:
            print(f"✅ {path} -> included")


if __name__ == "__main__":
    test_improved_pattern_matching()
    test_path_parts_approach()

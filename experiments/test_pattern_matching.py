#!/usr/bin/env python3
"""Test pattern matching for exclude patterns."""

import fnmatch
from pathlib import Path


def test_fnmatch_patterns():
    """Test fnmatch behavior with various patterns."""
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

    print("Testing fnmatch patterns:")
    print("=" * 50)

    for path in test_paths:
        matches = []
        for pattern in patterns:
            if fnmatch.fnmatch(path, pattern):
                matches.append(pattern)

        if matches:
            print(f"❌ {path} -> matches: {matches}")
        else:
            print(f"✅ {path} -> no matches (should be included)")


def test_path_match_patterns():
    """Test Path.match behavior with various patterns."""
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

    print("\nTesting Path.match patterns:")
    print("=" * 50)

    for path in test_paths:
        path_obj = Path(path)
        matches = []
        for pattern in patterns:
            if path_obj.match(pattern):
                matches.append(pattern)

        if matches:
            print(f"❌ {path} -> matches: {matches}")
        else:
            print(f"✅ {path} -> no matches (should be included)")


if __name__ == "__main__":
    test_fnmatch_patterns()
    test_path_match_patterns()

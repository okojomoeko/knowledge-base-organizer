#!/usr/bin/env python3
"""実験: より効果的なexclude pattern実装の検証
日付: 2025-01-02
目的: fnmatchの制限を回避する最適なパターンマッチング手法を検証
"""

import fnmatch
from pathlib import Path


def test_fnmatch_limitations():
    """fnmatchの制限を詳細検証"""
    print("=== fnmatch制限の詳細検証 ===")

    test_cases = [
        # 先頭マッチの問題
        ("temp/file.md", "**/temp/**", False),  # 先頭にディレクトリがない
        ("project/temp/file.md", "**/temp/**", True),  # 先頭にディレクトリがある
        # 解決策候補
        ("temp/file.md", "temp/**", True),  # 直接マッチ
        ("temp/file.md", "*/temp/**", False),  # 1レベル上が必要
        ("temp/file.md", "temp/*", True),  # ファイル直接
    ]

    for path, pattern, expected in test_cases:
        result = fnmatch.fnmatch(path, pattern)
        status = "✅" if result == expected else "❌"
        print(f"{status} {path} vs {pattern} -> {result}")


def test_multiple_pattern_approach():
    """複数パターンアプローチの検証"""
    print("\n=== 複数パターンアプローチ検証 ===")

    def should_exclude_multi_pattern(path: str, base_pattern: str) -> bool:
        """複数パターンで除外判定"""
        patterns = [
            base_pattern,  # 基本パターン
            f"*/{base_pattern}",  # 1レベル上
            f"**/{base_pattern}",  # 任意レベル上
        ]

        return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)

    test_cases = [
        ("temp/file.md", "temp/**"),
        ("project/temp/file.md", "temp/**"),
        ("deep/project/temp/file.md", "temp/**"),
        (".obsidian/config.md", ".obsidian/**"),
        ("project/.obsidian/plugins/plugin.md", ".obsidian/**"),
        ("node_modules/package/file.md", "node_modules/**"),
        ("src/node_modules/lib/file.md", "node_modules/**"),
        ("regular/file.md", "temp/**"),
    ]

    for path, base_pattern in test_cases:
        result = should_exclude_multi_pattern(path, base_pattern)
        print(f"{path} vs {base_pattern} -> {result}")


def test_path_parts_approach():
    """パス部分チェックアプローチの検証"""
    print("\n=== パス部分チェックアプローチ検証 ===")

    def should_exclude_path_parts(path: str, exclude_dirs: list[str]) -> bool:
        """パス部分に除外ディレクトリが含まれるかチェック"""
        path_parts = Path(path).parts
        return any(exclude_dir in path_parts for exclude_dir in exclude_dirs)

    exclude_dirs = ["temp", ".obsidian", "node_modules", ".git"]

    test_cases = [
        "temp/file.md",
        "project/temp/file.md",
        "deep/project/temp/file.md",
        ".obsidian/config.md",
        "project/.obsidian/plugins/plugin.md",
        "node_modules/package/file.md",
        "src/node_modules/lib/file.md",
        ".git/config",
        "project/.git/hooks/file",
        "regular/file.md",
        "notes/daily/note.md",
    ]

    for path in test_cases:
        result = should_exclude_path_parts(path, exclude_dirs)
        print(f"{path} -> {'除外' if result else '含む'}")


def test_regex_approach():
    """正規表現アプローチの検証"""
    print("\n=== 正規表現アプローチ検証 ===")

    import re

    def should_exclude_regex(path: str, exclude_patterns: list[str]) -> bool:
        """正規表現で除外判定"""
        for pattern in exclude_patterns:
            if re.search(pattern, path):
                return True
        return False

    # 正規表現パターン（glob風を正規表現に変換）
    exclude_patterns = [
        r"(^|/)temp(/|$)",  # temp ディレクトリ
        r"(^|/)\.obsidian(/|$)",  # .obsidian ディレクトリ
        r"(^|/)node_modules(/|$)",  # node_modules ディレクトリ
        r"(^|/)\.git(/|$)",  # .git ディレクトリ
    ]

    test_cases = [
        "temp/file.md",
        "project/temp/file.md",
        "deep/project/temp/file.md",
        ".obsidian/config.md",
        "project/.obsidian/plugins/plugin.md",
        "node_modules/package/file.md",
        "src/node_modules/lib/file.md",
        ".git/config",
        "project/.git/hooks/file",
        "regular/file.md",
        "notes/daily/note.md",
        "templates/temp-note.md",  # false positive test
    ]

    for path in test_cases:
        result = should_exclude_regex(path, exclude_patterns)
        print(f"{path} -> {'除外' if result else '含む'}")


def test_performance_comparison():
    """各アプローチのパフォーマンス比較"""
    print("\n=== パフォーマンス比較 ===")

    import re
    import time

    test_paths = [
        "temp/file.md",
        "project/temp/file.md",
        "notes/file.md",
        ".obsidian/config.md",
        "project/.obsidian/plugins/plugin.md",
        "node_modules/package/file.md",
        "src/node_modules/lib/file.md",
        "regular/file.md",
    ] * 1000

    # 1. fnmatch multiple patterns
    def test_fnmatch_multi():
        patterns = [
            "temp/**",
            "*/temp/**",
            "**/temp/**",
            ".obsidian/**",
            "*/.obsidian/**",
            "**/.obsidian/**",
            "node_modules/**",
            "*/node_modules/**",
            "**/node_modules/**",
        ]
        results = []
        for path in test_paths:
            results.append(any(fnmatch.fnmatch(path, p) for p in patterns))
        return results

    # 2. Path parts approach
    def test_path_parts():
        exclude_dirs = ["temp", ".obsidian", "node_modules"]
        results = []
        for path in test_paths:
            path_parts = Path(path).parts
            results.append(
                any(exclude_dir in path_parts for exclude_dir in exclude_dirs)
            )
        return results

    # 3. Regex approach
    def test_regex():
        patterns = [
            re.compile(p)
            for p in [
                r"(^|/)temp(/|$)",
                r"(^|/)\.obsidian(/|$)",
                r"(^|/)node_modules(/|$)",
            ]
        ]
        results = []
        for path in test_paths:
            results.append(any(p.search(path) for p in patterns))
        return results

    # Performance test
    approaches = [
        ("fnmatch multiple", test_fnmatch_multi),
        ("path parts", test_path_parts),
        ("regex", test_regex),
    ]

    for name, func in approaches:
        start_time = time.time()
        results = func()
        elapsed = time.time() - start_time
        print(f"{name}: {elapsed:.4f}s ({len([r for r in results if r])} matches)")


def main():
    """実験実行"""
    print("=== より効果的なexclude pattern実装実験開始 ===")

    test_fnmatch_limitations()
    test_multiple_pattern_approach()
    test_path_parts_approach()
    test_regex_approach()
    test_performance_comparison()

    print("\n=== 実験結果まとめ ===")
    print("結論:")
    print("1. fnmatch単体では先頭マッチに制限あり")
    print("2. パス部分チェックが最もシンプルで高速")
    print("3. 正規表現は柔軟だが複雑")
    print("4. 推奨実装: パス部分チェック + 必要に応じてfnmatch補完")

    print("\n=== 実験完了 ===")


if __name__ == "__main__":
    main()

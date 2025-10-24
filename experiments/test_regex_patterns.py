#!/usr/bin/env python3
"""
実験: 外部リンク検出の正規表現パターンテスト
日付: 2025-10-24
目的: regular_linkパターンが複雑な外部リンクを正しく検出できるかテスト
"""

import re


def test_regular_link_patterns():
    """外部リンクパターンのテスト"""

    # 現在のパターン
    current_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    # テストケース
    test_cases = [
        # 通常の外部リンク
        "[AWS Organizations Documentation](https://docs.aws.amazon.com/organizations/)",
        # 問題のある外部リンク（WikiLink記法を含む）
        "[[Organizations]CloudWatchを別アカウントに共有する際にOrganization account selectorを使ってみた | DevelopersIO](https://dev.classmethod.jp/articles/cloudwatch-organizations-selector/)",
        # その他のテストケース
        "[Simple Link](https://example.com)",
        "[Link with [brackets] inside](https://example.com)",
        "[Link with [[double brackets]]](https://example.com)",
    ]

    print("=== 現在のパターンテスト ===")
    print(f"パターン: {current_pattern.pattern}")

    for i, test_case in enumerate(test_cases, 1):
        print(f"\nテストケース {i}:")
        print(f"入力: {test_case}")

        matches = current_pattern.findall(test_case)
        if matches:
            print(f"マッチ: {matches}")

            # 全体のマッチも確認
            full_matches = current_pattern.finditer(test_case)
            for match in full_matches:
                print(
                    f"全体マッチ: '{match.group()}' (位置: {match.start()}-{match.end()})"
                )
        else:
            print("マッチなし")

    # 改良されたパターンのテスト
    print("\n\n=== 改良パターンテスト ===")

    # より柔軟なパターン（ネストした括弧に対応）
    improved_pattern = re.compile(r"\[(?:[^\[\]]*(?:\[[^\]]*\][^\[\]]*)*)\]\([^)]+\)")

    print(f"改良パターン: {improved_pattern.pattern}")

    for i, test_case in enumerate(test_cases, 1):
        print(f"\nテストケース {i}:")
        print(f"入力: {test_case}")

        matches = improved_pattern.finditer(test_case)
        match_found = False
        for match in matches:
            print(f"マッチ: '{match.group()}' (位置: {match.start()}-{match.end()})")
            match_found = True

        if not match_found:
            print("マッチなし")


def test_exclusion_zone_detection():
    """除外ゾーン検出のテスト"""

    test_content = """# Test External Link Protection

This file mentions Organizations which should be linked in body text.

But this external link should NOT be modified:
[[Organizations]CloudWatchを別アカウントに共有する際にOrganization account selectorを使ってみた | DevelopersIO](https://dev.classmethod.jp/articles/cloudwatch-organizations-selector/)

And this regular external link should also be protected:
[AWS Organizations Documentation](https://docs.aws.amazon.com/organizations/)

Organizations is mentioned again here and should be linked.
"""

    # 現在のパターン
    regular_link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    print("=== 除外ゾーン検出テスト ===")

    lines = test_content.split("\n")
    for line_num, line in enumerate(lines, 1):
        print(f"\n行 {line_num}: {line}")

        matches = regular_link_pattern.finditer(line)
        for match in matches:
            print(
                f"  除外ゾーン検出: '{match.group()}' (位置: {match.start()}-{match.end()})"
            )


def main():
    """実験実行"""
    print("=== 外部リンク検出パターン実験開始 ===")

    test_regular_link_patterns()
    test_exclusion_zone_detection()

    print("\n=== 実験完了 ===")


if __name__ == "__main__":
    main()

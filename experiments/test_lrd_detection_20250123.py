#!/usr/bin/env python3
"""
実験: Link Reference Definition検出の改善
日付: 2025-01-23
目的: 実際のLRD形式に対応した正規表現パターンを開発
"""

import re


def test_current_pattern():
    """現在の正規表現パターンのテスト"""
    print("=== 現在のパターンテスト ===")

    # 現在の正規表現
    current_pattern = re.compile(
        r"^\[([^|\]]+)\|([^\]]+)\]:\s*([^\s]+)(?:\s+\"([^\"]+)\")?"
    )

    # 実際のLRDサンプル
    test_cases = [
        '[20230727234718|EC2]: 20230727234718 "Amazon Elastic Compute Cloud (Amazon EC2)"',
        '[20230730201034|ELB]: 20230730201034 "Elastic Load Balancing"',
        '[20230802000730|RDS]: 20230802000730 "Amazon Relational Database Service (Amazon RDS)"',
        '[20230709211042|AWS Organizations]: 20230709211042 "AWS Organizations"',
        '[20230624175527|CloudWatch]: 20230624175527 "Amazon CloudWatch"',
        '[20230816170731|CloudFormation]: 20230816170731 "AWS CloudFormation"',
        '[20230731234309|Amazon S3]: 20230731234309 "Amazon Simple Storage Service (Amazon S3)"',
        '[20230731234309|S3]: 20230731234309 "Amazon Simple Storage Service (Amazon S3)"',
        '[20230727220035|EBS]: 20230727220035 "Amazon Elastic Block Storage(EBS)"',
        '[20230817192133|KMS]: 20230817192133 "AWS Key Management Service (AWS KMS)"',
    ]

    print("現在の正規表現:", current_pattern.pattern)
    print()

    matches = 0
    for i, test_case in enumerate(test_cases, 1):
        match = current_pattern.match(test_case)
        if match:
            print(f"✅ {i}: MATCH - {test_case}")
            matches += 1
        else:
            print(f"❌ {i}: NO MATCH - {test_case}")

    print(f"\n結果: {matches}/{len(test_cases)} がマッチしました")
    return matches == len(test_cases)


def test_improved_pattern():
    """改善された正規表現パターンのテスト"""
    print("\n=== 改善されたパターンテスト ===")

    # 改善された正規表現（行の開始を要求しない）
    improved_pattern = re.compile(
        r"\[([^|\]]+)\|([^\]]+)\]:\s*([^\s]+)(?:\s+\"([^\"]+)\")?"
    )

    # 実際のLRDサンプル
    test_cases = [
        '[20230727234718|EC2]: 20230727234718 "Amazon Elastic Compute Cloud (Amazon EC2)"',
        '[20230730201034|ELB]: 20230730201034 "Elastic Load Balancing"',
        '[20230802000730|RDS]: 20230802000730 "Amazon Relational Database Service (Amazon RDS)"',
        '[20230709211042|AWS Organizations]: 20230709211042 "AWS Organizations"',
        '[20230624175527|CloudWatch]: 20230624175527 "Amazon CloudWatch"',
        '[20230816170731|CloudFormation]: 20230816170731 "AWS CloudFormation"',
        '[20230731234309|Amazon S3]: 20230731234309 "Amazon Simple Storage Service (Amazon S3)"',
        '[20230731234309|S3]: 20230731234309 "Amazon Simple Storage Service (Amazon S3)"',
        '[20230727220035|EBS]: 20230727220035 "Amazon Elastic Block Storage(EBS)"',
        '[20230817192133|KMS]: 20230817192133 "AWS Key Management Service (AWS KMS)"',
    ]

    print("改善された正規表現:", improved_pattern.pattern)
    print()

    matches = 0
    for i, test_case in enumerate(test_cases, 1):
        match = improved_pattern.search(test_case)  # searchを使用（行の途中でもマッチ）
        if match:
            print(f"✅ {i}: MATCH - {test_case}")
            print(f"    Groups: {match.groups()}")
            matches += 1
        else:
            print(f"❌ {i}: NO MATCH - {test_case}")

    print(f"\n結果: {matches}/{len(test_cases)} がマッチしました")
    return matches == len(test_cases)


def test_edge_cases():
    """エッジケースのテスト"""
    print("\n=== エッジケーステスト ===")

    improved_pattern = re.compile(
        r"\[([^|\]]+)\|([^\]]+)\]:\s*([^\s]+)(?:\s+\"([^\"]+)\")?"
    )

    edge_cases = [
        # タイトルなしのLRD
        "[20230727234718|EC2]: 20230727234718",
        # 複数のLRDが同じ行にある場合
        '[20230727234718|EC2]: 20230727234718 "Title1" [20230730201034|ELB]: 20230730201034 "Title2"',
        # 通常のWikiLinkとの区別
        "This is a [[20230727234718|EC2]] wikilink, not an LRD",
        # 通常のMarkdownリンクとの区別
        "This is a [EC2](20230727234718) markdown link, not an LRD",
    ]

    for i, test_case in enumerate(edge_cases, 1):
        matches = list(improved_pattern.finditer(test_case))
        print(f"Test {i}: {test_case}")
        if matches:
            for j, match in enumerate(matches):
                print(f"  Match {j + 1}: {match.group(0)}")
                print(f"    Groups: {match.groups()}")
        else:
            print("  No matches")
        print()


def main():
    """実験実行"""
    print("=== Link Reference Definition検出実験開始 ===")

    success1 = test_current_pattern()
    success2 = test_improved_pattern()
    test_edge_cases()

    if success2:
        print("🎉 改善されたパターンが全てのテストケースにマッチしました")
    else:
        print("❌ 改善が必要です")

    print("=== 実験完了 ===")


if __name__ == "__main__":
    main()

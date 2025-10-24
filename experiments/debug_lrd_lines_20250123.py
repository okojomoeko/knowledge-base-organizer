#!/usr/bin/env python3
"""
実験: LRD行の詳細デバッグ
日付: 2025-01-23
目的: 実際のファイル内のLRD行を詳しく調べる
"""

import re


def debug_lrd_lines():
    """LRD行の詳細デバッグ"""
    print("=== LRD行詳細デバッグ ===")

    # テストコンテンツ
    content = """# Amazon CloudWatch

- 統合的な運用監視サービス

## 機能

- CloudWatch Logs
- CloudWatch Events
- CloudWatch Alarms

This mentions Amazon API Gateway which should be linked.

---

[20230727234718|EC2]: 20230727234718 "Amazon Elastic Compute Cloud (Amazon EC2)"
[20230730201034|ELB]: 20230730201034 "Elastic Load Balancing"
[20230802000730|RDS]: 20230802000730 "Amazon Relational Database Service (Amazon RDS)"
"""

    lines = content.split("\n")

    # 現在の正規表現パターン
    link_ref_pattern = re.compile(
        r"^\[([^|\]]+)\|([^\]]+)\]:\s*([^\s]+)(?:\s+\"([^\"]+)\")?"
    )

    print("各行の詳細分析:")
    for line_num, line in enumerate(lines, 1):
        print(f"Line {line_num}: '{line}'")
        print(f"  Stripped: '{line.strip()}'")

        # 現在のパターンでマッチするかテスト
        match = link_ref_pattern.match(line.strip())
        if match:
            print(f"  ✅ MATCH: {match.groups()}")
        else:
            print("  ❌ NO MATCH")

        # LRDっぽい行かどうかチェック
        if "]:" in line:
            print("  🔍 Contains ']:', might be LRD")

        print()


def test_improved_lrd_detection():
    """改善されたLRD検出のテスト"""
    print("=== 改善されたLRD検出テスト ===")

    # テストコンテンツ
    content = """# Amazon CloudWatch

- 統合的な運用監視サービス

## 機能

- CloudWatch Logs
- CloudWatch Events
- CloudWatch Alarms

This mentions Amazon API Gateway which should be linked.

---

[20230727234718|EC2]: 20230727234718 "Amazon Elastic Compute Cloud (Amazon EC2)"
[20230730201034|ELB]: 20230730201034 "Elastic Load Balancing"
[20230802000730|RDS]: 20230802000730 "Amazon Relational Database Service (Amazon RDS)"
"""

    lines = content.split("\n")

    # 改善された正規表現パターン（行の開始を要求しない）
    improved_pattern = re.compile(
        r"\[([^|\]]+)\|([^\]]+)\]:\s*([^\s]+)(?:\s+\"([^\"]+)\")?"
    )

    print("改善されたパターンでの検出:")
    lrd_count = 0
    for line_num, line in enumerate(lines, 1):
        # finditerを使って行内の全てのマッチを検出
        matches = list(improved_pattern.finditer(line))
        if matches:
            print(f"Line {line_num}: '{line}'")
            for i, match in enumerate(matches):
                print(f"  Match {i + 1}: {match.group(0)}")
                print(f"    Groups: {match.groups()}")
                print(f"    Position: {match.start()}-{match.end()}")
                lrd_count += 1
            print()

    print(f"検出されたLRD数: {lrd_count}")


def main():
    """実験実行"""
    print("=== LRD行デバッグ実験開始 ===")

    debug_lrd_lines()
    test_improved_lrd_detection()

    print("=== 実験完了 ===")


if __name__ == "__main__":
    main()

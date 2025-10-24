#!/usr/bin/env python3
"""
実験: 除外ゾーン検出の詳細デバッグ
日付: 2025-01-23
目的: なぜLRDが除外ゾーンとして検出されないのかを調べる
"""

import re
import tempfile
from pathlib import Path

from knowledge_base_organizer.domain.services.link_analysis_service import \
    LinkAnalysisService


def debug_exclusion_zone_detection():
    """除外ゾーン検出の詳細デバッグ"""
    print("=== 除外ゾーン検出詳細デバッグ ===")

    # テスト用の一時ディレクトリを作成
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # LinkAnalysisServiceを初期化
        link_service = LinkAnalysisService(config_dir=temp_path / ".kiro")

        # テストコンテンツ（実際のファイル構造に合わせる）
        content = """---
title: Amazon CloudWatch
aliases: [CloudWatch,cloudwatch]
tags: [aws/management-governance/cloudwatch,dva]
id: 20230624175527
date: 2023-06-24
publish: false
---

# Amazon CloudWatch

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

        print("テストコンテンツ:")
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            print(f"{i:2d}: '{line}'")
        print()

        # 除外ゾーンを抽出
        exclusion_zones = link_service.extract_exclusion_zones(content)

        print("検出された除外ゾーン:")
        for i, zone in enumerate(exclusion_zones, 1):
            print(
                f"{i}. {zone.zone_type}: Line {zone.start_line}-{zone.end_line}, Col {zone.start_column}-{zone.end_column}"
            )
        print()

        # 手動でLRDパターンをテスト
        print("手動LRDパターンテスト:")
        link_ref_pattern = re.compile(
            r"\[([^|\]]+)\|([^\]]+)\]:\s*([^\s]+)(?:\s+\"([^\"]+)\")?"
        )

        for line_num, line in enumerate(lines, 1):
            matches = list(link_ref_pattern.finditer(line))
            if matches:
                print(f"Line {line_num}: '{line}'")
                for j, match in enumerate(matches):
                    print(f"  Match {j + 1}: '{match.group(0)}'")
                    print(f"    Position: {match.start()}-{match.end()}")
                    print(f"    Groups: {match.groups()}")

        # _compile_exclusion_patternsメソッドを直接テスト
        print("\n_compile_exclusion_patternsテスト:")
        patterns = link_service._compile_exclusion_patterns()
        print(f"LRDパターン: {patterns['link_ref'].pattern}")

        for line_num, line in enumerate(lines, 1):
            matches = list(patterns["link_ref"].finditer(line))
            if matches:
                print(f"Line {line_num}: '{line}'")
                for j, match in enumerate(matches):
                    print(f"  Match {j + 1}: '{match.group(0)}'")


def main():
    """実験実行"""
    print("=== 除外ゾーン検出デバッグ実験開始 ===")

    debug_exclusion_zone_detection()

    print("=== 実験完了 ===")


if __name__ == "__main__":
    main()

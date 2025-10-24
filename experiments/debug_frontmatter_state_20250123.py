#!/usr/bin/env python3
"""
実験: Frontmatter状態の詳細デバッグ
日付: 2025-01-23
目的: FrontmatterStateの動作を詳しく調べる
"""

import tempfile
from pathlib import Path

from knowledge_base_organizer.domain.services.link_analysis_service import (
    FrontmatterState, LinkAnalysisService)


def debug_frontmatter_state():
    """Frontmatter状態の詳細デバッグ"""
    print("=== Frontmatter状態詳細デバッグ ===")

    # テスト用の一時ディレクトリを作成
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # LinkAnalysisServiceを初期化
        link_service = LinkAnalysisService(config_dir=temp_path / ".kiro")

        # テストコンテンツ（MarkdownFile.contentと同じ）
        content = """# Test LRD Exclusion

This file mentions Amazon API Gateway which should be linked.

It also mentions EC2 and ELB which should NOT be linked because they appear in LRDs below.

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

        # 手動でfrontmatter処理をシミュレート
        exclusion_zones = []
        patterns = link_service._compile_exclusion_patterns()

        # FrontmatterStateを初期化
        frontmatter_state = FrontmatterState()

        print("行ごとのfrontmatter状態:")
        for line_num, line in enumerate(lines, 1):
            print(f"Line {line_num}: '{line}'")
            print(
                f"  処理前: start_line={frontmatter_state.start_line}, in_frontmatter={frontmatter_state.in_frontmatter}, processed={frontmatter_state.frontmatter_processed}"
            )

            # frontmatter処理
            link_service._handle_frontmatter(
                line, line_num, frontmatter_state, exclusion_zones
            )

            print(
                f"  処理後: start_line={frontmatter_state.start_line}, in_frontmatter={frontmatter_state.in_frontmatter}, processed={frontmatter_state.frontmatter_processed}"
            )

            # frontmatter内かどうかで処理をスキップするかチェック
            if frontmatter_state.in_frontmatter:
                print("  -> SKIP: frontmatter内のためスキップ")
            else:
                print("  -> PROCESS: 行レベル除外処理を実行")
                # LRDパターンをチェック
                for match in patterns["link_ref"].finditer(line):
                    print(
                        f"    LRD検出: '{match.group(0)}' at {match.start()}-{match.end()}"
                    )
            print()

        print(f"最終的な除外ゾーン数: {len(exclusion_zones)}")
        for i, zone in enumerate(exclusion_zones, 1):
            print(f"{i}. {zone.zone_type}: Line {zone.start_line}-{zone.end_line}")


def main():
    """実験実行"""
    print("=== Frontmatter状態デバッグ実験開始 ===")

    debug_frontmatter_state()

    print("=== 実験完了 ===")


if __name__ == "__main__":
    main()

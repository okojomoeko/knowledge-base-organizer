#!/usr/bin/env python3
"""
実験: LRDテスト失敗の原因調査
日付: 2025-01-23
目的: なぜLRD除外テストが失敗するのかを調べる
"""

import tempfile
from pathlib import Path

from knowledge_base_organizer.domain.services.link_analysis_service import \
    LinkAnalysisService
from knowledge_base_organizer.infrastructure.config import ProcessingConfig
from knowledge_base_organizer.infrastructure.file_repository import \
    FileRepository


def debug_lrd_test_failure():
    """LRDテスト失敗の原因を調査"""
    print("=== LRDテスト失敗原因調査 ===")

    # テスト用の一時ディレクトリを作成
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # テストケースと同じ内容でファイルを作成
        source_content = """---
title: Test LRD Exclusion
id: 20250123000001
tags: [test, lrd]
---

# Test LRD Exclusion

This file mentions Amazon API Gateway which should be linked.

It also mentions EC2 and ELB which should NOT be linked because they appear in LRDs below.

---

[20230727234718|EC2]: 20230727234718 "Amazon Elastic Compute Cloud (Amazon EC2)"
[20230730201034|ELB]: 20230730201034 "Elastic Load Balancing"
[20230802000730|RDS]: 20230802000730 "Amazon Relational Database Service (Amazon RDS)"
"""

        source_file = temp_path / "source.md"
        source_file.write_text(source_content, encoding="utf-8")

        # FileRepositoryとLinkAnalysisServiceを初期化
        config = ProcessingConfig.get_default_config()
        file_repo = FileRepository(config)
        link_service = LinkAnalysisService(config_dir=temp_path / ".kiro")

        # ファイルを読み込み
        markdown_file = file_repo.load_file(source_file)

        print("元のファイル内容（frontmatter含む）:")
        original_lines = source_content.split("\n")
        for i, line in enumerate(original_lines, 1):
            print(f"{i:2d}: '{line}'")
        print()

        print("MarkdownFile.content（body content）:")
        lines = markdown_file.content.split("\n")
        for i, line in enumerate(lines, 1):
            print(f"{i:2d}: '{line}'")
        print()

        # 除外ゾーンを抽出
        print("除外ゾーン検出対象のコンテンツ:")
        content_for_exclusion = markdown_file.content
        content_lines = content_for_exclusion.split("\n")
        for i, line in enumerate(content_lines, 1):
            marker = " <-- 7行目の---" if i == 7 and line.strip() == "---" else ""
            print(f"{i:2d}: '{line}'{marker}")
        print()

        exclusion_zones = link_service.extract_exclusion_zones(markdown_file.content)

        print("検出された除外ゾーン:")
        for i, zone in enumerate(exclusion_zones, 1):
            print(
                f"{i}. {zone.zone_type}: Line {zone.start_line}-{zone.end_line}, Col {zone.start_column}-{zone.end_column}"
            )
        print()

        # LRD除外ゾーンを確認
        lrd_zones = [z for z in exclusion_zones if z.zone_type == "link_ref_def"]
        print(f"LRD除外ゾーン数: {len(lrd_zones)}")

        # 各LRD行を詳細に確認
        for line_num, line in enumerate(lines, 1):
            if "]:" in line:
                print(f"LRD候補 Line {line_num}: '{line}'")
                # この行がLRD除外ゾーンに含まれているかチェック
                line_in_lrd_zone = any(
                    zone.start_line <= line_num <= zone.end_line for zone in lrd_zones
                )
                print(f"  LRD除外ゾーンに含まれる: {line_in_lrd_zone}")

        print()

        # 実際のリンク候補検索をテスト
        # ダミーのfile_registryを作成
        from knowledge_base_organizer.domain.models import (Frontmatter,
                                                            MarkdownFile)

        ec2_file = MarkdownFile(
            path=Path("test.md"),
            file_id="20230727234718",
            frontmatter=Frontmatter(
                title="Amazon Elastic Compute Cloud (Amazon EC2)",
                aliases=["EC2", "Amazon EC2"],
                id="20230727234718",
            ),
            content="# Amazon EC2\n\nContent about EC2.",
        )

        file_registry = {"20230727234718": ec2_file}

        candidates = link_service.find_link_candidates(
            markdown_file.content,
            file_registry,
            exclusion_zones,
            current_file_id=markdown_file.extract_file_id(),
        )

        print(f"検出されたリンク候補数: {len(candidates)}")
        for i, candidate in enumerate(candidates, 1):
            print(
                f"{i}. '{candidate.text}' -> {candidate.target_file_id} (Line {candidate.position.line_number}, Col {candidate.position.column_start}-{candidate.position.column_end})"
            )

        # LRD内のテキストがリンク候補に含まれているかチェック
        lrd_candidates = []
        for candidate in candidates:
            # LRD行（15-17行目）にあるかチェック
            if candidate.position.line_number >= 15:
                lrd_candidates.append(candidate)

        if lrd_candidates:
            print("\n❌ PROBLEM: LRD内のテキストがリンク候補に含まれています:")
            for candidate in lrd_candidates:
                print(
                    f"  - '{candidate.text}' at Line {candidate.position.line_number}"
                )
        else:
            print("\n✅ SUCCESS: LRD内のテキストは正しく除外されています")


def main():
    """実験実行"""
    print("=== LRDテスト失敗原因調査実験開始 ===")

    debug_lrd_test_failure()

    print("=== 実験完了 ===")


if __name__ == "__main__":
    main()

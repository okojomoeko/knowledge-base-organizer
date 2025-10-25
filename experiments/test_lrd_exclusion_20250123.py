#!/usr/bin/env python3
"""
実験: Link Reference Definition除外の検証
日付: 2025-01-23
目的: 実際のauto-link処理でLRDが正しく除外されているかテスト
"""

import tempfile
from pathlib import Path

from knowledge_base_organizer.domain.services.link_analysis_service import (
    LinkAnalysisService,
)
from knowledge_base_organizer.infrastructure.config import ProcessingConfig
from knowledge_base_organizer.infrastructure.file_repository import FileRepository


def test_lrd_exclusion():
    """LRD除外機能のテスト"""
    print("=== LRD除外機能テスト開始 ===")

    # テスト用の一時ディレクトリを作成
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # テスト用ファイルを作成（実際のLRDを含む）
        test_file1 = temp_path / "20230624175527.md"
        content1 = """---
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

        test_file1.write_text(content1, encoding="utf-8")

        # ターゲットファイルを作成
        target_file = temp_path / "20230730200042.md"
        target_content = """---
title: Amazon API Gateway
id: 20230730200042
tags: [aws, api]
---

# Amazon API Gateway

Amazon API Gateway is a fully managed service.
"""

        target_file.write_text(target_content, encoding="utf-8")

        # FileRepositoryとLinkAnalysisServiceを初期化
        config = ProcessingConfig.get_default_config()
        file_repo = FileRepository(config)
        link_service = LinkAnalysisService(config_dir=temp_path / ".kiro")

        # ファイルを読み込み
        files = file_repo.load_vault(temp_path)
        file_registry = {f.extract_file_id(): f for f in files if f.extract_file_id()}

        source_file = next(f for f in files if f.path.name == "20230624175527.md")

        print("元のコンテンツ:")
        print(source_file.content)
        print()

        # 除外ゾーンを抽出
        exclusion_zones = link_service.extract_exclusion_zones(source_file.content)

        print("検出された除外ゾーン:")
        for i, zone in enumerate(exclusion_zones, 1):
            print(f"{i}. {zone.zone_type}: Line {zone.start_line}-{zone.end_line}")
        print()

        # LRDが除外ゾーンに含まれているかチェック
        lrd_zones = [z for z in exclusion_zones if z.zone_type == "link_ref_def"]
        print(f"LRD除外ゾーン数: {len(lrd_zones)}")

        # リンク候補を検索
        candidates = link_service.find_link_candidates(
            source_file.content,
            file_registry,
            exclusion_zones,
            current_file_id=source_file.extract_file_id(),
        )

        print(f"検出されたリンク候補数: {len(candidates)}")
        for i, candidate in enumerate(candidates, 1):
            print(
                f"{i}. '{candidate.text}' -> {candidate.target_file_id} (Line {candidate.position.line_number})"
            )

        # LRD内のテキストがリンク候補に含まれていないかチェック
        lrd_texts = ["EC2", "ELB", "RDS"]  # LRD内のエイリアス
        lrd_candidates = [c for c in candidates if c.text in lrd_texts]

        if lrd_candidates:
            print(
                f"❌ FAILED: LRD内のテキストがリンク候補に含まれています: {[c.text for c in lrd_candidates]}"
            )
            return False
        print("✅ SUCCESS: LRD内のテキストは正しく除外されています")
        return True


def main():
    """実験実行"""
    print("=== LRD除外検証実験開始 ===")

    success = test_lrd_exclusion()

    if success:
        print("\n🎉 LRD除外機能が正常に動作しています")
    else:
        print("\n❌ LRD除外機能に問題があります")

    print("=== 実験完了 ===")


if __name__ == "__main__":
    main()

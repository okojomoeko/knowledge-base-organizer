#!/usr/bin/env python3
"""
実験: テスト用ヘルパー関数の作成と検証
日付: 2025-01-04
目的: CLI JSON出力を正しく解析するヘルパー関数を作成・検証
"""

import json
import re

from typer.testing import CliRunner

from knowledge_base_organizer.cli.main import app


def extract_json_from_cli_output(stdout: str) -> dict:
    """CLI出力からJSONを抽出してパースする"""
    # ANSIエスケープシーケンスを除去
    clean_stdout = re.sub(r"\x1b\[[0-9;]*m", "", stdout)

    # プログレスインジケーターを除去
    clean_stdout = re.sub(r"⠋.*?!", "", clean_stdout)

    # 行ごとに分割
    lines = clean_stdout.split("\n")
    json_lines = []
    json_started = False

    # JSON開始行を見つけて収集
    for line in lines:
        if line.strip().startswith("{"):
            json_started = True
        if json_started:
            json_lines.append(line)

    if not json_lines:
        raise ValueError("JSON output not found in CLI output")

    # JSON文字列を結合してパース
    json_text = "\n".join(json_lines).strip()
    return json.loads(json_text)


def test_helper_function():
    """ヘルパー関数をテスト"""
    print("=== ヘルパー関数テスト ===")

    runner = CliRunner()

    # detect-dead-linksコマンドをテスト
    result = runner.invoke(
        app,
        [
            "detect-dead-links",
            "tests/test-data/vaults/test-myvault",
            "--output-format",
            "json",
            "--limit",
            "2",
        ],
    )

    print(f"Exit code: {result.exit_code}")

    try:
        json_output = extract_json_from_cli_output(result.stdout)
        print("✅ detect-dead-links JSON解析成功!")
        print(f"Keys: {list(json_output.keys())}")
        print(f"Dead links count: {json_output['total_dead_links']}")
        return True
    except Exception as e:
        print(f"❌ detect-dead-links JSON解析失敗: {e}")
        return False


def test_with_filters():
    """フィルター付きでテスト"""
    print("\n=== フィルター付きテスト ===")

    runner = CliRunner()

    # フィルター付きコマンド
    result = runner.invoke(
        app,
        [
            "detect-dead-links",
            "tests/test-data/vaults/test-myvault",
            "--output-format",
            "json",
            "--only-with-suggestions",
            "--limit",
            "3",
        ],
    )

    try:
        json_output = extract_json_from_cli_output(result.stdout)
        print("✅ フィルター付きJSON解析成功!")

        # 全てのdead linksにsuggested_fixesがあることを確認
        all_have_suggestions = all(
            len(dl["suggested_fixes"]) > 0 for dl in json_output["dead_links"]
        )

        print(f"全てのdead linksにsuggestions有り: {all_have_suggestions}")
        print(f"Dead links count: {len(json_output['dead_links'])}")

        return all_have_suggestions
    except Exception as e:
        print(f"❌ フィルター付きJSON解析失敗: {e}")
        return False


def test_sorting():
    """ソート機能をテスト"""
    print("\n=== ソート機能テスト ===")

    runner = CliRunner()

    # ターゲット別ソート
    result = runner.invoke(
        app,
        [
            "detect-dead-links",
            "tests/test-data/vaults/test-myvault",
            "--output-format",
            "json",
            "--sort-by",
            "target",
            "--limit",
            "5",
        ],
    )

    try:
        json_output = extract_json_from_cli_output(result.stdout)
        print("✅ ソート付きJSON解析成功!")

        # ターゲットがソートされているかチェック
        targets = [dl["target"] for dl in json_output["dead_links"]]
        is_sorted = targets == sorted(targets)

        print(f"ターゲットがソート済み: {is_sorted}")
        print(f"Targets: {targets}")

        return is_sorted
    except Exception as e:
        print(f"❌ ソート付きJSON解析失敗: {e}")
        return False


def create_test_template():
    """テストテンプレートを作成"""
    print("\n=== テストテンプレート作成 ===")

    template = '''
def test_detect_dead_links_json_output(self) -> None:
    """Test detect-dead-links command with JSON output."""
    runner = CliRunner()
    vault_path = "tests/test-data/vaults/test-myvault"

    result = runner.invoke(
        app, ["detect-dead-links", vault_path, "--output-format", "json"]
    )

    # Should succeed despite warnings
    assert result.exit_code == 0

    # Extract JSON using helper function
    json_output = extract_json_from_cli_output(result.stdout)

    assert "detection_timestamp" in json_output
    assert "vault_path" in json_output
    assert "total_files_scanned" in json_output
    assert "dead_links" in json_output
    assert isinstance(json_output["dead_links"], list)

def test_detect_dead_links_with_limit(self) -> None:
    """Test detect-dead-links command with limit option."""
    runner = CliRunner()
    vault_path = "tests/test-data/vaults/test-myvault"

    result = runner.invoke(
        app,
        [
            "detect-dead-links",
            vault_path,
            "--output-format",
            "json",
            "--limit",
            "3",
        ],
    )

    assert result.exit_code == 0

    # Extract JSON using helper function
    json_output = extract_json_from_cli_output(result.stdout)

    # Should have at most 3 dead links
    assert len(json_output["dead_links"]) <= 3
    assert json_output["total_dead_links"] <= 3
'''

    print("テストテンプレート:")
    print(template)

    return template


def main():
    """実験実行"""
    print("=== テスト用ヘルパー関数の検証実験 ===")

    # ヘルパー関数の基本テスト
    basic_test = test_helper_function()

    # フィルター機能テスト
    filter_test = test_with_filters()

    # ソート機能テスト
    sort_test = test_sorting()

    # テストテンプレート作成
    template = create_test_template()

    print("\n=== 実験結果 ===")
    print(f"基本テスト: {'✅' if basic_test else '❌'}")
    print(f"フィルターテスト: {'✅' if filter_test else '❌'}")
    print(f"ソートテスト: {'✅' if sort_test else '❌'}")

    if all([basic_test, filter_test, sort_test]):
        print("\n✅ 全てのテストが成功！ヘルパー関数は正常に動作します")
        print("テストファイルを修正してヘルパー関数を使用できます")
    else:
        print("\n❌ 一部のテストが失敗しました")


if __name__ == "__main__":
    main()

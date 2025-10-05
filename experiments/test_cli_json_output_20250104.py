#!/usr/bin/env python3
"""
実験: CLI JSON出力の問題を解決する
日付: 2025-01-04
目的: detect-dead-linksコマンドのJSON出力がテストで正しく解析できない問題を調査・解決
"""

import json

from typer.testing import CliRunner

from knowledge_base_organizer.cli.main import app


def test_json_output_parsing():
    """JSON出力の解析問題を調査"""
    print("=== CLI JSON出力の実験開始 ===")

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "detect-dead-links",
            "tests/test-data/vaults/test-myvault",
            "--output-format",
            "json",
            "--limit",
            "1",
        ],
    )

    print(f"Exit code: {result.exit_code}")
    print(f"Stdout length: {len(result.stdout)}")

    # 生の出力を確認
    print("\n=== 生の出力（最初の500文字） ===")
    print(repr(result.stdout[:500]))

    # 行ごとに分析
    lines = result.stdout.strip().split("\n")
    print(f"\n=== 行数: {len(lines)} ===")

    json_started = False
    json_lines = []

    for i, line in enumerate(lines):
        if line.strip().startswith("{"):
            json_started = True
            print(f"JSON開始行 {i}: {line[:100]!r}")

        if json_started:
            json_lines.append(line)

    print(f"\nJSON行数: {len(json_lines)}")

    if json_lines:
        json_text = "\n".join(json_lines)
        print(f"JSON文字列長: {len(json_text)}")

        # ANSI エスケープシーケンスを除去
        import re

        clean_json = re.sub(r"\x1b\[[0-9;]*m", "", json_text)
        print(f"クリーンアップ後の長さ: {len(clean_json)}")

        # プログレスインジケーターを除去
        clean_json = re.sub(r"⠋.*?!", "", clean_json)
        clean_json = clean_json.strip()

        print(f"最終クリーンアップ後: {len(clean_json)}")
        print("最初の200文字:", repr(clean_json[:200]))

        try:
            parsed = json.loads(clean_json)
            print("✅ JSON解析成功!")
            print(f"キー: {list(parsed.keys())}")
            return parsed
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析エラー: {e}")
            print(f"エラー位置: {e.pos}")
            if e.pos < len(clean_json):
                start = max(0, e.pos - 50)
                end = min(len(clean_json), e.pos + 50)
                print(f"エラー周辺: {clean_json[start:end]!r}")

    return None


def test_analyze_command_comparison():
    """analyzeコマンドとの比較"""
    print("\n=== analyzeコマンドとの比較 ===")

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["analyze", "tests/test-data/vaults/test-myvault", "--output-format", "json"],
    )

    print(f"Analyze exit code: {result.exit_code}")

    # 同じ方法でJSON抽出
    lines = result.stdout.strip().split("\n")
    json_lines = []
    json_started = False

    for line in lines:
        if line.strip().startswith("{"):
            json_started = True
        if json_started:
            json_lines.append(line)

    if json_lines:
        json_text = "\n".join(json_lines)

        # クリーンアップ
        import re

        clean_json = re.sub(r"\x1b\[[0-9;]*m", "", json_text)
        clean_json = clean_json.strip()

        try:
            parsed = json.loads(clean_json)
            print("✅ Analyzeコマンド JSON解析成功!")
            return True
        except json.JSONDecodeError as e:
            print(f"❌ Analyzeコマンド JSON解析エラー: {e}")
            return False

    return False


def create_json_parser_helper():
    """テスト用のJSONパーサーヘルパー関数を作成"""
    print("\n=== JSONパーサーヘルパー関数の作成 ===")

    helper_code = '''
def extract_json_from_cli_output(stdout: str) -> dict:
    """CLI出力からJSONを抽出してパースする"""
    import json
    import re

    # 行ごとに分割
    lines = stdout.strip().split("\\n")
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

    # JSON文字列を結合
    json_text = "\\n".join(json_lines)

    # ANSIエスケープシーケンスを除去
    clean_json = re.sub(r"\\x1b\\[[0-9;]*m", "", json_text)

    # プログレスインジケーターを除去
    clean_json = re.sub(r"⠋.*?!", "", clean_json)
    clean_json = clean_json.strip()

    # JSONをパース
    return json.loads(clean_json)
'''

    print("ヘルパー関数コード:")
    print(helper_code)

    return helper_code


def main():
    """実験実行"""
    print("=== detect-dead-links CLI JSON出力実験 ===")

    # JSON出力の解析テスト
    result = test_json_output_parsing()

    # analyzeコマンドとの比較
    analyze_works = test_analyze_command_comparison()

    # ヘルパー関数の作成
    helper_code = create_json_parser_helper()

    print("\n=== 実験結果 ===")
    if result:
        print("✅ detect-dead-linksのJSON出力解析に成功")
    else:
        print("❌ detect-dead-linksのJSON出力解析に失敗")

    if analyze_works:
        print("✅ analyzeコマンドのJSON出力解析に成功")
    else:
        print("❌ analyzeコマンドのJSON出力解析に失敗")

    print("\n=== 結論 ===")
    print(
        "問題: CLI出力にANSIエスケープシーケンスとプログレスインジケーターが含まれている"
    )
    print("解決策: 正規表現でクリーンアップしてからJSONをパース")
    print("ヘルパー関数を使用してテストを修正する必要がある")


if __name__ == "__main__":
    main()

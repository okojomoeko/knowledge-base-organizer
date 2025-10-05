#!/usr/bin/env python3
"""
実験: 制御文字問題のデバッグ
日付: 2025-01-04
目的: JSON解析で制御文字エラーが発生する原因を特定・解決
"""

import json
import re

from typer.testing import CliRunner

from knowledge_base_organizer.cli.main import app


def debug_control_character_issue():
    """制御文字問題をデバッグ"""
    print("=== 制御文字問題デバッグ ===")

    runner = CliRunner()

    # limitなしで実行（テストと同じ条件）
    result = runner.invoke(
        app,
        [
            "detect-dead-links",
            "tests/test-data/vaults/test-myvault",
            "--output-format",
            "json",
        ],
    )

    print(f"Exit code: {result.exit_code}")
    print(f"Stdout length: {len(result.stdout)}")

    # ANSIエスケープシーケンスを除去
    clean_stdout = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)

    # プログレスインジケーターを除去
    clean_stdout = re.sub(r"⠋.*?!", "", clean_stdout)

    # JSON部分を抽出
    lines = clean_stdout.split("\n")
    json_lines = []
    json_started = False

    for line in lines:
        if line.strip().startswith("{"):
            json_started = True
        if json_started:
            json_lines.append(line)

    if json_lines:
        json_text = "\n".join(json_lines).strip()
        print(f"JSON text length: {len(json_text)}")

        # 制御文字をチェック
        control_chars = []
        for i, char in enumerate(json_text):
            if ord(char) < 32 and char not in ["\n", "\r", "\t"]:
                control_chars.append((i, char, ord(char)))

        print(f"制御文字数: {len(control_chars)}")
        if control_chars:
            print("最初の10個の制御文字:")
            for i, (pos, char, code) in enumerate(control_chars[:10]):
                context_start = max(0, pos - 20)
                context_end = min(len(json_text), pos + 20)
                context = json_text[context_start:context_end]
                print(f"  {i + 1}: pos={pos}, char={char!r}, code={code}")
                print(f"      context: {context!r}")

        # 制御文字を除去してJSONパースを試行
        clean_json = "".join(
            char for char in json_text if ord(char) >= 32 or char in ["\n", "\r", "\t"]
        )
        print(f"制御文字除去後の長さ: {len(clean_json)}")

        try:
            parsed = json.loads(clean_json)
            print("✅ 制御文字除去後のJSON解析成功!")
            return True, clean_json
        except json.JSONDecodeError as e:
            print(f"❌ 制御文字除去後もJSON解析失敗: {e}")
            print(f"エラー位置: {e.pos}")
            if e.pos < len(clean_json):
                start = max(0, e.pos - 50)
                end = min(len(clean_json), e.pos + 50)
                print(f"エラー周辺: {clean_json[start:end]!r}")
            return False, clean_json

    return False, ""


def test_with_limit():
    """limitありでテスト"""
    print("\n=== Limitありでテスト ===")

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "detect-dead-links",
            "tests/test-data/vaults/test-myvault",
            "--output-format",
            "json",
            "--limit",
            "5",
        ],
    )

    # 同じ処理
    clean_stdout = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
    clean_stdout = re.sub(r"⠋.*?!", "", clean_stdout)

    lines = clean_stdout.split("\n")
    json_lines = []
    json_started = False

    for line in lines:
        if line.strip().startswith("{"):
            json_started = True
        if json_started:
            json_lines.append(line)

    if json_lines:
        json_text = "\n".join(json_lines).strip()

        # 制御文字をチェック
        control_chars = []
        for i, char in enumerate(json_text):
            if ord(char) < 32 and char not in ["\n", "\r", "\t"]:
                control_chars.append((i, char, ord(char)))

        print(f"Limit付き制御文字数: {len(control_chars)}")

        try:
            parsed = json.loads(json_text)
            print("✅ Limit付きJSON解析成功!")
            return True
        except json.JSONDecodeError as e:
            print(f"❌ Limit付きJSON解析失敗: {e}")
            return False

    return False


def create_improved_helper():
    """改良されたヘルパー関数を作成"""
    print("\n=== 改良されたヘルパー関数 ===")

    helper_code = '''
def extract_json_from_cli_output(stdout: str) -> dict:
    """CLI出力からJSONを抽出してパースする（制御文字対応版）"""
    import json
    import re

    # ANSIエスケープシーケンスを除去
    clean_stdout = re.sub(r'\\x1b\\[[0-9;]*m', '', stdout)

    # プログレスインジケーターを除去
    clean_stdout = re.sub(r'⠋.*?!', '', clean_stdout)

    # 行ごとに分割
    lines = clean_stdout.split('\\n')
    json_lines = []
    json_started = False

    # JSON開始行を見つけて収集
    for line in lines:
        if line.strip().startswith('{'):
            json_started = True
        if json_started:
            json_lines.append(line)

    if not json_lines:
        raise ValueError("JSON output not found in CLI output")

    # JSON文字列を結合
    json_text = '\\n'.join(json_lines).strip()

    # 制御文字を除去（改行、タブ、復帰文字以外）
    clean_json = ''.join(
        char for char in json_text
        if ord(char) >= 32 or char in ['\\n', '\\r', '\\t']
    )

    # JSONをパース
    return json.loads(clean_json)
'''

    print("改良されたヘルパー関数:")
    print(helper_code)

    return helper_code


def test_improved_helper():
    """改良されたヘルパー関数をテスト"""
    print("\n=== 改良されたヘルパー関数テスト ===")

    def extract_json_from_cli_output_improved(stdout: str) -> dict:
        """CLI出力からJSONを抽出してパースする（制御文字対応版）"""
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

        # JSON文字列を結合
        json_text = "\n".join(json_lines).strip()

        # 制御文字を除去（改行、タブ、復帰文字以外）
        clean_json = "".join(
            char for char in json_text if ord(char) >= 32 or char in ["\n", "\r", "\t"]
        )

        # JSONをパース
        return json.loads(clean_json)

    # テスト実行
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "detect-dead-links",
            "tests/test-data/vaults/test-myvault",
            "--output-format",
            "json",
        ],
    )

    try:
        json_output = extract_json_from_cli_output_improved(result.stdout)
        print("✅ 改良されたヘルパー関数でJSON解析成功!")
        print(f"Keys: {list(json_output.keys())}")
        print(f"Dead links count: {json_output['total_dead_links']}")
        return True
    except Exception as e:
        print(f"❌ 改良されたヘルパー関数でJSON解析失敗: {e}")
        return False


def main():
    """実験実行"""
    print("=== 制御文字問題デバッグ実験 ===")

    # 制御文字問題をデバッグ
    success1, json_text = debug_control_character_issue()

    # limitありでテスト
    success2 = test_with_limit()

    # 改良されたヘルパー関数を作成
    helper_code = create_improved_helper()

    # 改良されたヘルパー関数をテスト
    success3 = test_improved_helper()

    print("\n=== 実験結果 ===")
    print(f"制御文字除去: {'✅' if success1 else '❌'}")
    print(f"Limit付き: {'✅' if success2 else '❌'}")
    print(f"改良ヘルパー: {'✅' if success3 else '❌'}")

    if success3:
        print("\n✅ 改良されたヘルパー関数で問題解決！")
        print("テストファイルのヘルパー関数を更新してください")
    else:
        print("\n❌ まだ問題が残っています")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
実験: CLI JSON出力の詳細デバッグ
日付: 2025-01-04
目的: なぜJSON開始行が見つからないかを詳細調査
"""

import json
import re

from typer.testing import CliRunner

from knowledge_base_organizer.cli.main import app


def debug_cli_output():
    """CLI出力を詳細にデバッグ"""
    print("=== CLI出力詳細デバッグ ===")

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

    # 全ての行を詳細に調査
    lines = result.stdout.split("\n")
    print(f"Total lines: {len(lines)}")

    for i, line in enumerate(lines):
        # 各行の詳細情報
        stripped = line.strip()
        if stripped:
            print(f"Line {i:2d}: len={len(line):3d}, stripped_len={len(stripped):3d}")
            print(f"         starts_with_{{: {stripped.startswith('{')}")
            print(f"         content: {line[:100]!r}")

            # JSON開始の可能性をチェック
            if "{" in line:
                print(f"         *** Contains '{{' at position {line.find('{')}")

            if i > 50:  # 最初の50行だけ表示
                print("... (truncated)")
                break

    return result.stdout


def test_different_json_detection():
    """異なるJSON検出方法をテスト"""
    print("\n=== 異なるJSON検出方法のテスト ===")

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

    stdout = result.stdout

    # 方法1: 単純に'{' を含む行を探す
    print("方法1: '{' を含む行を探す")
    lines_with_brace = [i for i, line in enumerate(stdout.split("\n")) if "{" in line]
    print(f"'{{' を含む行: {lines_with_brace}")

    # 方法2: 正規表現で JSON らしきパターンを探す
    print("\n方法2: JSONパターンを正規表現で探す")
    json_pattern = re.compile(r"\{[\s\S]*\}", re.MULTILINE)
    matches = json_pattern.findall(stdout)
    print(f"JSONパターンマッチ数: {len(matches)}")

    if matches:
        for i, match in enumerate(matches):
            print(f"Match {i}: length={len(match)}, first_100={match[:100]!r}")

    # 方法3: ANSIエスケープを先に除去してから探す
    print("\n方法3: ANSIエスケープを先に除去")
    clean_stdout = re.sub(r"\x1b\[[0-9;]*m", "", stdout)
    clean_lines = clean_stdout.split("\n")

    json_start_lines = []
    for i, line in enumerate(clean_lines):
        if line.strip().startswith("{"):
            json_start_lines.append(i)
            print(f"Clean line {i} starts with '{{': {line[:100]!r}")

    print(f"クリーンアップ後のJSON開始行: {json_start_lines}")

    # 方法4: プログレスインジケーターも除去
    print("\n方法4: プログレスインジケーターも除去")
    super_clean = re.sub(r"⠋.*?!", "", clean_stdout)
    super_clean_lines = super_clean.split("\n")

    for i, line in enumerate(super_clean_lines):
        if line.strip().startswith("{"):
            print(f"Super clean line {i} starts with '{{': {line[:100]!r}")

            # この行から最後まで取得してJSONパースを試行
            json_candidate = "\n".join(super_clean_lines[i:])
            json_candidate = json_candidate.strip()

            try:
                parsed = json.loads(json_candidate)
                print("✅ JSON解析成功!")
                print(f"Keys: {list(parsed.keys())}")
                return parsed
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析失敗: {e}")
                print(f"候補の最初の200文字: {json_candidate[:200]!r}")

    return None


def test_file_output():
    """ファイル出力を使った場合のテスト"""
    print("\n=== ファイル出力テスト ===")

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
            "--output",
            "test_output.json",
        ],
    )

    print(f"File output exit code: {result.exit_code}")
    print(f"Stdout: {result.stdout[:200]!r}")

    # ファイルが作成されたかチェック
    import os

    if os.path.exists("test_output.json"):
        print("✅ ファイルが作成された")
        with open("test_output.json") as f:
            content = f.read()
            print(f"ファイル内容長: {len(content)}")
            try:
                parsed = json.loads(content)
                print("✅ ファイルからのJSON解析成功!")
                print(f"Keys: {list(parsed.keys())}")
                return parsed
            except json.JSONDecodeError as e:
                print(f"❌ ファイルからのJSON解析失敗: {e}")

        # クリーンアップ
        os.remove("test_output.json")
    else:
        print("❌ ファイルが作成されなかった")

    return None


def main():
    """実験実行"""
    print("=== CLI JSON出力詳細デバッグ実験 ===")

    # 詳細デバッグ
    stdout = debug_cli_output()

    # 異なる検出方法のテスト
    result1 = test_different_json_detection()

    # ファイル出力テスト
    result2 = test_file_output()

    print("\n=== 実験結果まとめ ===")
    if result1:
        print("✅ stdout からのJSON抽出に成功")
    else:
        print("❌ stdout からのJSON抽出に失敗")

    if result2:
        print("✅ ファイル出力からのJSON読み込みに成功")
    else:
        print("❌ ファイル出力からのJSON読み込みに失敗")


if __name__ == "__main__":
    main()

"""CLI テスト用のユーティリティ関数"""

import contextlib
import glob
import json
import re
from pathlib import Path


def extract_json_from_cli_output(stdout: str) -> dict:
    """CLI出力からJSONを抽出してパースする(制御文字対応版)

    Args:
        stdout: CLI コマンドの標準出力

    Returns:
        パースされたJSONオブジェクト

    Raises:
        ValueError: JSON出力が見つからない場合
        json.JSONDecodeError: JSON解析に失敗した場合
    """
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

    # 制御文字を除去(改行、タブ、復帰文字以外)
    clean_json = "".join(
        char for char in json_text if ord(char) >= 32 or char in ["\n", "\r", "\t"]
    )

    # JSONをパース
    return json.loads(clean_json)


def save_test_output(content: str, filename: str) -> None:
    """テスト出力を適切なディレクトリに保存する

    Args:
        content: 保存する内容
        filename: ファイル名
    """
    # tests/test_output_results ディレクトリを作成
    output_dir = Path(__file__).parent.parent / "test_output_results"
    output_dir.mkdir(exist_ok=True)

    # ファイルを保存
    output_file = output_dir / filename
    with Path(output_file).open("w", encoding="utf-8") as f:
        f.write(content)


def cleanup_test_files(pattern: str = "test_*.json") -> None:
    """テスト実行で生成されたファイルをクリーンアップする

    Args:
        pattern: 削除するファイルのパターン(安全のため、test_* で始まるファイルのみ)
    """
    # 安全のため、特定のテスト出力ファイルのみを削除
    safe_patterns = [
        "test_*.json",
        "test_*.csv",
        "dead_links_test.*",
        "filtered_dead_links.*",
        "test_output.*",
    ]

    # 指定されたパターンが安全なパターンに含まれているかチェック
    if pattern not in safe_patterns:
        # 安全でないパターンの場合は何もしない
        return

    # プロジェクトルートの不要なファイルを削除
    project_root = Path(__file__).parent.parent.parent
    for file_path in project_root.glob(pattern):
        with contextlib.suppress(FileNotFoundError):
            file_path.unlink()

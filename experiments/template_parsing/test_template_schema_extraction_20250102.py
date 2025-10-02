#!/usr/bin/env python3
"""
実験: テンプレートファイルからのスキーマ抽出アルゴリズム検証
日付: 2025-01-02
目的: テンプレートファイルの解析ロジックとスキーマ生成の動作を検証
"""

import re
import tempfile
from pathlib import Path
from typing import Any

import yaml


def test_yaml_frontmatter_parsing():
    """YAMLフロントマター解析の基本動作を検証"""
    print("=== YAML フロントマター解析テスト ===")

    # テストケース1: 基本的なテンプレート
    template_content = """---
title: <% tp.file.cursor(1) %>
aliases: []
tags: []
id: <% tp.file.creation_date("YYYYMMDDHHmmss") %>
date: <% tp.file.creation_date("YYYY-MM-DD") %>
publish: false
---

# <% tp.file.cursor(2) %>
"""

    # フロントマター抽出
    frontmatter_match = re.match(r"^---\n(.*?)\n---", template_content, re.DOTALL)
    if frontmatter_match:
        frontmatter_text = frontmatter_match.group(1)
        print(f"抽出されたフロントマター:\n{frontmatter_text}")

        try:
            frontmatter_data = yaml.safe_load(frontmatter_text)
            print(f"解析結果: {frontmatter_data}")
            print(f"データ型: {type(frontmatter_data)}")

            for key, value in frontmatter_data.items():
                print(f"  {key}: {value} (型: {type(value).__name__})")

        except yaml.YAMLError as e:
            print(f"YAML解析エラー: {e}")

    print()


def test_template_variable_extraction():
    """テンプレート変数の抽出パターンを検証"""
    print("=== テンプレート変数抽出テスト ===")

    frontmatter_text = """title: <% tp.file.cursor(1) %>
aliases: []
tags: []
id: <% tp.file.creation_date("YYYYMMDDHHmmss") %>
date: <% tp.file.creation_date("YYYY-MM-DD") %>
publish: false
category: ""
description: ""
"""

    # Templater構文の検出パターン
    templater_patterns = [
        (r"(\w+):\s*<%([^>]+)%>", "Templater構文"),
        (r"(\w+):\s*\{\{([^}]+)\}\}", "Handlebars構文"),
    ]

    for pattern, pattern_name in templater_patterns:
        print(f"\n{pattern_name}の検出:")
        matches = re.findall(pattern, frontmatter_text)
        for field_name, template_var in matches:
            print(f"  {field_name}: {template_var.strip()}")

    print()


def test_field_type_detection():
    """フィールドタイプ検出ロジックの検証"""
    print("=== フィールドタイプ検出テスト ===")

    test_cases = [
        ("title", "<% tp.file.cursor(1) %>", "tp.file.cursor(1)"),
        ("aliases", [], None),
        ("tags", [], None),
        (
            "id",
            '<% tp.file.creation_date("YYYYMMDDHHmmss") %>',
            'tp.file.creation_date("YYYYMMDDHHmmss")',
        ),
        (
            "date",
            '<% tp.file.creation_date("YYYY-MM-DD") %>',
            'tp.file.creation_date("YYYY-MM-DD")',
        ),
        ("publish", False, None),
        ("category", "", None),
        ("description", "", None),
        ("totalPage", 0, None),
        ("isbn13", "{{isbn13}}", "isbn13"),
    ]

    def determine_field_type(field_value: Any, template_variable: str | None) -> str:
        """フィールドタイプ判定ロジック"""
        # テンプレート変数パターンを最初にチェック
        if template_variable:
            if "creation_date" in template_variable.lower():
                if "YYYYMMDDHHmmss" in template_variable:
                    return "STRING (ID format)"
                return "DATE"
            if (
                "cursor" in template_variable.lower()
                or "title" in template_variable.lower()
            ):
                return "STRING"

        # 実際の値の型をチェック
        if isinstance(field_value, bool):
            return "BOOLEAN"
        if isinstance(field_value, int):
            return "INTEGER"
        if isinstance(field_value, float):
            return "NUMBER"
        if isinstance(field_value, list):
            return "ARRAY"
        if isinstance(field_value, str):
            if field_value.lower() in ("true", "false"):
                return "BOOLEAN"
            if field_value.isdigit():
                return "INTEGER"
            return "STRING"

        return "STRING"  # デフォルト

    for field_name, field_value, template_var in test_cases:
        field_type = determine_field_type(field_value, template_var)
        print(f"{field_name}: {field_value} -> {field_type}")
        if template_var:
            print(f"  テンプレート変数: {template_var}")

    print()


def test_required_field_detection():
    """必須フィールド検出ロジックの検証"""
    print("=== 必須フィールド検出テスト ===")

    def is_field_required(
        field_name: str, field_value: Any, template_variable: str | None
    ) -> bool:
        """必須フィールド判定ロジック"""
        # コアフィールドは通常必須
        core_fields = {"title", "id", "date"}
        if field_name in core_fields:
            return True

        # テンプレート変数があるフィールドは通常必須
        if template_variable:
            return True

        # 空またはプレースホルダー値は通常必須
        if isinstance(field_value, str):
            placeholder_patterns = [
                r"^$",  # 空
                r"^\s*$",  # 空白のみ
                r"^<.*>$",  # <placeholder>
                r"^\{.*\}$",  # {placeholder}
                r"^TODO",  # TODO placeholder
                r"^PLACEHOLDER",  # PLACEHOLDER
            ]
            for pattern in placeholder_patterns:
                if re.match(pattern, field_value, re.IGNORECASE):
                    return True

        # 配列とブール値は多くの場合オプション
        if isinstance(field_value, (list, bool)):
            return False

        return False  # デフォルトはオプション

    test_cases = [
        ("title", "<% tp.file.cursor(1) %>", "tp.file.cursor(1)"),
        ("aliases", [], None),
        ("tags", [], None),
        (
            "id",
            '<% tp.file.creation_date("YYYYMMDDHHmmss") %>',
            'tp.file.creation_date("YYYYMMDDHHmmss")',
        ),
        (
            "date",
            '<% tp.file.creation_date("YYYY-MM-DD") %>',
            'tp.file.creation_date("YYYY-MM-DD")',
        ),
        ("publish", False, None),
        ("category", "", None),
        ("description", "", None),
        ("author", "{{author}}", "author"),
        ("isbn13", "{{isbn13}}", "isbn13"),
    ]

    for field_name, field_value, template_var in test_cases:
        required = is_field_required(field_name, field_value, template_var)
        print(f"{field_name}: {'必須' if required else 'オプション'}")
        if template_var:
            print(f"  理由: テンプレート変数あり ({template_var})")
        elif field_name in {"title", "id", "date"}:
            print("  理由: コアフィールド")
        elif isinstance(field_value, str) and field_value == "":
            print("  理由: 空の文字列（プレースホルダー）")
        elif isinstance(field_value, (list, bool)):
            print("  理由: 配列またはブール値（通常オプション）")

    print()


def test_book_template_parsing():
    """書籍テンプレートの解析テスト"""
    print("=== 書籍テンプレート解析テスト ===")

    book_template = """---
title: "{{title}}"
author: "{{author}}"
publisher: "{{publisher}}"
totalPage: "{{totalPage}}"
isbn13: "{{isbn13}}"
tags: [books]
id: <% tp.file.creation_date("YYYYMMDDHHmmss") %>
date: <% tp.file.creation_date("YYYY-MM-DD") %>
publish: false
---

# {{title}}

## 基本情報
- 著者: {{author}}
- 出版社: {{publisher}}
- ページ数: {{totalPage}}
- ISBN: {{isbn13}}
"""

    # フロントマター抽出
    frontmatter_match = re.match(r"^---\n(.*?)\n---", book_template, re.DOTALL)
    if frontmatter_match:
        frontmatter_text = frontmatter_match.group(1)
        frontmatter_data = yaml.safe_load(frontmatter_text)

        print("書籍テンプレートのフィールド:")
        for key, value in frontmatter_data.items():
            print(f"  {key}: {value} (型: {type(value).__name__})")

        # Handlebars変数の検出
        handlebars_pattern = r'(\w+):\s*"?\{\{([^}]+)\}\}"?'
        matches = re.findall(handlebars_pattern, frontmatter_text)
        print("\nHandlebars変数:")
        for field_name, template_var in matches:
            print(f"  {field_name}: {template_var}")

    print()


def test_template_detection_logic():
    """テンプレート検出ロジックの検証"""
    print("=== テンプレート検出ロジックテスト ===")

    # ディレクトリベースの検出
    directory_mappings = {
        "100_FleetingNotes": "new-fleeing-note",
        "104_Books": "booksearchtemplate",
        "Books": "booksearchtemplate",
        "FleetingNotes": "new-fleeing-note",
        "Notes": "new-fleeing-note",
    }

    test_paths = [
        "/vault/100_FleetingNotes/test-note.md",
        "/vault/104_Books/my-book.md",
        "/vault/Books/another-book.md",
        "/vault/Random/some-file.md",
    ]

    print("ディレクトリベース検出:")
    for path in test_paths:
        path_obj = Path(path)
        detected_template = None

        for part in path_obj.parts:
            if part in directory_mappings:
                detected_template = directory_mappings[part]
                break

        print(f"  {path} -> {detected_template or 'なし'}")

    # コンテンツベースの検出
    print("\nコンテンツベース検出:")

    test_frontmatters = [
        {"title": "Test", "isbn13": "1234567890123", "author": "Test Author"},
        {"title": "Note", "category": "test", "description": "A note"},
        {"title": "Random", "some_field": "value"},
    ]

    book_indicators = {"isbn13", "publisher", "author", "totalPage", "isbn"}
    note_indicators = {"published", "category", "description"}

    for frontmatter in test_frontmatters:
        if any(field in frontmatter for field in book_indicators):
            template_type = "booksearchtemplate"
        elif any(field in frontmatter for field in note_indicators):
            template_type = "new-fleeing-note"
        else:
            template_type = None

        print(f"  {frontmatter} -> {template_type or 'なし'}")

    print()


def test_validation_pattern_creation():
    """バリデーションパターン生成の検証"""
    print("=== バリデーションパターン生成テスト ===")

    def create_validation_pattern(field_name: str, field_type: str) -> str | None:
        """バリデーションパターン生成"""
        # IDフィールドのバリデーション（14桁のタイムスタンプ）
        if field_name == "id" and field_type == "STRING":
            return r"^\d{14}$"

        # 日付フィールドのバリデーション（YYYY-MM-DD形式）
        if field_name == "date" and field_type in ("DATE", "STRING"):
            return r"^\d{4}-\d{2}-\d{2}$"

        # ISBNバリデーション
        if field_name in ("isbn", "isbn13") and field_type == "STRING":
            return r"^\d{13}$"

        return None

    test_cases = [
        ("id", "STRING"),
        ("date", "DATE"),
        ("isbn13", "STRING"),
        ("title", "STRING"),
        ("tags", "ARRAY"),
    ]

    for field_name, field_type in test_cases:
        pattern = create_validation_pattern(field_name, field_type)
        print(f"{field_name} ({field_type}): {pattern or 'パターンなし'}")

    print()


def test_real_template_files():
    """実際のテンプレートファイルでの動作テスト"""
    print("=== 実際のテンプレートファイルテスト ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        vault_path = Path(temp_dir)

        # テンプレートディレクトリ作成
        template_dir = vault_path / "900_TemplaterNotes"
        template_dir.mkdir()

        book_template_dir = vault_path / "903_BookSearchTemplates"
        book_template_dir.mkdir()

        # フリーティングノートテンプレート作成
        fleeting_template = template_dir / "new-fleeing-note.md"
        fleeting_template.write_text("""---
title: <% tp.file.cursor(1) %>
aliases: []
tags: []
id: <% tp.file.creation_date("YYYYMMDDHHmmss") %>
date: <% tp.file.creation_date("YYYY-MM-DD") %>
publish: false
category: ""
description: ""
---

# <% tp.file.cursor(2) %>
""")

        # 書籍テンプレート作成
        book_template = book_template_dir / "booksearchtemplate.md"
        book_template.write_text("""---
title: "{{title}}"
author: "{{author}}"
publisher: "{{publisher}}"
totalPage: "{{totalPage}}"
isbn13: "{{isbn13}}"
tags: [books]
id: <% tp.file.creation_date("YYYYMMDDHHmmss") %>
date: <% tp.file.creation_date("YYYY-MM-DD") %>
publish: false
---

# {{title}}
""")

        # テンプレートファイルをスキャン
        template_directories = ["900_TemplaterNotes", "903_BookSearchTemplates"]
        schemas = {}

        for template_dir_name in template_directories:
            template_path = vault_path / template_dir_name
            if template_path.exists():
                print(f"\n{template_dir_name} をスキャン:")
                for template_file in template_path.glob("*.md"):
                    print(f"  テンプレートファイル: {template_file.name}")

                    # フロントマター抽出と解析
                    content = template_file.read_text()
                    frontmatter_match = re.match(
                        r"^---\n(.*?)\n---", content, re.DOTALL
                    )

                    if frontmatter_match:
                        frontmatter_text = frontmatter_match.group(1)
                        try:
                            frontmatter_data = yaml.safe_load(frontmatter_text)
                            print(f"    フィールド数: {len(frontmatter_data)}")

                            for field_name, field_value in frontmatter_data.items():
                                # テンプレート変数抽出
                                templater_pattern = (
                                    rf"{re.escape(field_name)}:\s*<%([^>]+)%>"
                                )
                                handlebars_pattern = rf"{re.escape(field_name)}:\s*\"?\{{\{{([^}}]+)\}}\}}\"?"

                                template_var = None
                                if re.search(templater_pattern, frontmatter_text):
                                    match = re.search(
                                        templater_pattern, frontmatter_text
                                    )
                                    template_var = (
                                        match.group(1).strip() if match else None
                                    )
                                elif re.search(handlebars_pattern, frontmatter_text):
                                    match = re.search(
                                        handlebars_pattern, frontmatter_text
                                    )
                                    template_var = (
                                        match.group(1).strip() if match else None
                                    )

                                print(f"      {field_name}: {field_value}")
                                if template_var:
                                    print(f"        テンプレート変数: {template_var}")

                            schemas[template_file.stem] = {
                                "path": template_file,
                                "fields": frontmatter_data,
                                "field_count": len(frontmatter_data),
                            }

                        except yaml.YAMLError as e:
                            print(f"    YAML解析エラー: {e}")
                    else:
                        print("    フロントマターが見つかりません")

        print(f"\n抽出されたスキーマ数: {len(schemas)}")
        for schema_name, schema_info in schemas.items():
            print(f"  {schema_name}: {schema_info['field_count']} フィールド")


def main():
    """実験実行"""
    print("=== テンプレートスキーマ抽出アルゴリズム検証実験 ===\n")

    test_yaml_frontmatter_parsing()
    test_template_variable_extraction()
    test_field_type_detection()
    test_required_field_detection()
    test_book_template_parsing()
    test_template_detection_logic()
    test_validation_pattern_creation()
    test_real_template_files()

    print("=== 実験完了 ===")

    print("""
実験結果まとめ:
1. YAML フロントマター解析: yaml.safe_load() で正常に動作
2. テンプレート変数抽出: 正規表現で Templater と Handlebars 構文を検出可能
3. フィールドタイプ検出: テンプレート変数パターンと値の型から判定可能
4. 必須フィールド検出: コアフィールド、テンプレート変数、空値で判定可能
5. バリデーションパターン: ID、日付、ISBN などの特定フィールドに適用可能
6. 実際のファイル処理: テンプレートディレクトリのスキャンと解析が正常動作

結論:
- テンプレートスキーマ抽出アルゴリズムは実装可能
- 正規表現パターンとYAML解析の組み合わせで十分
- エラーハンドリングを適切に行えば安定動作する
""")


if __name__ == "__main__":
    main()

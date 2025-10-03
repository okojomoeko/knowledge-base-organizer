# タグ管理システム使用ガイド

## 概要

Knowledge Base Organizerのタグ管理システムは、インテリジェントなタグ提案とパターン管理を提供します。このシステムにより、以下が可能になります：

- **パターンベースのタグ提案**: コンテンツ分析に基づく自動タグ提案
- **タグパターンの管理**: カスタムタグパターンの追加・編集・削除
- **Vault分析**: 既存タグの統計分析と関係性の発見
- **LLM統合準備**: LLMによる自動化のためのデータエクスポート

## 基本的な使用方法

### 1. タグパターンの一覧表示

```bash
# テーブル形式で表示
uv run python -m knowledge_base_organizer tags list-patterns

# ツリー形式で表示
uv run python -m knowledge_base_organizer tags list-patterns --format tree

# JSON形式で表示
uv run python -m knowledge_base_organizer tags list-patterns --format json

# 特定のカテゴリのみ表示
uv run python -m knowledge_base_organizer tags list-patterns --category programming_languages
```

### 2. カスタムタグパターンの追加

```bash
# 新しいタグパターンを追加
uv run python -m knowledge_base_organizer tags add-pattern \
  "machine_learning" \
  "ml_pattern" \
  "machine-learning" \
  "machine learning,ml,neural network,deep learning,ai" \
  --description "Machine learning and AI content" \
  --weight 1.2
```

### 3. タグパターンの検索

```bash
# キーワードでパターンを検索
uv run python -m knowledge_base_organizer tags search-patterns "python"
uv run python -m knowledge_base_organizer tags search-patterns "database"
```

### 4. Vaultのタグ分析

```bash
# Vault全体のタグを分析
uv run python -m knowledge_base_organizer tags analyze-vault /path/to/vault

# 詳細分析を表示
uv run python -m knowledge_base_organizer tags analyze-vault /path/to/vault --details

# 分析結果をJSONファイルに保存
uv run python -m knowledge_base_organizer tags analyze-vault /path/to/vault --output analysis.json
```

### 5. 個別ファイルのタグ提案

```bash
# 特定のファイルに対するタグ提案
uv run python -m knowledge_base_organizer tags suggest-tags /path/to/file.md

# 信頼度スコアを表示
uv run python -m knowledge_base_organizer tags suggest-tags /path/to/file.md --show-confidence

# 最小信頼度を設定
uv run python -m knowledge_base_organizer tags suggest-tags /path/to/file.md --min-confidence 0.5
```

### 6. 関連タグの表示

```bash
# 特定のタグに関連するタグを表示
uv run python -m knowledge_base_organizer tags related-tags "programming" --vault /path/to/vault

# 関係性の強度を調整
uv run python -m knowledge_base_organizer tags related-tags "programming" --min-strength 0.5
```

### 7. LLM用データのエクスポート

```bash
# LLM用にタグパターンをエクスポート
uv run python -m knowledge_base_organizer tags export-for-llm --output llm_patterns.json
```

## プログラムでの使用方法

### 基本的な使用例

```python
from pathlib import Path
from knowledge_base_organizer.domain.services.frontmatter_enhancement_service import FrontmatterEnhancementService
from knowledge_base_organizer.domain.models import MarkdownFile, Frontmatter

# サービスの初期化
service = FrontmatterEnhancementService()

# ファイルの作成（例）
content = """---
title: Python Tutorial
---

# Python Programming

This tutorial covers Python basics, Django framework, and NumPy.
"""

frontmatter = Frontmatter(title="Python Tutorial")
file = MarkdownFile(path=Path("tutorial.md"), frontmatter=frontmatter, content=content)

# タグ提案の取得
suggestions = service.get_tag_suggestions_with_confidence(file)
print(f"Suggested tags: {suggestions}")

# インテリジェントタグ提案
intelligent_tags = service.suggest_intelligent_tags_with_patterns(file)
print(f"Intelligent tags: {intelligent_tags}")
```

### カスタムパターンの追加

```python
# カスタムタグパターンの追加
service.add_custom_tag_pattern(
    category="custom_category",
    pattern_name="my_pattern",
    tag_name="my-tag",
    keywords=["keyword1", "keyword2", "keyword3"],
    description="My custom pattern",
    confidence_weight=1.1
)
```

### Vault分析

```python
# Vaultファイルの読み込み（FileRepositoryを使用）
from knowledge_base_organizer.infrastructure.file_repository import FileRepository

file_repo = FileRepository()
files = file_repo.load_vault_files(Path("/path/to/vault"))

# タグ分析の実行
analysis = service.update_vault_tag_analysis(files)

print(f"Total files: {analysis.total_files}")
print(f"Unique tags: {analysis.unique_tags}")
print(f"Most common tags: {analysis.most_common_tags[:10]}")
```

### LLM統合の準備

```python
# LLM用データのエクスポート
llm_data = service.export_tag_patterns_for_llm()

# エクスポートされたデータの構造
print(f"Categories: {list(llm_data['categories'].keys())}")
print(f"Total patterns: {llm_data['metadata']['total_patterns']}")

# LLMからのデータインポート（例）
llm_suggestions = {
    "categories": {
        "ai_ml": {
            "description": "AI and Machine Learning",
            "priority": 9,
            "patterns": [
                {
                    "tag": "deep-learning",
                    "keywords": ["deep learning", "neural network", "cnn", "rnn"],
                    "confidence_weight": 1.3,
                    "description": "Deep learning content"
                }
            ]
        }
    }
}

service.import_tag_patterns_from_llm(llm_suggestions)
```

## 設定とカスタマイズ

### 設定ディレクトリ

タグパターンは以下の場所に保存されます：

```
.kiro/tag_patterns/
├── tag_patterns.json      # タグパターン定義
└── vault_tag_analysis.json # Vault分析結果
```

### パターンファイルの構造

```json
{
  "programming_languages": {
    "description": "Programming languages and frameworks",
    "priority": 8,
    "patterns": {
      "python": {
        "tag_name": "python",
        "keywords": ["python", "py", "django", "flask"],
        "category": "programming_languages",
        "confidence_weight": 1.2,
        "usage_count": 5,
        "description": "Python programming language",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00"
      }
    }
  }
}
```

## 高度な使用例

### 1. バッチ処理でのタグ付け

```python
# 複数ファイルの一括処理
files = file_repo.load_vault_files(vault_path)
results = service.enhance_vault_frontmatter(files, apply_changes=True)

for result in results:
    if result.success and result.improvements_made > 0:
        print(f"Enhanced {result.file_path}: {result.changes_applied}")
```

### 2. タグ関係性の分析

```python
# タグ関係性の詳細分析
analysis = service.update_vault_tag_analysis(files)

for tag, relationships in analysis.tag_relationships.items():
    strong_relations = [(t, s) for t, s in relationships.items() if s > 0.5]
    if strong_relations:
        print(f"{tag} -> {strong_relations}")
```

### 3. 統計情報の取得

```python
# 詳細統計の取得
stats = service.get_vault_tag_statistics()
print(f"Average tags per file: {stats['summary']['average_tags_per_file']}")
print(f"Orphaned tags: {len(stats['orphaned_tags'])}")
```

## トラブルシューティング

### よくある問題

1. **パターンが適用されない**
   - 信頼度閾値を確認してください（デフォルト: 0.4）
   - キーワードがコンテンツに含まれているか確認してください

2. **分析結果が保存されない**
   - 設定ディレクトリの書き込み権限を確認してください
   - `.kiro/tag_patterns/` ディレクトリが存在することを確認してください

3. **LLMエクスポートが失敗する**
   - Vault分析が実行されているか確認してください
   - JSON形式の妥当性を確認してください

### デバッグ方法

```python
# デバッグ情報の表示
service = FrontmatterEnhancementService()
patterns = service.tag_pattern_manager.get_all_patterns()

for category_name, category in patterns.items():
    print(f"Category: {category_name}")
    for pattern_name, pattern in category.patterns.items():
        print(f"  Pattern: {pattern_name}")
        print(f"  Keywords: {pattern.keywords}")
        print(f"  Usage: {pattern.usage_count}")
```

## 今後の拡張予定

1. **LLM統合**: OpenAI GPTやClaude APIとの直接統合
2. **自動学習**: 使用パターンに基づく自動パターン更新
3. **多言語対応**: より多くの言語でのコンテンツ分析
4. **可視化**: タグ関係性のグラフ表示
5. **推奨システム**: 類似ファイルに基づくタグ推奨

このタグ管理システムにより、Knowledge Base Organizerはより知的で効率的なタグ付けを実現し、LLMとの統合への道筋を提供します。

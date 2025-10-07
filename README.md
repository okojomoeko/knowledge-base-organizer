# knowledge-base-organizer

Obsidianボルト用の自動整理・最適化ツール。フロントマター検証、デッドリンク検出、自動WikiLink生成など、ナレッジベースの品質向上を支援します。

## 🚀 クイックスタート

### インストール

```bash
# uvをインストール（未インストールの場合）
curl -LsSf https://astral.sh/uv/install.sh | sh

# プロジェクトをクローン
git clone <repository-url>
cd knowledge-base-organizer

# 依存関係をインストール
uv sync
```

### 基本的な使い方

```bash
# ボルトの基本分析
uv run python -m knowledge_base_organizer analyze /path/to/your/vault

# フロントマター検証（プレビュー）
uv run python -m knowledge_base_organizer validate-frontmatter /path/to/your/vault --dry-run

# デッドリンク検出
uv run python -m knowledge_base_organizer detect-dead-links /path/to/your/vault

# 自動WikiLink生成（プレビュー）
uv run python -m knowledge_base_organizer auto-link /path/to/your/vault --dry-run --max-links 10
```

## 📋 主な機能

| 機能 | 説明 | コマンド |
|------|------|----------|
| **ボルト分析** | ファイル数、リンク数、フロントマター統計を表示 | `analyze` |
| **フロントマター検証** | テンプレートに基づいてフロントマターを検証・修正 | `validate-frontmatter` |
| **デッドリンク検出** | 存在しないファイルへのリンクを検出 | `detect-dead-links` |
| **自動WikiLink生成** | テキストから自動的にWikiLinkを生成 | `auto-link` |
| **総合整理** | 複数の改善を一括実行 | `organize` |

## 🎯 ユースケース別逆引きガイド

### 📊 ボルトの現状を把握したい

```bash
# 基本統計を確認
uv run python -m knowledge_base_organizer analyze /path/to/vault

# 詳細な分析結果をJSONで出力
uv run python -m knowledge_base_organizer analyze /path/to/vault --output-format json --verbose
```

### 🔍 フロントマターの問題を見つけて修正したい

```bash
# 問題のあるフロントマターを確認（実行しない）
uv run python -m knowledge_base_organizer validate-frontmatter /path/to/vault --dry-run

# 実際に修正を適用
uv run python -m knowledge_base_organizer validate-frontmatter /path/to/vault --execute

# 特定のテンプレートのみ検証
uv run python -m knowledge_base_organizer validate-frontmatter /path/to/vault --template fleeting-note
```

### 🔗 壊れたリンクを見つけたい

```bash
# デッドリンクを検出
uv run python -m knowledge_base_organizer detect-dead-links /path/to/vault

# WikiLinkのみチェック
uv run python -m knowledge_base_organizer detect-dead-links /path/to/vault --link-type wikilink

# 結果をCSVで出力
uv run python -m knowledge_base_organizer detect-dead-links /path/to/vault --output-format csv --output results.csv
```

### ✨ 自動的にWikiLinkを作成したい

```bash
# 安全にプレビュー（推奨）
uv run python -m knowledge_base_organizer auto-link /path/to/vault --dry-run --max-links 5

# 実際にリンクを作成（少数から開始）
uv run python -m knowledge_base_organizer auto-link /path/to/vault --execute --max-links 3 --max-files 5

# テーブル内容を除外してリンク作成
uv run python -m knowledge_base_organizer auto-link /path/to/vault --execute --exclude-tables
```

### 🛠️ ボルト全体を一括で整理したい

```bash
# 総合的な改善提案を確認
uv run python -m knowledge_base_organizer organize /path/to/vault --dry-run

# インタラクティブモードで改善を適用
uv run python -m knowledge_base_organizer organize /path/to/vault --execute --interactive

# バックアップ付きで自動実行
uv run python -m knowledge_base_organizer organize /path/to/vault --execute --backup
```

### 🎯 特定のファイルパターンのみ処理したい

```bash
# 特定のディレクトリのみ処理
uv run python -m knowledge_base_organizer analyze /path/to/vault --include "101_PermanentNotes/**"

# 複数のディレクトリを対象にする（--includeを複数回指定）
uv run python -m knowledge_base_organizer analyze /path/to/vault \
  --include "101_PermanentNotes/**" \
  --include "100_FleetingNotes/**"

# 特定のファイルを除外
uv run python -m knowledge_base_organizer validate-frontmatter /path/to/vault --exclude "900_Templates/**"

# 複数の除外パターンを指定（--excludeを複数回指定）
uv run python -m knowledge_base_organizer auto-link /path/to/vault \
  --exclude "900_Templates/**" \
  --exclude "Archive/**" \
  --exclude "draft_*"

# includeとexcludeを組み合わせ
uv run python -m knowledge_base_organizer organize /path/to/vault \
  --include "101_PermanentNotes/**" \
  --include "100_FleetingNotes/**" \
  --exclude "*.draft.md"
```

## ⚙️ よく使うオプション

### 安全性オプション

- `--dry-run`: 実際の変更を行わずプレビューのみ
- `--backup`: 変更前にバックアップを作成
- `--interactive`: 各変更を確認してから適用
- `--max-files N`: 処理するファイル数を制限
- `--max-links N`: 作成するリンク数を制限

### 出力オプション

- `--output-format json|csv|console`: 出力形式を指定
- `--output FILE`: 結果をファイルに保存
- `--verbose`: 詳細な情報を表示

### フィルタリングオプション

- `--include PATTERN`: 処理対象ファイルパターン（複数回指定可能）
- `--exclude PATTERN`: 除外ファイルパターン（複数回指定可能）
- `--template NAME`: 特定のテンプレートのみ処理

## 🔧 高度な使い方

### カスタム設定ファイル

```bash
# 設定ファイルを使用
uv run python -m knowledge_base_organizer analyze /path/to/vault --config custom-config.yaml
```

### バッチ処理

```bash
# 複数のボルトを一括処理
for vault in vault1 vault2 vault3; do
  uv run python -m knowledge_base_organizer organize "$vault" --dry-run
done
```

### 結果の活用

```bash
# JSON結果をjqで加工
uv run python -m knowledge_base_organizer analyze /path/to/vault --output-format json | jq '.file_statistics'

# CSV結果をExcelで開く
uv run python -m knowledge_base_organizer detect-dead-links /path/to/vault --output-format csv --output dead-links.csv
```

## 🚨 注意事項

### 初回実行時

1. **必ずバックアップを取る**: 重要なデータは事前にバックアップ
2. **小規模から開始**: `--max-files 5` などで少数のファイルから試す
3. **dry-runで確認**: `--dry-run` で変更内容を事前確認
4. **テンプレート検証の注意**: 現在のテンプレート自動検出は改善中のため、`analyze`コマンドから始めることを推奨

### 大規模ボルトでの使用

```bash
# 段階的に処理
uv run python -m knowledge_base_organizer auto-link /path/to/vault --execute --max-files 10 --max-links 3
uv run python -m knowledge_base_organizer auto-link /path/to/vault --execute --max-files 20 --max-links 5
```

### パフォーマンス最適化

```bash
# 特定のディレクトリのみ処理
uv run python -m knowledge_base_organizer organize /path/to/vault --include "101_PermanentNotes/**"

# 複数のディレクトリを対象にしつつ、不要なディレクトリを除外
uv run python -m knowledge_base_organizer auto-link /path/to/vault \
  --include "101_PermanentNotes/**" \
  --include "100_FleetingNotes/**" \
  --exclude "900_Templates/**" \
  --exclude "Archive/**"
```

## 🆘 トラブルシューティング

### よくある問題

**Q: フロントマターの検証でエラーが出る**

```bash
# 詳細なエラー情報を確認
uv run python -m knowledge_base_organizer validate-frontmatter /path/to/vault --dry-run --verbose

# 特定のテンプレートのみ検証（テンプレート自動検出に問題がある場合）
uv run python -m knowledge_base_organizer validate-frontmatter /path/to/vault --template specific-template --dry-run
```

**Q: 全ファイルが同じテンプレートとして検出される**

```bash
# 現在のテンプレート検出は改善中です。一時的な回避策：
# 1. 特定のテンプレートを指定して検証
uv run python -m knowledge_base_organizer validate-frontmatter /path/to/vault --template fleeting-note --dry-run

# 2. または、基本的な分析のみ実行
uv run python -m knowledge_base_organizer analyze /path/to/vault
```

**Q: 自動リンク生成で意図しないリンクが作られる**

```bash
# より厳しい条件で実行
uv run python -m knowledge_base_organizer auto-link /path/to/vault --dry-run --max-links 1 --exclude-tables
```

**Q: 処理が遅い**

```bash
# ファイル数を制限
uv run python -m knowledge_base_organizer organize /path/to/vault --max-files 50
```

**Q: 複数のディレクトリを対象にしたい**

```bash
# --includeオプションを複数回指定
uv run python -m knowledge_base_organizer analyze /path/to/vault \
  --include "100_FleetingNotes/**" \
  --include "101_PermanentNotes/**" \
  --include "102_Literature/**"

# または、複数の除外パターンを指定
uv run python -m knowledge_base_organizer auto-link /path/to/vault \
  --exclude "900_Templates/**" \
  --exclude "Archive/**" \
  --exclude "Draft/**"
```

## 🔗 関連リンク

- [Obsidian](https://obsidian.md/) - ナレッジベース管理ツール
- [uv](https://docs.astral.sh/uv/) - Python パッケージマネージャー

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 📚 実践例

### 新しいボルトを整理する完全ワークフロー

```bash
# 1. まずボルトの現状を把握
uv run python -m knowledge_base_organizer analyze /path/to/vault --verbose

# 2. フロントマターの問題を確認
uv run python -m knowledge_base_organizer validate-frontmatter /path/to/vault --dry-run

# 3. デッドリンクをチェック
uv run python -m knowledge_base_organizer detect-dead-links /path/to/vault

# 4. 少数のファイルで自動リンクをテスト
uv run python -m knowledge_base_organizer auto-link /path/to/vault --dry-run --max-files 5 --max-links 3

# 5. 問題なければ段階的に適用
uv run python -m knowledge_base_organizer validate-frontmatter /path/to/vault --execute
uv run python -m knowledge_base_organizer auto-link /path/to/vault --execute --max-files 10 --max-links 5

# 6. 最終確認
uv run python -m knowledge_base_organizer analyze /path/to/vault
```

### 日常的なメンテナンス

```bash
# 週次チェック用スクリプト例
#!/bin/bash
VAULT_PATH="/path/to/your/vault"

echo "=== 週次ボルトチェック ==="
echo "1. デッドリンク検出"
uv run python -m knowledge_base_organizer detect-dead-links "$VAULT_PATH" --output-format console

echo "2. フロントマター検証"
uv run python -m knowledge_base_organizer validate-frontmatter "$VAULT_PATH" --dry-run

echo "3. 新しいリンク機会の確認"
uv run python -m knowledge_base_organizer auto-link "$VAULT_PATH" --dry-run --max-links 5

echo "=== チェック完了 ==="
```

### 大規模ボルト（1000+ファイル）での安全な処理

```bash
# 段階1: 分析とプランニング
uv run python -m knowledge_base_organizer analyze /path/to/large-vault --output-format json > analysis.json

# 段階2: 小規模テスト（100ファイル）
uv run python -m knowledge_base_organizer organize /path/to/large-vault --dry-run --max-files 100

# 段階3: 段階的実行（バックアップ付き）
uv run python -m knowledge_base_organizer validate-frontmatter /path/to/large-vault --execute --backup
uv run python -m knowledge_base_organizer auto-link /path/to/large-vault --execute --max-files 50 --max-links 3

# 段階4: 結果確認
uv run python -m knowledge_base_organizer analyze /path/to/large-vault --output-format json > analysis-after.json
```

## 🎨 カスタマイズ例

### 特定用途向けの設定

```bash
# 学術論文ボルト用（厳密なフロントマター）
uv run python -m knowledge_base_organizer validate-frontmatter /path/to/academic-vault --template academic-paper --execute

# 日記ボルト用（軽いリンク生成）
uv run python -m knowledge_base_organizer auto-link /path/to/diary-vault --execute --max-links 2 --exclude-tables

# プロジェクトノート用（包括的整理）
uv run python -m knowledge_base_organizer organize /path/to/project-vault --execute --interactive --backup

# メインコンテンツのみ処理（テンプレートやアーカイブを除外）
uv run python -m knowledge_base_organizer auto-link /path/to/vault \
  --include "100_FleetingNotes/**" \
  --include "101_PermanentNotes/**" \
  --include "102_Literature/**" \
  --exclude "900_Templates/**" \
  --exclude "Archive/**" \
  --exclude "*.draft.md"

# 特定のプロジェクトフォルダのみ整理
uv run python -m knowledge_base_organizer organize /path/to/vault \
  --include "Projects/ProjectA/**" \
  --include "Projects/ProjectB/**" \
  --execute --backup
```

### 出力結果の活用

```bash
# デッドリンクレポートをMarkdownで生成
uv run python -m knowledge_base_organizer detect-dead-links /path/to/vault --output-format json | \
  jq -r '.dead_links[] | "- [ ] Fix: [\(.text)](\(.file_path):\(.line_number))"' > dead-links-todo.md

# フロントマター統計をCSVで出力
uv run python -m knowledge_base_organizer analyze /path/to/vault --output-format json | \
  jq -r '.frontmatter_statistics.most_common_fields[] | "\(.[0]),\(.[1])"' > frontmatter-stats.csv
```

## 🔄 継続的改善のワークフロー

### Git統合例

```bash
# 変更前にコミット
git add . && git commit -m "Before knowledge-base-organizer improvements"

# 改善実行
uv run python -m knowledge_base_organizer organize /path/to/vault --execute --backup

# 結果確認とコミット
git add . && git commit -m "Apply knowledge-base-organizer improvements

- Fixed frontmatter issues
- Added auto-generated WikiLinks
- Resolved dead links"
```

### CI/CD統合例

```yaml
# .github/workflows/vault-quality-check.yml
name: Vault Quality Check
on: [push, pull_request]

jobs:
  quality-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: astral-sh/setup-uv@v1

      - name: Install dependencies
        run: uv sync

      - name: Check vault quality
        run: |
          uv run python -m knowledge_base_organizer analyze vault/
          uv run python -m knowledge_base_organizer detect-dead-links vault/
          uv run python -m knowledge_base_organizer validate-frontmatter vault/ --dry-run
```

---

## 🛠️ 開発者向け情報

### 開発環境のセットアップ

```bash
# リポジトリをクローン
git clone <repository-url>
cd knowledge-base-organizer

# 開発依存関係をインストール
uv sync --group dev

# pre-commitフックをインストール
uv run pre-commit install
```

### テスト実行

```bash
# 全テスト実行
uv run pytest

# カバレッジ付きテスト
uv run pytest --cov=src --cov-report=html

# 特定のテストのみ実行
uv run pytest tests/integration/test_auto_link_generation_task_7_4.py -v
```

### コード品質チェック

```bash
# リンティング
uv run ruff check src tests

# フォーマット
uv run ruff format src tests

# 型チェック
uv run mypy src
```

### 新機能の追加

1. **仕様作成**: `.kiro/specs/` にspecファイルを作成
2. **テスト駆動開発**: テストを先に書く
3. **実装**: 段階的に機能を実装
4. **統合テスト**: 実際のボルトでテスト

### アーキテクチャ

```
src/knowledge_base_organizer/
├── cli/                    # CLIインターフェース
├── application/            # ユースケース層
├── domain/                 # ドメインロジック
│   ├── models/            # ドメインモデル
│   └── services/          # ドメインサービス
└── infrastructure/        # インフラ層
```

### 貢献方法

1. Issueを作成して議論
2. フィーチャーブランチを作成
3. テストを含む実装
4. プルリクエストを作成

詳細は [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。

# knowledge-base-organizer

Obsidianボルト用の高機能自動整理・最適化ツール。日本語対応のWikiLink生成、フロントマター検証、デッドリンク検出、包括的メンテナンスなど、ナレッジベースの品質向上を総合的に支援します。

## ✨ 主な特徴

- 🇯🇵 **日本語完全対応**: カタカナ表記ゆれ、英日対訳、略語展開に対応
- 🔗 **高精度WikiLink生成**: 文脈を理解した自動リンク作成
- 📊 **包括的分析**: ボルト全体の健康状態を可視化
- 🛠️ **総合メンテナンス**: 複数の改善タスクを一括実行
- ⚙️ **柔軟な設定**: YAML設定ファイルでカスタマイズ可能
- 🔒 **安全性重視**: dry-runモード、バックアップ機能標準装備

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

# 包括的メンテナンス（推奨）
uv run python -m knowledge_base_organizer maintain /path/to/your/vault --dry-run

# フロントマター検証
uv run python -m knowledge_base_organizer validate-frontmatter /path/to/your/vault --dry-run

# デッドリンク検出
uv run python -m knowledge_base_organizer detect-dead-links /path/to/your/vault

# 自動WikiLink生成（少数から開始推奨）
uv run python -m knowledge_base_organizer auto-link /path/to/your/vault --dry-run --max-links 5
```

## 📋 全機能一覧

| 機能 | 説明 | コマンド | 主な用途 |
|------|------|----------|----------|
| **ボルト分析** | ファイル数、リンク数、フロントマター統計を表示 | `analyze` | 現状把握・健康診断 |
| **包括的メンテナンス** | 複数の改善タスクを統合実行 | `maintain` | 定期メンテナンス |
| **フロントマター検証** | テンプレートに基づく検証・修正 | `validate-frontmatter` | メタデータ整理 |
| **デッドリンク検出** | 存在しないファイルへのリンクを検出 | `detect-dead-links` | リンク整合性確認 |
| **自動WikiLink生成** | 日本語対応の高精度リンク作成 | `auto-link` | 知識の関連付け |
| **総合整理** | フロントマター改善と重複検出 | `organize` | 品質向上 |
| **AI強化要約生成** | LLMを使用した高品質な要約作成 | `summarize` | コンテンツ要約 |
| **タグ管理** | タグパターンの管理 | `tags` | タグ体系整理 |

## 🎯 ユースケース別逆引きガイド

### 📊 ボルトの現状を把握したい

```bash
# 基本統計を確認
uv run python -m knowledge_base_organizer analyze /path/to/vault

# 詳細な分析結果をJSONで出力
uv run python -m knowledge_base_organizer analyze /path/to/vault --output-format json --verbose

# 特定のディレクトリのみ分析
uv run python -m knowledge_base_organizer analyze /path/to/vault --include "101_PermanentNotes/**"
```

### 🛠️ 包括的メンテナンスを実行したい（推奨）

```bash
# 全メンテナンスタスクをプレビュー
uv run python -m knowledge_base_organizer maintain /path/to/vault --dry-run

# 特定のタスクのみ実行
uv run python -m knowledge_base_organizer maintain /path/to/vault --task organize --task dead-links --dry-run

# 実際にメンテナンスを適用
uv run python -m knowledge_base_organizer maintain /path/to/vault --execute --backup

# JSON形式でレポート出力
uv run python -m knowledge_base_organizer maintain /path/to/vault --output-format json --output maintenance-report.json

# インタラクティブモードで確認しながら実行
uv run python -m knowledge_base_organizer maintain /path/to/vault --execute --interactive
```

### 🔍 フロントマターの問題を見つけて修正したい

```bash
# 問題のあるフロントマターを確認（実行しない）
uv run python -m knowledge_base_organizer validate-frontmatter /path/to/vault --dry-run

# 実際に修正を適用
uv run python -m knowledge_base_organizer validate-frontmatter /path/to/vault --execute

# 特定のテンプレートのみ検証
uv run python -m knowledge_base_organizer validate-frontmatter /path/to/vault --template fleeting-note

# インタラクティブモードで確認しながら修正
uv run python -m knowledge_base_organizer validate-frontmatter /path/to/vault --execute --interactive
```

### 🔗 壊れたリンクを見つけたい

```bash
# デッドリンクを検出
uv run python -m knowledge_base_organizer detect-dead-links /path/to/vault

# WikiLinkのみチェック
uv run python -m knowledge_base_organizer detect-dead-links /path/to/vault --link-type wikilink

# 修正提案があるもののみ表示
uv run python -m knowledge_base_organizer detect-dead-links /path/to/vault --only-with-suggestions

# 結果をCSVで出力
uv run python -m knowledge_base_organizer detect-dead-links /path/to/vault --output-format csv --output dead-links.csv

# 上位10件のみ表示
uv run python -m knowledge_base_organizer detect-dead-links /path/to/vault --limit 10
```

### ✨ 自動的にWikiLinkを作成したい

```bash
# 安全にプレビュー（推奨）
uv run python -m knowledge_base_organizer auto-link /path/to/vault --dry-run --max-links 5

# 実際にリンクを作成（少数から開始）
uv run python -m knowledge_base_organizer auto-link /path/to/vault --execute --max-links 3 --max-files 5

# テーブル内容を除外してリンク作成
uv run python -m knowledge_base_organizer auto-link /path/to/vault --execute --exclude-tables

# 特定のファイルのみ処理
uv run python -m knowledge_base_organizer auto-link /path/to/vault --target "specific-file.md" --execute

# 大規模ボルト用（ファイル数制限）
uv run python -m knowledge_base_organizer auto-link /path/to/vault --execute --max-files 50 --max-links 10
```

### 🤖 AI機能を活用したい

#### AI強化フロントマター生成

```bash
# AI提案を含む総合整理（プレビュー）
uv run python -m knowledge_base_organizer organize /path/to/vault --ai-suggest-metadata --dry-run

# AI提案を適用して実際に改善
uv run python -m knowledge_base_organizer organize /path/to/vault --ai-suggest-metadata --execute --interactive

# バックアップ付きで自動適用
uv run python -m knowledge_base_organizer organize /path/to/vault --ai-suggest-metadata --execute --backup
```

#### AI要約生成

```bash
# 単一ファイルの要約生成
uv run python -m knowledge_base_organizer summarize /path/to/note.md

# 長めの要約を生成
uv run python -m knowledge_base_organizer summarize /path/to/note.md --max-length 500

# 要約をファイルに保存
uv run python -m knowledge_base_organizer summarize /path/to/note.md --output summary.md

# 詳細な出力で実行
uv run python -m knowledge_base_organizer summarize /path/to/note.md --verbose
```

### 🛠️ ボルト全体を一括で整理したい

```bash
# 総合的な改善提案を確認
uv run python -m knowledge_base_organizer organize /path/to/vault --dry-run

# インタラクティブモードで改善を適用
uv run python -m knowledge_base_organizer organize /path/to/vault --execute --interactive

# バックアップ付きで自動実行
uv run python -m knowledge_base_organizer organize /path/to/vault --execute --backup

# 重複ファイル検出も含めて実行
uv run python -m knowledge_base_organizer organize /path/to/vault --execute --detect-duplicates --duplicate-threshold 0.8
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

# メンテナンスでも同様にフィルタリング可能
uv run python -m knowledge_base_organizer maintain /path/to/vault \
  --include "101_PermanentNotes/**" \
  --exclude "Archive/**" \
  --task organize --task dead-links
```

### 🏷️ タグパターンを管理したい

```bash
# タグパターンの一覧表示
uv run python -m knowledge_base_organizer tags list

# 新しいタグパターンを追加
uv run python -m knowledge_base_organizer tags add "プログラミング" --pattern "programming|coding|development"

# タグパターンを更新
uv run python -m knowledge_base_organizer tags update "プログラミング" --pattern "programming|coding|development|software"

# タグパターンを削除
uv run python -m knowledge_base_organizer tags remove "古いタグ"

# タグパターンをファイルからインポート
uv run python -m knowledge_base_organizer tags import tag-patterns.yaml
```

### 🤖 LLM設定を管理したい

```bash
# LLM設定ファイルのテンプレートを作成
uv run python -m knowledge_base_organizer llm create-config --output llm_config.yaml

# 利用可能なプロバイダーを確認
uv run python -m knowledge_base_organizer llm list-providers

# 利用可能なモデルを確認
uv run python -m knowledge_base_organizer llm list-models --provider ollama

# 接続テスト
uv run python -m knowledge_base_organizer llm test-connection --provider ollama --verbose

# テキスト生成テスト
uv run python -m knowledge_base_organizer llm test-generation --provider ollama --prompt "Hello, world!"

# 現在の設定を表示
uv run python -m knowledge_base_organizer llm show-config
```

## ⚙️ よく使うオプション

### 安全性オプション

- `--dry-run`: 実際の変更を行わずプレビューのみ（推奨）
- `--backup`: 変更前にバックアップを作成
- `--interactive`: 各変更を確認してから適用
- `--max-files N`: 処理するファイル数を制限（大規模ボルト用）
- `--max-links N`: 作成するリンク数を制限

### 出力オプション

- `--output-format json|csv|console`: 出力形式を指定
- `--output FILE`: 結果をファイルに保存
- `--verbose`: 詳細な情報を表示

### フィルタリングオプション

- `--include PATTERN`: 処理対象ファイルパターン（複数回指定可能）
- `--exclude PATTERN`: 除外ファイルパターン（複数回指定可能）
- `--template NAME`: 特定のテンプレートのみ処理

### メンテナンス専用オプション

- `--task TASK`: 実行するメンテナンスタスクを指定（organize, duplicates, orphans, dead-links）
- `--schedule SCHEDULE`: スケジュール実行（将来実装予定）
- `--duplicate-threshold FLOAT`: 重複検出の類似度閾値（0.0-1.0）

### AI機能オプション

- `--ai-suggest-metadata`: AI によるメタデータ提案を有効化（organizeコマンド）
- `--max-length N`: 要約の最大文字数を指定（summarizeコマンド）
- `--llm-provider PROVIDER`: 使用するLLMプロバイダーを指定（ollama, lm_studio, etc.）
- `--llm-model MODEL`: 使用するLLMモデルを指定
- `--llm-config PATH`: LLM設定ファイルのパスを指定

### 高度なオプション

- `--exclude-tables`: テーブル内容をリンク処理から除外
- `--exclude-content PATTERN`: 特定のコンテンツパターンを除外
- `--link-type TYPE`: 特定のリンクタイプのみ処理
- `--sort-by FIELD`: 結果のソート順を指定
- `--limit N`: 表示する結果数を制限
- `--only-with-suggestions`: 修正提案があるもののみ表示

## 🤖 AI機能の詳細

knowledge-base-organizerは、LLM（Large Language Model）を活用した高度な機能を提供します。これらの機能により、手動では困難な高品質なメタデータ生成と要約作成が可能になります。

### AI強化フロントマター生成（Phase 13実装済み）

`organize`コマンドに`--ai-suggest-metadata`オプションを追加することで、AIによる高度なメタデータ提案が利用できます。

#### 機能概要

- **インテリジェントタグ提案**: コンテンツを分析して関連性の高いタグを自動提案
- **クロス言語エイリアス**: 英日対訳や略語展開に基づくエイリアス提案
- **メタデータ抽出**: コンテンツから著者、出典、プロジェクト情報などを自動抽出
- **説明文生成**: ファイル内容に基づく適切な説明文の自動生成

#### 使用例

```bash
# AI提案を含む分析（安全）
uv run python -m knowledge_base_organizer organize /path/to/vault --ai-suggest-metadata --dry-run

# インタラクティブモードで確認しながら適用
uv run python -m knowledge_base_organizer organize /path/to/vault --ai-suggest-metadata --execute --interactive

# 特定のファイルパターンのみAI処理
uv run python -m knowledge_base_organizer organize /path/to/vault \
  --ai-suggest-metadata --include "101_PermanentNotes/**" --execute
```

#### AI提案の種類

1. **技術タグ**: プログラミング言語、フレームワーク、技術概念
2. **コンテンツタグ**: 文書の内容や分野に基づくタグ
3. **言語横断エイリアス**: 「API」→「エーピーアイ」、「DB」→「データベース」
4. **メタデータフィールド**: author、source、project、status等
5. **説明文**: ファイル内容を要約した簡潔な説明

### AI要約生成（Phase 15実装済み）

`summarize`コマンドは、LLMを使用してマークダウンファイルの高品質な要約を生成します。

#### 機能概要

- **コンテンツ理解**: マークダウン構造を理解した要約生成
- **長さ制御**: 指定した文字数内での要約作成
- **日本語対応**: 日本語コンテンツの自然な要約
- **キーポイント抽出**: 重要な情報を漏らさない要約

#### 使用例

```bash
# 基本的な要約生成（200文字）
uv run python -m knowledge_base_organizer summarize /path/to/note.md

# 詳細な要約（500文字）
uv run python -m knowledge_base_organizer summarize /path/to/note.md --max-length 500

# 要約をファイルに保存
uv run python -m knowledge_base_organizer summarize /path/to/note.md --output summary.md

# 処理詳細を表示
uv run python -m knowledge_base_organizer summarize /path/to/note.md --verbose

# 特定のLLMプロバイダーとモデルを指定
uv run python -m knowledge_base_organizer summarize /path/to/note.md \
  --llm-provider ollama --llm-model qwen2.5:14b --max-length 500

# LM Studioを使用
uv run python -m knowledge_base_organizer summarize /path/to/note.md \
  --llm-provider lm_studio --max-length 300
```

### LLM設定管理

#### 設定ファイルの作成

```bash
# LLM設定ファイルのテンプレートを作成
uv run python -m knowledge_base_organizer llm create-config --output llm_config.yaml

# 利用可能なプロバイダーを確認
uv run python -m knowledge_base_organizer llm list-providers

# 接続テスト
uv run python -m knowledge_base_organizer llm test-connection --provider ollama

# テキスト生成テスト
uv run python -m knowledge_base_organizer llm test-generation --provider ollama --verbose
```

#### 設定ファイルの例

```yaml
# llm_config.yaml
default_provider: "ollama"

providers:
  ollama:
    base_url: "http://localhost:11434"
    model_name: "qwen2.5:7b"
    timeout: 120
    options:
      temperature: 0.3
      top_p: 0.9

  lm_studio:
    base_url: "http://localhost:1234"
    model_name: "local-model"
    api_format: "openai"
    timeout: 120
    options:
      temperature: 0.3
      max_tokens: 2048

  custom_api:
    base_url: "http://your-server:8000"
    model_name: "custom-model"
    api_format: "openai"
    api_key: "your-api-key"
```

#### コマンドラインでのプロバイダー指定

```bash
# Ollamaで特定のモデルを使用
uv run python -m knowledge_base_organizer organize /path/to/vault --ai-suggest-metadata \
  --llm-provider ollama --llm-model qwen2.5:14b --dry-run

# LM Studioを使用
uv run python -m knowledge_base_organizer organize /path/to/vault --ai-suggest-metadata \
  --llm-provider lm_studio --execute --interactive

# カスタム設定ファイルを使用
uv run python -m knowledge_base_organizer organize /path/to/vault --ai-suggest-metadata \
  --llm-config /path/to/custom/llm_config.yaml --dry-run
```

#### 要約の品質

- **構造理解**: 見出し、リスト、コードブロックを考慮
- **重要度判定**: 文書内の重要な情報を優先的に抽出
- **自然な文章**: 読みやすく自然な日本語での要約
- **情報保持**: 元文書の主要な情報を漏らさない

### AI機能の前提条件

#### 対応プロバイダー

- **Ollama**: ローカルLLMランタイム（推奨）
- **LM Studio**: ローカルLLMサーバー
- **OpenAI互換API**: カスタムエンドポイント

#### セットアップ手順

1. **Ollamaのインストール**

   ```bash
   # macOS
   brew install ollama

   # Linux
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. **モデルのダウンロード**

   ```bash
   # 推奨モデル（日本語対応）
   ollama pull qwen2.5:7b

   # または
   ollama pull llama3.1:8b
   ```

3. **Ollamaサービスの起動**

   ```bash
   ollama serve
   ```

4. **LM Studioの場合**
   - LM Studioをダウンロード・インストール
   - モデルをダウンロード
   - ローカルサーバーを起動（通常ポート1234）

#### 設定の確認

```bash
# 設定ファイルを作成
uv run python -m knowledge_base_organizer llm create-config

# プロバイダー一覧を確認
uv run python -m knowledge_base_organizer llm list-providers

# 接続テスト
uv run python -m knowledge_base_organizer llm test-connection --verbose

# AI機能が利用可能か確認
uv run python -m knowledge_base_organizer organize /path/to/vault --ai-suggest-metadata --dry-run --verbose
```

### 環境変数による設定

```bash
# Ollamaの設定
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="qwen2.5:7b"

# LM Studioの設定
export LM_STUDIO_BASE_URL="http://localhost:1234"

# デフォルトプロバイダーの変更
export LLM_PROVIDER="lm_studio"

# 設定ファイルのパス指定
export LLM_CONFIG_PATH="/path/to/custom/llm_config.yaml"
```

### 外部からのLLM設定注入

knowledge-base-organizerは、外部システムからLLM設定を動的に注入することができます。これにより、CI/CD環境や自動化システムから柔軟にLLM設定を管理できます。

#### 設定注入の方法

**1. 環境変数による注入**

```bash
# 基本設定
export LLM_PROVIDER="custom_api"
export LLM_BASE_URL="https://api.example.com"
export LLM_MODEL="gpt-4"
export LLM_API_KEY="your-api-key"

# 高度な設定
export LLM_TIMEOUT="180"
export LLM_TEMPERATURE="0.7"
export LLM_MAX_TOKENS="4096"

# AI機能を実行
uv run python -m knowledge_base_organizer organize /path/to/vault --ai-suggest-metadata --execute
```

**2. 設定ファイルによる注入**

```bash
# カスタム設定ファイルを作成
cat > custom_llm_config.yaml << EOF
default_provider: "production_api"

providers:
  production_api:
    base_url: "https://your-production-api.com"
    model_name: "production-model-v2"
    api_format: "openai"
    api_key: "${PRODUCTION_API_KEY}"
    timeout: 300
    options:
      temperature: 0.3
      max_tokens: 8192
      top_p: 0.9

  development_api:
    base_url: "http://localhost:8080"
    model_name: "dev-model"
    api_format: "openai"
    timeout: 60
    options:
      temperature: 0.8
EOF

# 設定ファイルを指定して実行
uv run python -m knowledge_base_organizer organize /path/to/vault \
  --ai-suggest-metadata --llm-config custom_llm_config.yaml --execute
```

**3. コマンドライン引数による注入**

```bash
# プロバイダーとモデルを直接指定
uv run python -m knowledge_base_organizer organize /path/to/vault \
  --ai-suggest-metadata \
  --llm-provider custom_api \
  --llm-model gpt-4-turbo \
  --execute

# 要約生成で特定のモデルを使用
uv run python -m knowledge_base_organizer summarize /path/to/note.md \
  --llm-provider ollama \
  --llm-model qwen2.5:32b \
  --max-length 500
```

#### CI/CD統合例

**GitHub Actions**

```yaml
name: Knowledge Base AI Enhancement
on:
  schedule:
    - cron: '0 2 * * 1'  # 毎週月曜日2時

jobs:
  ai-enhance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v1

      - name: Setup LLM Configuration
        env:
          LLM_PROVIDER: "openai_compatible"
          LLM_BASE_URL: ${{ secrets.LLM_API_URL }}
          LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
          LLM_MODEL: "gpt-4"
        run: |
          uv sync

          # AI強化処理を実行
          uv run python -m knowledge_base_organizer organize vault/ \
            --ai-suggest-metadata --execute --backup \
            --output-format json > enhancement-report.json

      - name: Commit AI enhancements
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add .
          git commit -m "AI-enhanced metadata updates" || exit 0
          git push
```

**Docker環境**

```dockerfile
# Dockerfile
FROM python:3.13-slim

# Install uv
RUN pip install uv

# Copy application
COPY . /app
WORKDIR /app

# Install dependencies
RUN uv sync

# Set default LLM configuration
ENV LLM_PROVIDER="ollama"
ENV LLM_BASE_URL="http://ollama:11434"
ENV LLM_MODEL="qwen2.5:7b"

# Entry point
ENTRYPOINT ["uv", "run", "python", "-m", "knowledge_base_organizer"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  knowledge-base-organizer:
    build: .
    environment:
      - LLM_PROVIDER=ollama
      - LLM_BASE_URL=http://ollama:11434
      - LLM_MODEL=qwen2.5:7b
    volumes:
      - ./vault:/vault
    command: ["organize", "/vault", "--ai-suggest-metadata", "--execute"]
    depends_on:
      - ollama

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  ollama_data:
```

#### API統合例

**REST API経由での設定注入**

```python
# api_integration.py
import requests
import subprocess
import json

def enhance_knowledge_base_with_api_config():
    # 外部APIから設定を取得
    config_response = requests.get("https://config-api.example.com/llm-config")
    llm_config = config_response.json()

    # 設定ファイルを生成
    with open("runtime_llm_config.yaml", "w") as f:
        yaml.dump(llm_config, f)

    # knowledge-base-organizerを実行
    result = subprocess.run([
        "uv", "run", "python", "-m", "knowledge_base_organizer",
        "organize", "/path/to/vault",
        "--ai-suggest-metadata",
        "--llm-config", "runtime_llm_config.yaml",
        "--execute",
        "--output-format", "json"
    ], capture_output=True, text=True)

    # 結果を処理
    if result.returncode == 0:
        enhancement_report = json.loads(result.stdout)
        return enhancement_report
    else:
        raise Exception(f"Enhancement failed: {result.stderr}")

# 使用例
try:
    report = enhance_knowledge_base_with_api_config()
    print(f"Enhanced {report['files_processed']} files")
except Exception as e:
    print(f"Error: {e}")
```

#### セキュリティ考慮事項

**API キーの管理**

```bash
# 環境変数ファイルを使用（.env）
echo "LLM_API_KEY=your-secret-key" > .env
echo "LLM_BASE_URL=https://secure-api.example.com" >> .env

# .envファイルを読み込んで実行
set -a && source .env && set +a
uv run python -m knowledge_base_organizer organize vault/ --ai-suggest-metadata --execute
```

**設定の検証**

```bash
# 設定の妥当性を事前確認
uv run python -m knowledge_base_organizer llm test-connection --verbose

# 設定内容を確認（API キーは隠される）
uv run python -m knowledge_base_organizer llm show-config
```

#### トラブルシューティング

**設定注入の問題**

```bash
# 現在の設定を確認
uv run python -m knowledge_base_organizer llm show-config

# 利用可能なプロバイダーを確認
uv run python -m knowledge_base_organizer llm list-providers

# 接続テスト
uv run python -m knowledge_base_organizer llm test-connection --provider custom_api --verbose

# 設定ファイルの妥当性チェック
uv run python -c "
import yaml
with open('custom_llm_config.yaml') as f:
    config = yaml.safe_load(f)
    print('Configuration is valid YAML')
    print(f'Providers: {list(config.get(\"providers\", {}).keys())}')
"
```

**よくある問題と解決方法**

1. **環境変数が反映されない**

   ```bash
   # 環境変数の確認
   env | grep LLM

   # 明示的に設定
   export LLM_PROVIDER="your_provider"
   ```

2. **API接続エラー**

   ```bash
   # ネットワーク接続確認
   curl -I "$LLM_BASE_URL/v1/models"

   # タイムアウト設定を調整
   export LLM_TIMEOUT="300"
   ```

3. **設定ファイルが見つからない**

   ```bash
   # 絶対パスで指定
   uv run python -m knowledge_base_organizer organize vault/ \
     --llm-config /absolute/path/to/llm_config.yaml \
     --ai-suggest-metadata --execute
   ```

この柔軟な設定注入システムにより、様々な環境やワークフローでknowledge-base-organizerのAI機能を活用できます。

### AI機能の制限事項

#### 現在の制限

- **ローカル実行のみ**: クラウドAPIは未対応
- **処理時間**: 大量ファイルの処理には時間がかかる
- **モデル依存**: 使用するLLMモデルにより品質が変動

#### 推奨事項

- **段階的適用**: 少数のファイルから開始
- **dry-runモード**: 必ず事前にプレビューで確認
- **バックアップ**: 重要なボルトは事前にバックアップ
- **インタラクティブモード**: 初回は`--interactive`で確認

### トラブルシューティング

#### よくある問題

**Q: AI機能が利用できない**

```bash
# プロバイダーの状態確認
uv run python -m knowledge_base_organizer llm list-providers

# 接続テスト
uv run python -m knowledge_base_organizer llm test-connection --verbose

# Ollamaの場合
ollama list
ollama ps
ollama serve
```

**Q: 要約生成が失敗する**

```bash
# モデルの確認
uv run python -m knowledge_base_organizer llm list-models

# 生成テスト
uv run python -m knowledge_base_organizer llm test-generation --verbose

# 詳細エラー情報
uv run python -m knowledge_base_organizer summarize /path/to/note.md --verbose
```

**Q: AI提案の品質が低い**

- より高性能なモデルを使用（qwen2.5:14b等）
- ファイル内容の品質を向上（明確な見出し、構造化）
- 専門用語辞書の拡充（config/japanese_variations.yaml）
- 異なるプロバイダーやモデルを試す

## ⚙️ 設定ファイルとカスタマイズ

### 設定ファイルの場所

knowledge-base-organizerは以下の設定ファイルを使用します：

```
src/knowledge_base_organizer/config/
├── keyword_extraction.yaml      # キーワード抽出設定
└── japanese_variations.yaml     # 日本語表記ゆれ設定
```

### キーワード抽出設定（keyword_extraction.yaml）

```yaml
# 除外する一般的な単語
common_words:
  english: ["the", "and", "for", ...]
  japanese: ["これ", "それ", "について", ...]

# 重要なキーワードパターン
important_keywords:
  technical_terms:
    specific_terms: ["API", "REST", "GraphQL", ...]
  japanese_terms:
    programming: ["プログラミング", "アルゴリズム", ...]

# 抽出設定
extraction_settings:
  min_keyword_length: 3
  max_keyword_length: 50
  exclude_numbers_only: true
  max_keywords: 100
```

### 日本語表記ゆれ設定（japanese_variations.yaml）

```yaml
# カタカナ長音符のバリエーション
long_vowel_patterns:
  "ー": ["", "ウ", "ー"]  # インターフェース ↔ インターフェイス

# 英日対訳辞書
english_japanese_pairs:
  "API":
    japanese: ["エーピーアイ", "アプリケーションプログラミングインターフェース"]
    aliases: ["api", "Api"]

# 略語展開辞書
abbreviation_expansions:
  "DB":
    full_form: "データベース"
    english: "Database"
    variations: ["db", "データベース", "database"]
```

### 設定ファイルのカスタマイズ

設定ファイルを編集して、プロジェクト固有の用語や表記ゆれに対応できます：

```yaml
# user_defined_keywords セクションに追加
user_defined_keywords:
  custom_important:
    - "マイプロジェクト"
    - "重要な専門用語"

  custom_exclude:
    - "除外したい単語"

# user_defined_patterns セクションに追加
user_defined_patterns:
  custom_variations:
    "カスタム用語":
      - "バリエーション1"
      - "バリエーション2"
```

## 🔧 高度な使い方

### バッチ処理

```bash
# 複数のボルトを一括処理
for vault in vault1 vault2 vault3; do
  uv run python -m knowledge_base_organizer maintain "$vault" --dry-run
done

# 定期メンテナンススクリプト
#!/bin/bash
VAULT_PATH="/path/to/your/vault"
DATE=$(date +%Y%m%d)

echo "=== 日次メンテナンス ($DATE) ==="
uv run python -m knowledge_base_organizer maintain "$VAULT_PATH" \
  --task organize --task dead-links \
  --output-format json \
  --output "maintenance-report-$DATE.json"
```

### 結果の活用

```bash
# JSON結果をjqで加工
uv run python -m knowledge_base_organizer analyze /path/to/vault --output-format json | jq '.file_statistics'

# メンテナンスレポートから問題ファイルを抽出
uv run python -m knowledge_base_organizer maintain /path/to/vault --output-format json | \
  jq -r '.tasks.dead_links.sample_dead_links[] | "\(.source_file):\(.line_number) - \(.link_text)"'

# CSV結果をExcelで開く
uv run python -m knowledge_base_organizer detect-dead-links /path/to/vault --output-format csv --output dead-links.csv
```

### 設定ディレクトリの指定

```bash
# カスタム設定ディレクトリを使用（将来実装予定）
export KNOWLEDGE_BASE_CONFIG_DIR="/path/to/custom/config"
uv run python -m knowledge_base_organizer analyze /path/to/vault
```

## 🚨 注意事項と推奨事項

### 初回実行時の推奨手順

1. **必ずバックアップを取る**: 重要なデータは事前にバックアップ
2. **分析から開始**: まず `analyze` コマンドでボルトの現状を把握
3. **maintainコマンドを使用**: `maintain` コマンドで包括的な問題を確認
4. **dry-runで確認**: `--dry-run` で変更内容を事前確認
5. **小規模から開始**: `--max-files 5` などで少数のファイルから試す

```bash
# 推奨初回実行手順
uv run python -m knowledge_base_organizer analyze /path/to/vault --verbose
uv run python -m knowledge_base_organizer maintain /path/to/vault --dry-run
uv run python -m knowledge_base_organizer maintain /path/to/vault --task organize --execute --max-files 10
```

### 大規模ボルト（1000+ファイル）での使用

```bash
# 段階的メンテナンス
uv run python -m knowledge_base_organizer maintain /path/to/vault --task organize --max-files 100 --dry-run
uv run python -m knowledge_base_organizer maintain /path/to/vault --task dead-links --dry-run
uv run python -m knowledge_base_organizer auto-link /path/to/vault --execute --max-files 50 --max-links 5

# 特定ディレクトリから開始
uv run python -m knowledge_base_organizer maintain /path/to/vault \
  --include "101_PermanentNotes/**" \
  --task organize --execute
```

### パフォーマンス最適化

```bash
# 重要なディレクトリのみ処理
uv run python -m knowledge_base_organizer maintain /path/to/vault \
  --include "101_PermanentNotes/**" \
  --include "100_FleetingNotes/**" \
  --exclude "900_Templates/**" \
  --exclude "Archive/**"

# 処理時間を短縮
uv run python -m knowledge_base_organizer auto-link /path/to/vault \
  --max-files 50 --max-links 10 --exclude-tables
```

### 安全性のベストプラクティス

- **Git管理**: ボルトをGitで管理し、変更前にコミット
- **段階的適用**: 一度に大量の変更を適用せず、段階的に実行
- **定期バックアップ**: 重要なボルトは定期的にバックアップ
- **テスト環境**: 本番ボルトの前にテスト用コピーで試行

## 🆘 トラブルシューティング

### よくある問題と解決方法

**Q: フロントマターの検証でエラーが出る**

```bash
# 詳細なエラー情報を確認
uv run python -m knowledge_base_organizer validate-frontmatter /path/to/vault --dry-run --verbose

# maintainコマンドで包括的に確認
uv run python -m knowledge_base_organizer maintain /path/to/vault --task organize --dry-run

# 特定のテンプレートのみ検証
uv run python -m knowledge_base_organizer validate-frontmatter /path/to/vault --template specific-template --dry-run
```

**Q: 自動リンク生成で意図しないリンクが作られる**

```bash
# より厳しい条件で実行
uv run python -m knowledge_base_organizer auto-link /path/to/vault --dry-run --max-links 1 --exclude-tables

# 特定のコンテンツパターンを除外
uv run python -m knowledge_base_organizer auto-link /path/to/vault \
  --exclude-content "TODO|FIXME|Draft" --dry-run
```

**Q: 処理が遅い・メモリを大量消費する**

```bash
# ファイル数を制限
uv run python -m knowledge_base_organizer maintain /path/to/vault --max-files 50

# 特定のディレクトリのみ処理
uv run python -m knowledge_base_organizer maintain /path/to/vault \
  --include "101_PermanentNotes/**" --task organize
```

**Q: デッドリンクが大量に検出される**

```bash
# 修正提案があるもののみ確認
uv run python -m knowledge_base_organizer detect-dead-links /path/to/vault --only-with-suggestions

# 特定のリンクタイプのみチェック
uv run python -m knowledge_base_organizer detect-dead-links /path/to/vault --link-type wikilink
```

**Q: 日本語のリンク生成がうまくいかない**

```bash
# 設定ファイルを確認・編集
# src/knowledge_base_organizer/config/japanese_variations.yaml
# src/knowledge_base_organizer/config/keyword_extraction.yaml

# プロジェクト固有の用語を追加後、再実行
uv run python -m knowledge_base_organizer auto-link /path/to/vault --dry-run
```

**Q: メンテナンスレポートの内容を詳しく知りたい**

```bash
# JSON形式で詳細レポートを出力
uv run python -m knowledge_base_organizer maintain /path/to/vault \
  --output-format json --output detailed-report.json

# 特定のタスクのみ詳細確認
uv run python -m knowledge_base_organizer maintain /path/to/vault \
  --task duplicates --verbose --dry-run
```

**Q: 設定をプロジェクト固有にカスタマイズしたい**

```bash
# 設定ファイルをコピーしてカスタマイズ
cp src/knowledge_base_organizer/config/keyword_extraction.yaml my-config.yaml
# my-config.yamlを編集後、将来的には --config オプションで指定予定
```

### エラーメッセージ別対処法

**`FileNotFoundError: Vault path does not exist`**

- ボルトパスが正しいか確認
- 相対パスではなく絶対パスを使用

**`PermissionError: Permission denied`**

- ファイルの読み書き権限を確認
- Obsidianが開いている場合は一時的に閉じる

**`MemoryError` または処理が非常に遅い**

- `--max-files` オプションでファイル数を制限
- 大きなファイルを `--exclude` で除外

**`UnicodeDecodeError`**

- ファイルエンコーディングの問題
- 問題のあるファイルを特定して修正または除外

## 🔗 関連リンク

- [Obsidian](https://obsidian.md/) - ナレッジベース管理ツール
- [uv](https://docs.astral.sh/uv/) - Python パッケージマネージャー

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 📚 実践例とワークフロー

### 新しいボルトを整理する完全ワークフロー

```bash
# 1. まずボルトの現状を把握
uv run python -m knowledge_base_organizer analyze /path/to/vault --verbose

# 2. 包括的メンテナンス分析（推奨）
uv run python -m knowledge_base_organizer maintain /path/to/vault --dry-run --verbose

# 3. AI強化フロントマター改善（段階的）
uv run python -m knowledge_base_organizer organize /path/to/vault --ai-suggest-metadata --dry-run --max-files 10
uv run python -m knowledge_base_organizer organize /path/to/vault --ai-suggest-metadata --execute --interactive --max-files 10

# 4. 従来の問題解決
uv run python -m knowledge_base_organizer maintain /path/to/vault --task dead-links --dry-run

# 5. 自動リンク生成（少数から開始）
uv run python -m knowledge_base_organizer auto-link /path/to/vault --execute --max-files 10 --max-links 5

# 6. 最終確認と全体レポート
uv run python -m knowledge_base_organizer maintain /path/to/vault --output-format json --output final-report.json
```

### AI機能を活用したワークフロー

```bash
# AI強化ワークフロー（推奨）

# 1. 現状分析
uv run python -m knowledge_base_organizer analyze /path/to/vault --verbose

# 2. AI提案の確認（安全）
uv run python -m knowledge_base_organizer organize /path/to/vault --ai-suggest-metadata --dry-run --max-files 5

# 3. インタラクティブ適用
uv run python -m knowledge_base_organizer organize /path/to/vault --ai-suggest-metadata --execute --interactive --max-files 10

# 4. 重要ファイルの要約生成
for file in important-notes/*.md; do
  uv run python -m knowledge_base_organizer summarize "$file" --output "${file%.md}-summary.md"
done

# 5. 全体の健康状態確認
uv run python -m knowledge_base_organizer maintain /path/to/vault --output-format json --output ai-enhanced-report.json
```

### 日常的なメンテナンス

```bash
# 日次メンテナンススクリプト例
#!/bin/bash
VAULT_PATH="/path/to/your/vault"
DATE=$(date +%Y%m%d)

echo "=== 日次ボルトメンテナンス ($DATE) ==="

# 包括的メンテナンス実行
uv run python -m knowledge_base_organizer maintain "$VAULT_PATH" \
  --task organize --task dead-links \
  --output-format json \
  --output "maintenance-report-$DATE.json"

# 新しいリンク機会の確認
uv run python -m knowledge_base_organizer auto-link "$VAULT_PATH" \
  --dry-run --max-links 5 \
  --output-format console

echo "=== メンテナンス完了 ==="
```

### 大規模ボルト（1000+ファイル）での安全な処理

```bash
# 段階1: 分析とプランニング
uv run python -m knowledge_base_organizer analyze /path/to/large-vault --output-format json > analysis.json
uv run python -m knowledge_base_organizer maintain /path/to/large-vault --dry-run --output-format json > maintenance-plan.json

# 段階2: 重要ディレクトリから開始
uv run python -m knowledge_base_organizer maintain /path/to/large-vault \
  --include "101_PermanentNotes/**" \
  --task organize --execute --backup

# 段階3: 段階的拡張
uv run python -m knowledge_base_organizer maintain /path/to/large-vault \
  --include "100_FleetingNotes/**" \
  --task organize --task dead-links --execute

# 段階4: 自動リンク生成（慎重に）
uv run python -m knowledge_base_organizer auto-link /path/to/large-vault \
  --execute --max-files 100 --max-links 10 --exclude-tables

# 段階5: 最終確認
uv run python -m knowledge_base_organizer maintain /path/to/large-vault \
  --output-format json --output final-analysis.json
```

### プロジェクト別カスタマイズ例

```bash
# 学術研究ボルト用（AI強化）
uv run python -m knowledge_base_organizer organize /path/to/academic-vault \
  --ai-suggest-metadata --include "Papers/**" --include "Notes/**" \
  --exclude "Drafts/**" --execute --interactive

# 論文要約の一括生成
find /path/to/academic-vault/Papers -name "*.md" -exec \
  uv run python -m knowledge_base_organizer summarize {} --max-length 300 --output {}-abstract.md \;

# ソフトウェア開発ボルト用（技術タグ強化）
uv run python -m knowledge_base_organizer organize /path/to/dev-vault \
  --ai-suggest-metadata --include "Projects/**" --include "TechNotes/**" \
  --execute --backup

# 技術文書の要約生成
uv run python -m knowledge_base_organizer summarize /path/to/dev-vault/architecture-design.md \
  --max-length 400 --output project-summary.md

# 個人日記・メモボルト用（軽量AI処理）
uv run python -m knowledge_base_organizer organize /path/to/personal-vault \
  --ai-suggest-metadata --include "Daily/**" --include "Thoughts/**" \
  --max-improvements 10 --execute

# 日記エントリの要約
uv run python -m knowledge_base_organizer summarize /path/to/personal-vault/Daily/2024-01-15.md \
  --max-length 150
```

## 🎨 カスタマイズと自動化

### 特定用途向けの設定

```bash
# 学術研究ボルト用（厳密なメンテナンス）
uv run python -m knowledge_base_organizer maintain /path/to/academic-vault \
  --task organize --task dead-links \
  --include "Papers/**" --include "Research/**" \
  --execute --backup

# 日記・個人メモボルト用（軽いリンク生成）
uv run python -m knowledge_base_organizer auto-link /path/to/diary-vault \
  --execute --max-links 2 --exclude-tables \
  --include "Daily/**" --include "Thoughts/**"

# ソフトウェア開発ボルト用（包括的整理）
uv run python -m knowledge_base_organizer maintain /path/to/dev-vault \
  --task organize --task duplicates --task orphans \
  --include "Projects/**" --include "TechNotes/**" \
  --execute --interactive

# メインコンテンツのみ処理（テンプレートやアーカイブを除外）
uv run python -m knowledge_base_organizer maintain /path/to/vault \
  --include "100_FleetingNotes/**" \
  --include "101_PermanentNotes/**" \
  --include "102_Literature/**" \
  --exclude "900_Templates/**" \
  --exclude "Archive/**" \
  --exclude "*.draft.md" \
  --task organize --task dead-links
```

### 出力結果の活用とレポート生成

```bash
# メンテナンスレポートからTODOリストを生成
uv run python -m knowledge_base_organizer maintain /path/to/vault --output-format json | \
  jq -r '.tasks.dead_links.sample_dead_links[] | "- [ ] Fix: [\(.link_text)](\(.source_file):\(.line_number))"' > maintenance-todo.md

# ボルト健康状態の可視化
uv run python -m knowledge_base_organizer maintain /path/to/vault --output-format json | \
  jq '.summary | "Health Score: \(.vault_health_score)%, Issues: \(.total_issues_found)"'

# フロントマター統計をCSVで出力
uv run python -m knowledge_base_organizer analyze /path/to/vault --output-format json | \
  jq -r '.frontmatter_statistics.most_common_fields[] | "\(.[0]),\(.[1])"' > frontmatter-stats.csv

# 重複ファイル検出結果の整理
uv run python -m knowledge_base_organizer maintain /path/to/vault --task duplicates --output-format json | \
  jq -r '.tasks.duplicates.details[] | "\(.file_path) has \(.duplicate_count) potential duplicates"'
```

### 自動化スクリプトの例

```bash
# 週次メンテナンススクリプト
#!/bin/bash
# weekly-maintenance.sh

VAULT_PATH="/path/to/vault"
REPORT_DIR="/path/to/reports"
DATE=$(date +%Y%m%d)

mkdir -p "$REPORT_DIR"

echo "=== 週次ボルトメンテナンス開始 ($DATE) ==="

# 1. 現状分析
uv run python -m knowledge_base_organizer analyze "$VAULT_PATH" \
  --output-format json > "$REPORT_DIR/analysis-$DATE.json"

# 2. 包括的メンテナンス
uv run python -m knowledge_base_organizer maintain "$VAULT_PATH" \
  --task organize --task dead-links --task duplicates \
  --output-format json > "$REPORT_DIR/maintenance-$DATE.json"

# 3. 健康スコアの表示
HEALTH_SCORE=$(jq -r '.summary.vault_health_score' "$REPORT_DIR/maintenance-$DATE.json")
echo "ボルト健康スコア: ${HEALTH_SCORE}%"

# 4. 問題があれば通知（例：Slack、メール等）
if (( $(echo "$HEALTH_SCORE < 80" | bc -l) )); then
  echo "⚠️ ボルトの健康状態が低下しています。メンテナンスが必要です。"
fi

echo "=== 週次メンテナンス完了 ==="
```

## 🔄 継続的改善とワークフロー統合

### Git統合による安全な改善

```bash
# 変更前にコミット
git add . && git commit -m "Before knowledge-base-organizer maintenance"

# 包括的メンテナンス実行
uv run python -m knowledge_base_organizer maintain /path/to/vault --execute --backup

# 結果確認とコミット
git add . && git commit -m "Apply knowledge-base-organizer maintenance

- Fixed frontmatter issues: $(jq -r '.tasks.organize.files_with_improvements' maintenance-report.json) files
- Resolved dead links: $(jq -r '.tasks.dead_links.total_dead_links' maintenance-report.json) links
- Health score improved to: $(jq -r '.summary.vault_health_score' maintenance-report.json)%"
```

### CI/CD統合による品質管理

```yaml
# .github/workflows/vault-quality-check.yml
name: Vault Quality Check
on:
  push:
    paths: ['vault/**']
  pull_request:
    paths: ['vault/**']
  schedule:
    - cron: '0 9 * * 1'  # 毎週月曜日9時

jobs:
  quality-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v1

      - name: Install dependencies
        run: uv sync

      - name: Analyze vault health
        run: |
          uv run python -m knowledge_base_organizer analyze vault/ \
            --output-format json > analysis-report.json

      - name: Run comprehensive maintenance check
        run: |
          uv run python -m knowledge_base_organizer maintain vault/ \
            --dry-run --output-format json > maintenance-report.json

      - name: Check vault health score
        run: |
          HEALTH_SCORE=$(jq -r '.summary.vault_health_score' maintenance-report.json)
          echo "Vault Health Score: ${HEALTH_SCORE}%"
          if (( $(echo "$HEALTH_SCORE < 70" | bc -l) )); then
            echo "::warning::Vault health score is below 70%. Consider running maintenance."
            exit 1
          fi

      - name: Upload reports
        uses: actions/upload-artifact@v3
        with:
          name: vault-reports
          path: |
            analysis-report.json
            maintenance-report.json
```

### 定期メンテナンスの自動化

```bash
# crontab設定例（毎日午前2時に実行）
# 0 2 * * * /path/to/daily-maintenance.sh

#!/bin/bash
# daily-maintenance.sh

VAULT_PATH="/path/to/vault"
LOG_DIR="/path/to/logs"
DATE=$(date +%Y%m%d)

# ログディレクトリ作成
mkdir -p "$LOG_DIR"

# Git作業ディレクトリに移動
cd "$VAULT_PATH" || exit 1

# 変更前にコミット
git add . && git commit -m "Daily backup before maintenance ($DATE)" || true

# メンテナンス実行
uv run python -m knowledge_base_organizer maintain . \
  --task organize --task dead-links \
  --execute --backup \
  --output-format json > "$LOG_DIR/maintenance-$DATE.json" 2>&1

# 結果をGitにコミット
if [ -s "$LOG_DIR/maintenance-$DATE.json" ]; then
  HEALTH_SCORE=$(jq -r '.summary.vault_health_score' "$LOG_DIR/maintenance-$DATE.json")
  git add . && git commit -m "Daily maintenance completed ($DATE)

Health Score: ${HEALTH_SCORE}%
Report: $LOG_DIR/maintenance-$DATE.json" || true
fi
```

### Obsidianプラグインとの連携

```javascript
// Obsidian プラグイン内での実行例
const { exec } = require('child_process');

// メンテナンス実行
exec('uv run python -m knowledge_base_organizer maintain . --dry-run --output-format json',
  { cwd: this.app.vault.adapter.basePath },
  (error, stdout, stderr) => {
    if (error) {
      new Notice('メンテナンスチェックでエラーが発生しました');
      return;
    }

    const report = JSON.parse(stdout);
    const healthScore = report.summary.vault_health_score;

    new Notice(`ボルト健康スコア: ${healthScore}%`);

    if (healthScore < 80) {
      new Notice('メンテナンスが推奨されます', 5000);
    }
  }
);
```

---

## 🔗 関連リンク・参考資料

- [Obsidian](https://obsidian.md/) - ナレッジベース管理ツール
- [uv](https://docs.astral.sh/uv/) - Python パッケージマネージャー
- [Rich](https://rich.readthedocs.io/) - 美しいターミナル出力ライブラリ
- [Typer](https://typer.tiangolo.com/) - 現代的なCLIフレームワーク

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

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
uv run pytest tests/cli/test_maintain_command.py -v

# 統合テスト実行
uv run pytest tests/integration/ -v
```

### コード品質チェック

```bash
# リンティング
uv run ruff check src tests

# フォーマット
uv run ruff format src tests

# 型チェック
uv run mypy src

# セキュリティチェック
uv run bandit -r src/
```

### アーキテクチャ

```
src/knowledge_base_organizer/
├── cli/                    # CLIインターフェース
│   ├── main.py            # メインCLI
│   ├── maintain_command.py # メンテナンスコマンド
│   └── organize_command.py # 整理コマンド
├── application/            # ユースケース層
│   ├── auto_link_generation_use_case.py
│   ├── dead_link_detection_use_case.py
│   └── frontmatter_validation_use_case.py
├── domain/                 # ドメインロジック
│   ├── models.py          # ドメインモデル
│   └── services/          # ドメインサービス
│       ├── link_analysis_service.py
│       ├── content_analysis_service.py
│       └── keyword_extraction_manager.py
├── infrastructure/         # インフラ層
│   ├── file_repository.py
│   └── template_schema_repository.py
└── config/                # 設定ファイル
    ├── keyword_extraction.yaml
    └── japanese_variations.yaml
```

### 新機能の追加

1. **仕様作成**: `.kiro/specs/` にspecファイルを作成
2. **テスト駆動開発**: テストを先に書く
3. **実装**: 段階的に機能を実装
4. **統合テスト**: 実際のボルトでテスト
5. **ドキュメント更新**: README.mdとヘルプテキストを更新

### 設定ファイルの拡張

新しい言語や専門分野に対応する場合：

1. `config/keyword_extraction.yaml` に専門用語を追加
2. `config/japanese_variations.yaml` に表記ゆれパターンを追加
3. テストケースを作成して動作確認

### 貢献方法

1. Issueを作成して議論
2. フィーチャーブランチを作成
3. テストを含む実装
4. プルリクエストを作成

詳細は [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。

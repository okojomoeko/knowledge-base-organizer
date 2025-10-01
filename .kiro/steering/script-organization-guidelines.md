---
inclusion: always
---

# Script Organization Guidelines

## 🏗️ 理想的なフォルダ構造とスクリプト管理

### プロジェクト構造原則

```
knowledge-base-organizer/
├── scripts/                    # 実行スクリプト
│   ├── automation/            # 自動化スクリプト
│   ├── development/           # 開発支援スクリプト
│   ├── testing/              # テスト実行スクリプト
│   └── deployment/           # デプロイメントスクリプト
├── examples/                  # 使用例とデモ
├── docs/                     # ドキュメント
├── src/                      # ソースコード
└── tests/                    # テストコード
```

### スクリプト作成ルール

#### 🚨 長いコマンド回避原則

**10行以上のコマンドや複雑な処理は必ずスクリプトファイルに分離すること**

❌ **避けるべき例**:

```bash
# 長いコマンドをターミナルで直接実行
uv run python -m pytest tests/unit/domain/services/test_automation_scheduler.py tests/unit/domain/services/test_continuous_improvement_system.py tests/unit/domain/services/test_auto_improvement_engine.py -v --cov=src/knowledge_base_organizer/domain/services --cov-report=html --cov-report=term-missing --tb=short
```

✅ **正しい例**:

```bash
# scripts/testing/run_learning_tests.sh
#!/bin/bash
uv run python -m pytest \
    tests/unit/domain/services/test_automation_scheduler.py \
    tests/unit/domain/services/test_continuous_improvement_system.py \
    tests/unit/domain/services/test_auto_improvement_engine.py \
    -v --cov=src/knowledge_base_organizer/domain/services \
    --cov-report=html --cov-report=term-missing --tb=short
```

### スクリプトカテゴリ別配置

#### 1. `scripts/automation/` - 自動化スクリプト

- 定期実行スクリプト
- CI/CDパイプライン
- メンテナンススクリプト

#### 2. `scripts/development/` - 開発支援スクリプト

- コード生成スクリプト
- 開発環境セットアップ
- デバッグ支援ツール

#### 3. `scripts/testing/` - テスト実行スクリプト

- 単体テスト実行
- 統合テスト実行
- パフォーマンステスト

#### 4. `scripts/deployment/` - デプロイメントスクリプト

- ビルドスクリプト
- パッケージング
- リリース準備

### スクリプト命名規則

```bash
# 形式: [動詞]_[対象]_[詳細].sh
run_all_tests.sh
build_documentation.sh
deploy_to_staging.sh
setup_development_env.sh
```

### スクリプトテンプレート

```bash
#!/bin/bash
# Script: [スクリプト名]
# Purpose: [目的の説明]
# Usage: ./script_name.sh [arguments]

set -euo pipefail  # エラー時即座終了、未定義変数エラー、パイプエラー検出

# 設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 関数定義
log_info() {
    echo "ℹ️  $1"
}

log_error() {
    echo "❌ $1" >&2
}

log_success() {
    echo "✅ $1"
}

# メイン処理
main() {
    log_info "Starting [スクリプト名]..."

    # 処理内容

    log_success "[スクリプト名] completed successfully"
}

# エラーハンドリング
trap 'log_error "Script failed at line $LINENO"' ERR

# 実行
main "$@"
```

### 実行権限管理

```bash
# スクリプト作成後は実行権限を付与
chmod +x scripts/category/script_name.sh

# プロジェクトルートから実行
./scripts/category/script_name.sh
```

### ドキュメント化

各スクリプトディレクトリに`README.md`を配置：

```markdown
# Scripts Directory

## Available Scripts

### automation/
- `daily_maintenance.sh` - 日次メンテナンス実行
- `quality_metrics_collection.sh` - 品質メトリクス収集

### development/
- `setup_dev_env.sh` - 開発環境セットアップ
- `generate_docs.sh` - ドキュメント生成

### testing/
- `run_all_tests.sh` - 全テスト実行
- `run_learning_tests.sh` - 学習システムテスト実行

### deployment/
- `build_package.sh` - パッケージビルド
- `prepare_release.sh` - リリース準備
```

### Git管理

```gitignore
# スクリプトは基本的にコミット対象
scripts/**/*.sh

# ただし、機密情報を含む設定ファイルは除外
scripts/**/*.env
scripts/**/*_secrets.sh
scripts/**/config_local.sh
```

### 実行ログ管理

```bash
# ログディレクトリ構造
logs/
├── automation/
├── development/
├── testing/
└── deployment/

# スクリプト内でのログ出力例
LOG_DIR="$PROJECT_ROOT/logs/$(basename "$(dirname "$0")")"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/$(basename "$0" .sh)_$(date +%Y%m%d_%H%M%S).log"

# ログ出力とコンソール出力の両方
exec > >(tee -a "$LOG_FILE")
exec 2>&1
```

### パフォーマンス考慮

- 長時間実行スクリプトには進捗表示を追加
- 大量データ処理時はメモリ使用量を監視
- 並列処理可能な部分は適切に並列化

### セキュリティ

- 機密情報は環境変数や別ファイルで管理
- スクリプト実行前の権限チェック
- 入力値の適切なバリデーション

この構造に従って、今後のスクリプト開発を行ってください。

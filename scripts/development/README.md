# Development Scripts

## 高速開発ワークフロー

### 日常開発用（高速）

```bash
# 高速な開発環境セットアップ
./scripts/development/setup_fast_dev.sh

# コミット前の高速チェック（30秒以内）
./scripts/development/quick_commit_check.sh

# noxを使った高速チェック
nox -s fast_check
```

### 品質保証用（完全）

```bash
# 完全な品質チェック（リリース前・週次）
./scripts/development/full_quality_check.sh

# セキュリティチェックのみ
nox -s security

# 従来の完全チェック
nox -s lint
nox -s pytest
nox -s lizard
```

## ワークフロー推奨事項

### 日常開発時

1. `quick_commit_check.sh` でコミット前チェック
2. 必要に応じて `setup_fast_dev.sh` で環境リセット
3. pre-commitは軽量設定で自動実行

### リリース前・週次

1. `full_quality_check.sh` で完全チェック
2. 全てのnoxセッションを実行
3. カバレッジレポートを確認

## パフォーマンス改善

- **nox**: `--reinstall` 削除、`uvx` 使用で高速化
- **ruff**: 必須ルールのみ選択（50個→15個）
- **pre-commit**: nox経由を削除、直接実行
- **tests**: 失敗時即停止（`-x`）、短いトレースバック

## 品質基準維持

- 必須ルール（E,F,W,I,UP,B）は厳格に維持
- セキュリティチェックは週次で実行
- 型チェックはリリース前に実行
- カバレッジ要件は維持（60%以上）

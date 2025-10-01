---
inclusion: always
---

# Safe Development Workflow Guidelines

## ブランチ戦略とワークフロー

### 🚨 重要原則

- **mainブランチでの直接作業禁止**: mainブランチでは機能開発・テストを行わない
- **適切なブランチ分離**: 機能開発とテストで異なるブランチを使用
- **ユーザー操作回避**: インタラクティブなgitコマンドは使用しない

### ブランチ命名規則

#### 機能開発ブランチ

```bash
# 形式: feature-機能名-YYYYMMDD
feature-enhanced-linking-20250811
feature-smart-cleanup-20250811
feature-content-analysis-20250811
```

#### テスト用ブランチ

```bash
# 形式: test-YYYYMMDD または test-機能名-YYYYMMDD
test-20250811
test-enhanced-linking-20250811
test-frontmatter-fix-20250811
```

#### 実験用ブランチ

```bash
# 形式: experiment-内容-YYYYMMDD
experiment-link-generation-20250811
experiment-performance-test-20250811
```

## 安全な開発ワークフロー

### Phase 1: ブランチ作成と切り替え

```bash
# 1. mainブランチから最新を取得
git checkout main
git pull origin main

# 2. 機能開発ブランチを作成
git checkout -b feature-enhanced-linking-$(date +%Y%m%d)

# または テスト用ブランチを作成
git checkout -b test-$(date +%Y%m%d)
```

### Phase 2: 安全な変更確認

```bash
# ❌ 危険: インタラクティブなコマンド
git diff

# ✅ 安全: 非インタラクティブなコマンド
git --no-pager diff
git --no-pager diff --stat
git --no-pager diff --name-only
git status --porcelain
```

### Phase 3: 段階的コミット

```bash
# 変更内容を確認
git --no-pager diff --stat

# 段階的にファイルを追加
git add specific-files-only

# 意味のあるコミットメッセージ
git commit -m "feat: implement specific feature

- Add specific functionality
- Fix specific issue
- Test completed successfully"
```

### Phase 4: 安全なマージ

```bash
# mainに戻る前に最終確認
git --no-pager diff main..HEAD --stat

# mainブランチに切り替え
git checkout main

# Fast-forwardマージ（安全）
git merge feature-enhanced-linking-20250811

# ブランチクリーンアップ
git branch -d feature-enhanced-linking-20250811
```

## Git コマンド使用ガイドライン

### ✅ 推奨コマンド（非インタラクティブ）

```bash
# 状態確認
git status --porcelain
git --no-pager diff
git --no-pager diff --stat
git --no-pager diff --name-only
git --no-pager log --oneline -10

# ブランチ操作
git branch
git checkout -b branch-name
git checkout branch-name

# 変更管理
git add .
git add specific-file
git commit -m "message"
git merge branch-name
```

### ❌ 避けるべきコマンド（インタラクティブ）

```bash
# これらは避ける
git diff                    # ページャーが起動
git log                     # ページャーが起動
git show                    # ページャーが起動
git blame                   # ページャーが起動
git rebase -i              # インタラクティブ
git add -p                 # インタラクティブ
```

## 実際の作業例

### Enhanced Linking テスト例

```bash
# 1. テスト用ブランチ作成
git checkout main
git checkout -b test-enhanced-linking-$(date +%Y%m%d)

# 2. テスト実行
uv run python -m knowledge_base_organizer enhanced-linking /path/to/vault --dry-run

# 3. 実際のテスト（少数）
uv run python -m knowledge_base_organizer enhanced-linking /path/to/vault --max-links 5

# 4. 変更確認（非インタラクティブ）
git --no-pager diff --stat
git --no-pager diff --name-only

# 5. 問題なければコミット
git add .
git commit -m "test: enhanced linking with 5 links

- Successfully generated 5 links
- Frontmatter protection working correctly
- No errors encountered"

# 6. mainにマージ（必要に応じて）
git checkout main
git merge test-enhanced-linking-$(date +%Y%m%d)
```

### myvault テスト時の特別な注意

```bash
# myvault変更前に必ずバックアップブランチ作成
git checkout -b backup-myvault-$(date +%Y%m%d%H%M%S)
git checkout -b test-myvault-$(date +%Y%m%d)

# テスト後、問題があれば即座に復旧
git checkout backup-myvault-$(date +%Y%m%d%H%M%S)
git checkout -b recovery-$(date +%Y%m%d%H%M%S)
```

## エラー時の復旧手順

### 1. 変更の取り消し

```bash
# 作業ディレクトリの変更を破棄
git checkout -- .

# 特定ファイルの変更を破棄
git checkout -- specific-file

# 最後のコミットに戻す
git reset --hard HEAD
```

### 2. ブランチの復旧

```bash
# 前のコミットに戻す
git reset --hard HEAD~1

# 特定のコミットに戻す
git reset --hard commit-hash

# mainブランチの状態に戻す
git checkout main
git checkout -b recovery-$(date +%Y%m%d)
```

### 3. myvault の緊急復旧

```bash
# test-myvault タグから復旧（既存のタグがある場合）
git checkout test-myvault -- myvault/
git add myvault/
git commit -m "emergency: restore myvault from test-myvault tag"

# または、前のコミットから復旧
git checkout HEAD~1 -- myvault/
git add myvault/
git commit -m "emergency: restore myvault from previous commit"
```

## 自動化スクリプト例

### 安全なテストブランチ作成

```bash
#!/bin/bash
# create-test-branch.sh

BRANCH_NAME="test-$(date +%Y%m%d)"
echo "Creating test branch: $BRANCH_NAME"

git checkout main
git pull origin main
git checkout -b "$BRANCH_NAME"

echo "Test branch created successfully: $BRANCH_NAME"
echo "Ready for testing!"
```

### 変更確認スクリプト

```bash
#!/bin/bash
# check-changes.sh

echo "=== Git Status ==="
git status --porcelain

echo -e "\n=== Changed Files ==="
git --no-pager diff --name-only

echo -e "\n=== Change Statistics ==="
git --no-pager diff --stat

echo -e "\n=== myvault Changes ==="
git --no-pager diff --name-only | grep "^myvault/" | head -10
```

## 品質保証チェックリスト

### テスト実行前

- [ ] 適切なテストブランチで作業している
- [ ] mainブランチではない
- [ ] バックアップが作成されている

### テスト実行中

- [ ] dry-runモードで事前確認
- [ ] 少数のファイルから開始
- [ ] 段階的に実行

### テスト完了後

- [ ] 変更内容を非インタラクティブで確認
- [ ] フロントマターが破壊されていない
- [ ] 意図しない変更がない
- [ ] 適切なコミットメッセージ

### マージ前

- [ ] 全ての変更が意図的
- [ ] テストが成功している
- [ ] コンフリクトがない
- [ ] mainブランチが最新

この安全なワークフローに従うことで、リスクを最小化しながら効率的な開発・テストが可能になります。

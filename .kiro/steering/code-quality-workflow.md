---
inclusion: always
---

# Code Quality Workflow

## 必須ルール: コード品質チェック

### 🚨 重要原則

**Pythonファイル作成・変更時は必ずruffチェックとフォーマットを実行すること**

### ファイル作成・変更時の必須ステップ

1. **ruffチェック実行**

   ```bash
   uv run ruff check src/ tests/
   ```

2. **ruffフォーマット実行**

   ```bash
   uv run ruff format src/ tests/
   ```

3. **テスト実行確認**

   ```bash
   uv run pytest
   ```

   - テストがFAILしないことを確認
   - カバレッジ要件を満たすことを確認

4. **診断チェック**

   ```bash
   # 必要に応じて型チェックなど
   uv run mypy src/
   ```

### コミット前チェックリスト

- [ ] ruff check でエラーがない
- [ ] ruff format が実行済み
- [ ] pytest が成功する
- [ ] カバレッジ要件を満たしている
- [ ] 重要な型アノテーションが追加されている
- [ ] `uv run pre-commit run`が全てpassしている

### 品質基準

- **型アノテーション**: 公開関数・メソッドには必須
- **定数使用**: マジックナンバーは定数として定義
- **エラーハンドリング**: 適切な例外処理
- **テストカバレッジ**: 最低60%以上（理想は80%以上）

### 自動化

pre-commitフックを使用して自動化することを推奨：

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

この workflow に従うことで、一貫した高品質なコードを維持できます。

# Test Output Results

このディレクトリには、**正式なテストスイート実行時**に生成される出力ファイルが保存されます。

## 目的

- `pytest` 実行時に生成されるファイルをプロジェクトルートに散らかさない
- テスト結果の比較・検証用データの保存
- CI/CD環境での出力ファイル管理

## 実験結果との区別

- **実験結果**: `experiments/experiment_results/` に保存
- **テスト出力**: このディレクトリに保存

## ファイルの種類

- `*.json` - JSON形式のテスト出力
- `*.csv` - CSV形式のテスト出力
- `*.md` - マークダウン形式のレポート

## 管理方針

- テスト実行前後で自動的にクリーンアップされます
- 一時的なテスト出力は `.gitignore` で除外
- 長期保存が必要な場合は明示的に管理

## 使用方法

テストコードから以下のユーティリティ関数を使用：

```python
from tests.cli.test_utils import save_test_output, cleanup_test_files

# テスト出力を保存
save_test_output(content, "test_result.json")

# テスト後のクリーンアップ
cleanup_test_files("*.json")
```

## 注意

このディレクトリは通常空であることが期待されます。ファイルが残っている場合は、テストのクリーンアップが正常に動作していない可能性があります。

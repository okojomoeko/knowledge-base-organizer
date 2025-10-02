# Algorithm Verification Guidelines

## 🧪 実験とアルゴリズム検証の原則

### 必須ルール: experimentsディレクトリでの検証

**複雑なアルゴリズムやパターンマッチングの検証は必ずexperimentsディレクトリで実施すること**

### 検証が必要なケース

- 新しいアルゴリズムの実装前
- パターンマッチングロジックの動作確認
- 複雑な正規表現やglob パターンの検証
- パフォーマンスが重要な処理の最適化
- 外部ライブラリの動作確認
- エッジケースの動作検証

### experimentsディレクトリ構造

```
experiments/
├── pattern_matching/          # パターンマッチング関連
├── performance/              # パフォーマンス検証
├── algorithms/               # アルゴリズム検証
├── regex/                    # 正規表現検証
├── library_behavior/         # ライブラリ動作確認
└── edge_cases/              # エッジケース検証
```

### 実験ファイル命名規則

```bash
# 形式: test_[検証内容]_[日付].py
test_glob_patterns_20250102.py
test_fnmatch_behavior_20250102.py
test_performance_comparison_20250102.py
```

### 実験ファイルテンプレート

```python
#!/usr/bin/env python3
"""
実験: [検証内容の説明]
日付: YYYY-MM-DD
目的: [何を検証するか]
"""

def test_basic_case():
    """基本的なケースの検証"""
    pass

def test_edge_cases():
    """エッジケースの検証"""
    pass

def main():
    """実験実行"""
    print("=== [検証内容] 実験開始 ===")

    test_basic_case()
    test_edge_cases()

    print("=== 実験完了 ===")

if __name__ == "__main__":
    main()
```

### 実験から実装への流れ

1. **仮説設定**: 何を検証したいかを明確にする
2. **実験実施**: experimentsディレクトリで検証
3. **結果分析**: 実験結果を分析し、最適解を特定
4. **実装適用**: 検証済みのアルゴリズムを本体コードに適用
5. **テスト作成**: 実験で確認したケースをテストに追加

### 実験結果の記録

実験ファイル内にコメントで結果を記録：

```python
"""
実験結果:
- fnmatch.fnmatch() は **/pattern/** 形式に対応
- Path.match() は完全パス一致が必要
- パフォーマンス: fnmatch > Path.match (大量ファイル時)

結論:
- exclude pattern には fnmatch.fnmatch() を使用
- include pattern には Path.rglob() を使用
"""
```

### 禁止事項

- ❌ 本体コードで直接アルゴリズム検証
- ❌ テストファイル内での複雑な検証ロジック
- ❌ 実験なしでの複雑なパターンマッチング実装
- ❌ 外部ライブラリの動作を仮定した実装

### 利点

- **リスク軽減**: 本体コードを汚染せずに検証
- **効率向上**: 最適解を事前に特定
- **知識蓄積**: 実験結果が将来の参考になる
- **デバッグ容易**: 問題の切り分けが簡単

この原則に従って、アルゴリズムの検証は必ずexperimentsディレクトリで実施してください。

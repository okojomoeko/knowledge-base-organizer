# Script Architecture Principles

## 絶対ルール: knowledge-base-organizerの機能活用

### 🚨 重要原則

**スクリプト作成時は必ずknowledge-base-organizerの既存機能を使用すること**

- ❌ **禁止**: スクリプト内に独自の処理ロジックを実装
- ✅ **必須**: knowledge-base-organizerのCLIコマンドを実行
- ✅ **必須**: 既存のドメインサービスを活用

### 正しいスクリプトパターン

#### ❌ 間違った例（処理分散）

```python
# スクリプト内で独自実装 - 禁止
class CustomLinkingEngine:
    def find_opportunities(self): # 独自ロジック
        pass
    def apply_links(self): # 独自ロジック
        pass
```

#### ✅ 正しい例（既存機能活用）

```python
# knowledge-base-organizerの機能を使用
subprocess.run([
    "uv", "run", "python", "-m", "knowledge_base_organizer",
    "batch", "autolink", vault_path, "--dry-run"
])

# または既存サービスを直接使用
from knowledge_base_organizer.application.use_cases.link_analysis import LinkAnalysisUseCase
use_case = LinkAnalysisUseCase(...)
results = use_case.execute(...)
```

### スクリプトの役割

スクリプトは以下のみを行う：

1. **パラメータ設定**: 実行条件の指定
2. **既存機能呼び出し**: knowledge-base-organizerのCLI/サービス実行
3. **結果表示**: 実行結果の整理・表示
4. **安全性確認**: dry-run、段階実行の制御

### 機能拡張が必要な場合

スクリプトではなく、knowledge-base-organizer本体を拡張する：

1. **ドメインサービス**に新機能追加
2. **CLIコマンド**に新オプション追加
3. **設定ファイル**で動作制御
4. **スクリプト**は拡張された機能を呼び出すのみ

### 利点

- **処理の一元化**: ロジックがknowledge-base-organizer内に集約
- **保守性向上**: 修正箇所が明確
- **テスト容易性**: 既存のテストスイートで検証可能
- **再利用性**: 他のスクリプトからも同じ機能を利用可能

### 実装チェックリスト

スクリプト作成前に確認：

- [ ] 既存のCLIコマンドで実現可能か？
- [ ] 既存のドメインサービスを活用できるか？
- [ ] 新しい処理ロジックをスクリプトに書こうとしていないか？
- [ ] knowledge-base-organizerの拡張が必要か？

**このルールに従わないスクリプトは作成禁止**

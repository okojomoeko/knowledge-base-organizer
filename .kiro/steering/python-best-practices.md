# Python Best Practices for Knowledge Base Organizer

## プロジェクト管理（uv使用）

### 新規プロジェクト作成

```bash
# プロジェクト初期化
uv init knowledge-base-organizer
cd knowledge-base-organizer

# Python バージョン指定（Python 3.13以上）
uv python pin 3.13

# 本番依存関係追加
uv add pydantic typer rich

# 開発依存関係追加（dependency-groups使用）
uv add --group dev pytest pytest-cov pytest-mock mypy ruff isort bandit

# 仮想環境での実行
uv run python -m knowledge_base_organizer
uv run pytest
```

### pyproject.toml ベストプラクティス

```toml
[project]
name = "knowledge-base-organizer"
version = "0.1.0"
description = "Obsidian vault organizer with advanced Japanese WikiLink detection"
readme = "README.md"
authors = []
requires-python = ">=3.13"
dependencies = [
    "pydantic>=2.11.9",
    "typer>=0.19.2",
    "rich>=13.0.0",
    "pyyaml>=6.0.0",
]

[dependency-groups]
dev = [
    "bandit>=1.8.6",
    "hypothesis>=6.140.2",
    "isort>=6.0.1",
    "mypy>=1.18.2",
    "pytest>=8.4.2",
    "pytest-cov>=7.0.0",
    "pytest-mock>=3.15.1",
    "ruff>=0.13.2",
    "pre-commit>=4.3.0",
]

doc = [
    "furo>=2025.9.25",
    "sphinx>=8.1.3",
    "myst-parser>=4.0.1",
]

[project.scripts]
knowledge-base-organizer = "knowledge_base_organizer:main"

[tool.ruff]
line-length = 88
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "W", "C90", "I", "N", "UP", "YTT", "S", "BLE", "FBT", "B", "A", "COM", "C4", "DTZ", "T10", "EM", "EXE", "FA", "ISC", "ICN", "G", "INP", "PIE", "T20", "PYI", "PT", "Q", "RSE", "RET", "SLF", "SLOT", "SIM", "TID", "TCH", "INT", "ARG", "PTH", "TD", "FIX", "ERA", "PD", "PGH", "PL", "TRY", "FLY", "NPY", "AIR", "PERF", "FURB", "LOG", "RUF"]

[tool.mypy]
python_version = "3.13"
disallow_untyped_defs = true
strict = true
warn_return_any = true
warn_unused_configs = true
```

## コーディング標準

### 型ヒントの徹底

```python
from typing import List, Dict, Optional, Protocol, Union
from pathlib import Path
from dataclasses import dataclass

# 良い例
def analyze_file(file_path: Path, config: Dict[str, Any]) -> Optional[AnalysisResult]:
    pass

# 避けるべき例
def analyze_file(file_path, config):
    pass
```

### Pydanticモデルの活用（dataclassの代替）

```python
from pydantic import BaseModel, Field, field_validator
from pathlib import Path
from typing import Dict, Any, List, Optional

# Pydantic v2スタイル（推奨）
class MarkdownFile(BaseModel):
    model_config = ConfigDict(
        frozen=True,  # イミュータブル
        validate_assignment=True,
        str_strip_whitespace=True
    )

    path: Path
    file_id: str
    frontmatter: Dict[str, Any]
    body_content: str

    @field_validator('path')
    @classmethod
    def validate_path_exists(cls, v: Path) -> Path:
        if not v.exists():
            raise ValueError(f"File does not exist: {v}")
        return v

    @field_validator('file_id')
    @classmethod
    def validate_file_id_format(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 14:
            raise ValueError("file_id must be 14-digit timestamp")
        return v

# Frontmatter専用モデル
class Frontmatter(BaseModel):
    title: str
    aliases: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    id: str
    date: Optional[str] = None
    publish: bool = False

    @field_validator('aliases', 'tags')
    @classmethod
    def remove_duplicates(cls, v: List[str]) -> List[str]:
        return list(dict.fromkeys(v))  # 順序を保持して重複除去
```

### Typer CLIフレームワークの活用

```python
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from pathlib import Path
from typing import List, Optional
from enum import Enum

app = typer.Typer(
    name="knowledge-base-organizer",
    help="Obsidian vault organizer with advanced Japanese WikiLink detection"
)
console = Console()

class OutputFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    CONSOLE = "console"

@app.command()
def validate_frontmatter(
    vault_path: Path = typer.Argument(..., help="Path to Obsidian vault"),
    dry_run: bool = typer.Option(True, "--dry-run/--execute", help="Preview changes without applying"),
    output_format: OutputFormat = typer.Option(OutputFormat.JSON, help="Output format"),
    include_patterns: Optional[List[str]] = typer.Option(None, "--include", help="Include file patterns"),
    exclude_patterns: Optional[List[str]] = typer.Option(None, "--exclude", help="Exclude file patterns"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output")
) -> None:
    """Validate and fix frontmatter according to template schemas."""

    if verbose:
        console.print(f"[bold blue]Processing vault:[/bold blue] {vault_path}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Scanning files...", total=None)

        # Use case execution logic here

        progress.update(task, description="Validation complete!")

@app.command()
def auto_link(
    vault_path: Path = typer.Argument(..., help="Path to Obsidian vault"),
    dry_run: bool = typer.Option(True, "--dry-run/--execute"),
    exclude_tables: bool = typer.Option(False, "--exclude-tables"),
    max_links_per_file: int = typer.Option(50, "--max-links"),
    enable_synonyms: bool = typer.Option(True, "--synonyms/--no-synonyms"),
    confidence_threshold: float = typer.Option(0.7, "--confidence", min=0.0, max=1.0)
) -> None:
    """Generate WikiLinks from plain text with Japanese synonym detection."""
    pass

def main():
    app()

if __name__ == "__main__":
    main()
```

### プロトコルによるインターフェース定義

```python
from typing import Protocol
from pathlib import Path

class FileRepository(Protocol):
    def load_file(self, path: Path) -> MarkdownFile:
        ...

    def save_file(self, file: MarkdownFile) -> None:
        ...

class TemplateSchemaRepository(Protocol):
    def extract_schemas_from_templates(self) -> Dict[str, FrontmatterSchema]:
        ...

    def detect_template_type(self, file: MarkdownFile) -> Optional[str]:
        ...
```

## エラーハンドリング

### カスタム例外の定義

```python
class KnowledgeBaseError(Exception):
    """Base exception for knowledge base operations"""
    pass

class FileProcessingError(KnowledgeBaseError):
    """Raised when file processing fails"""
    def __init__(self, file_path: Path, original_error: Exception):
        self.file_path = file_path
        self.original_error = original_error
        super().__init__(f"Failed to process {file_path}: {original_error}")
```

### グレースフルエラーハンドリング

```python
def process_files(files: List[Path]) -> Tuple[List[AnalysisResult], List[ProcessingError]]:
    results = []
    errors = []

    for file_path in files:
        try:
            result = analyze_file(file_path)
            results.append(result)
        except Exception as e:
            error = ProcessingError(file_path, e)
            errors.append(error)
            logger.warning(f"Skipping file due to error: {error}")

    return results, errors
```

## テスト実装

### テストの構造化

```python
import pytest
from hypothesis import given, strategies as st

class TestMarkdownFileAnalyzer:
    @pytest.fixture
    def sample_file(self, tmp_path):
        file_path = tmp_path / "test.md"
        file_path.write_text("""---
title: Test File
tags: [test, sample]
---
# Test Content
""")
        return file_path

    def test_analyze_valid_file(self, sample_file):
        result = analyze_file(sample_file)
        assert result.frontmatter['title'] == 'Test File'

    @given(st.text())
    def test_analyze_with_random_content(self, content):
        # Property-based testing
        pass
```

## パフォーマンス最適化

### メモリ効率的な処理

```python
from typing import Iterator

def process_files_streaming(base_path: Path) -> Iterator[AnalysisResult]:
    """大量ファイルをストリーミング処理"""
    for file_path in base_path.rglob("*.md"):
        try:
            yield analyze_file(file_path)
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            continue
```

### 並列処理の活用

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

def analyze_files_parallel(files: List[Path], max_workers: int = 4) -> List[AnalysisResult]:
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {executor.submit(analyze_file, file): file for file in files}

        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Error analyzing {file_path}: {e}")

    return results
```

## ログ設定

### 構造化ログの実装

```python
import logging
import json
from datetime import datetime

class StructuredFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        if hasattr(record, 'file_path'):
            log_entry['file_path'] = str(record.file_path)

        return json.dumps(log_entry, ensure_ascii=False)

# 使用例
logger = logging.getLogger(__name__)
logger.info("Processing file", extra={'file_path': file_path})
```

## 設定管理

### Pydanticを使った型安全な設定管理

```python
from pydantic import BaseModel, Field, validator
from typing import List, Literal
from pathlib import Path
import yaml

class AnalysisConfig(BaseModel):
    required_frontmatter_keys: List[str] = Field(..., min_items=1)
    excluded_directories: List[str] = Field(default_factory=list)
    output_format: Literal['json', 'yaml', 'markdown'] = Field(default='json')
    max_workers: int = Field(default=4, ge=1, le=16)

    @validator('required_frontmatter_keys')
    def validate_keys(cls, v):
        if not v:
            raise ValueError("required_frontmatter_keys cannot be empty")
        return v

    @classmethod
    def from_file(cls, config_path: Path) -> 'AnalysisConfig':
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return cls(**data)

    class Config:
        # Pydantic v2では ConfigDict を使用
        validate_assignment = True
        extra = 'forbid'

# Pydantic v2 スタイル（推奨）
from pydantic import BaseModel, ConfigDict, field_validator

class ModernAnalysisConfig(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        extra='forbid',
        str_strip_whitespace=True
    )

    required_frontmatter_keys: List[str] = Field(..., min_length=1)
    excluded_directories: List[str] = Field(default_factory=list)
    output_format: Literal['json', 'yaml', 'markdown'] = 'json'
    max_workers: int = Field(default=4, ge=1, le=16)

    @field_validator('required_frontmatter_keys')
    @classmethod
    def validate_keys(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("required_frontmatter_keys cannot be empty")
        return v
```

## 開発ツールとワークフロー

### Pre-commit フックの設定

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.3.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.13.2
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.18.2
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, typer]

# セットアップ
uv run pre-commit install
uv run pre-commit run --all-files
```

### Ruffによるリンティングとフォーマット

```bash
# リンティング実行
uv run ruff check .

# 自動修正
uv run ruff check --fix .

# フォーマット実行
uv run ruff format .

# 設定確認
uv run ruff check --show-settings
```

### Pytestテスト実行

```bash
# 基本テスト実行
uv run pytest

# カバレッジ付きテスト
uv run pytest --cov=src/knowledge_base_organizer --cov-report=html

# 特定テストファイル実行
uv run pytest tests/unit/domain/test_markdown_file.py -v

# マーカー付きテスト実行
uv run pytest -m "not slow" -v

# 並列テスト実行
uv run pytest -n auto
```

### uvを使った依存関係管理

```bash
# 本番依存関係の追加
uv add pydantic typer rich pyyaml

# 開発依存関係の追加（dependency-groups使用）
uv add --group dev pytest pytest-cov pytest-mock mypy ruff

# 特定バージョンの指定
uv add "pydantic>=2.11.9,<3.0.0"

# グループ指定でインストール
uv sync --group dev

# 依存関係の削除
uv remove package-name

# 依存関係の更新
uv lock --upgrade

# 環境の同期（CI/CD用）
uv sync --frozen

# スクリプト実行
uv run knowledge-base-organizer --help
```

### ドキュメント生成（Sphinx + MyST）

```bash
# ドキュメント依存関係インストール
uv add --group doc sphinx furo myst-parser

# ドキュメント初期化
uv run sphinx-quickstart docs

# ドキュメント生成
uv run sphinx-build -b html docs docs/_build/html

# 自動リビルド（開発時）
uv run sphinx-autobuild docs docs/_build/html
```

### セキュリティとコード品質チェック

```bash
# セキュリティ脆弱性チェック
uv run bandit -r src/

# ライセンスチェック
uv run licensecheck

# 循環複雑度チェック
uv run lizard src/

# 依存関係の脆弱性チェック
uv run pip-audit

# 安全性チェック
uv run safety check
```

---
inclusion: fileMatch
fileMatchPattern: 'knowledge-base-organizer/*'
---

# Senior Python Engineer Development Guidelines

## エンジニアリング哲学とマインドセット

### 問題解決アプローチ

#### 5 Whys分析による根本原因特定

```python
# 問題: テストが遅い
# Why 1: なぜテストが遅いのか？ → ファイルI/Oが多い
# Why 2: なぜファイルI/Oが多いのか？ → 毎回実ファイルを読み込んでいる
# Why 3: なぜ毎回実ファイルを読み込むのか？ → モックが使われていない
# Why 4: なぜモックが使われていないのか？ → テスト設計が不十分
# Why 5: なぜテスト設計が不十分なのか？ → TDD文化が浸透していない

# 解決策: テスト駆動開発の導入とモック活用
```

#### 仮説思考によるデータ駆動開発

```python
# 1. 仮説設定: "シノニム検出の精度は文字列類似度で向上する"
# 2. 検証設計: A/Bテストでアルゴリズム比較
# 3. 実験実行: 小規模データセットでプロトタイプ
# 4. 結果分析: 精度・再現率・処理時間の測定
# 5. 学習適用: 最適なアルゴリズムの本格導入
```

#### システム思考による全体最適

- **フィードバックループ**: ユーザー→分析→改善→ユーザーの循環
- **レバレッジポイント**: 最小の変更で最大の効果（例：キャッシュ導入）
- **制約理論**: ボトルネック特定（例：ファイルI/O、正規表現処理）
- **創発特性**: 個別機能の組み合わせによる新たな価値創出

### 技術選定の判断基準

#### 成熟度評価フレームワーク

```python
@dataclass
class TechnologyAssessment:
    adoption: float      # 業界採用率 (0.0-1.0)
    maturity: float      # プロダクト成熟度 (0.0-1.0)
    vendor_lock_in: float # ベンダー依存度 (0.0-1.0, 低いほど良い)
    tco: float          # 総所有コスト (学習+運用+保守)
    future_proof: float  # 将来性 (0.0-1.0)

    def overall_score(self) -> float:
        return (self.adoption * 0.2 +
                self.maturity * 0.3 +
                (1 - self.vendor_lock_in) * 0.2 +
                (1 / self.tco) * 0.2 +
                self.future_proof * 0.1)
```

#### アーキテクチャ決定プロセス

1. **問題の本質理解**: 技術的制約 vs ビジネス制約の分離
2. **トレードオフ分析**: パフォーマンス vs 保守性 vs 開発速度
3. **リスク評価**: 技術リスク、運用リスク、学習コストリスク
4. **プロトタイプ検証**: 仮説の実証とフィードバック収集
5. **段階的導入**: Big Bang回避、漸進的改善

## 設計原則とパターン

### SOLID原則の実践

#### 単一責任原則 (SRP)

```python
# ❌ 悪い例: 複数の責任を持つクラス
class MarkdownAnalyzer:
    def analyze_frontmatter(self): pass
    def detect_links(self): pass
    def generate_report(self): pass
    def save_to_file(self): pass

# ✅ 良い例: 責任を分離
class FrontmatterAnalyzer:
    def analyze(self, file: MarkdownFile) -> FrontmatterResult: pass

class LinkDetector:
    def detect_opportunities(self, file: MarkdownFile) -> List[LinkOpportunity]: pass

class ReportGenerator:
    def generate(self, results: AnalysisResults) -> Report: pass

class FileRepository:
    def save(self, content: str, path: Path) -> None: pass
```

#### 開放閉鎖原則 (OCP)

```python
# 拡張に開放、修正に閉鎖
from abc import ABC, abstractmethod

class SynonymDetector(ABC):
    @abstractmethod
    def detect(self, text: str, candidates: List[str]) -> List[SynonymMatch]:
        pass

class AcronymDetector(SynonymDetector):
    def detect(self, text: str, candidates: List[str]) -> List[SynonymMatch]:
        # SSO → Single Sign-On の検出ロジック
        pass

class SemanticSimilarityDetector(SynonymDetector):
    def detect(self, text: str, candidates: List[str]) -> List[SynonymMatch]:
        # 意味的類似性による検出ロジック
        pass

class CompositeSynonymDetector(SynonymDetector):
    def __init__(self, detectors: List[SynonymDetector]):
        self.detectors = detectors

    def detect(self, text: str, candidates: List[str]) -> List[SynonymMatch]:
        results = []
        for detector in self.detectors:
            results.extend(detector.detect(text, candidates))
        return self._merge_and_rank(results)
```

#### 依存性逆転原則 (DIP)

```python
# 抽象に依存し、具象に依存しない
class LinkAnalysisService:
    def __init__(
        self,
        file_repository: MarkdownFileRepository,  # インターフェース
        synonym_detector: SynonymDetector,        # インターフェース
        report_generator: ReportGenerator         # インターフェース
    ):
        self.file_repository = file_repository
        self.synonym_detector = synonym_detector
        self.report_generator = report_generator
```

### デザインパターンの活用

#### Strategy Pattern (戦略パターン)

```python
class AnalysisStrategy(Protocol):
    def analyze(self, files: List[MarkdownFile]) -> AnalysisResult:
        pass

class FastAnalysisStrategy:
    """高速だが精度は中程度"""
    def analyze(self, files: List[MarkdownFile]) -> AnalysisResult:
        # 基本的なパターンマッチングのみ
        pass

class DeepAnalysisStrategy:
    """時間はかかるが高精度"""
    def analyze(self, files: List[MarkdownFile]) -> AnalysisResult:
        # NLP、機械学習を活用した高度な分析
        pass

class AnalysisContext:
    def __init__(self, strategy: AnalysisStrategy):
        self.strategy = strategy

    def set_strategy(self, strategy: AnalysisStrategy):
        self.strategy = strategy

    def execute_analysis(self, files: List[MarkdownFile]) -> AnalysisResult:
        return self.strategy.analyze(files)
```

#### Observer Pattern (観察者パターン)

```python
class AnalysisProgressObserver(Protocol):
    def on_progress_update(self, progress: ProgressInfo) -> None:
        pass

class ConsoleProgressObserver:
    def on_progress_update(self, progress: ProgressInfo) -> None:
        print(f"Progress: {progress.percentage}% - {progress.current_task}")

class FileProgressObserver:
    def on_progress_update(self, progress: ProgressInfo) -> None:
        with open("progress.log", "a") as f:
            f.write(f"{progress.timestamp}: {progress.percentage}%\n")

class AnalysisEngine:
    def __init__(self):
        self.observers: List[AnalysisProgressObserver] = []

    def add_observer(self, observer: AnalysisProgressObserver):
        self.observers.append(observer)

    def notify_progress(self, progress: ProgressInfo):
        for observer in self.observers:
            observer.on_progress_update(progress)
```

#### Factory Pattern (ファクトリパターン)

```python
class AnalyzerFactory:
    @staticmethod
    def create_analyzer(analyzer_type: str, config: Config) -> BaseAnalyzer:
        analyzers = {
            "frontmatter": lambda: FrontmatterAnalyzer(config),
            "links": lambda: LinkAnalyzer(config),
            "synonyms": lambda: SynonymAnalyzer(config),
            "structure": lambda: StructureAnalyzer(config),
        }

        if analyzer_type not in analyzers:
            raise ValueError(f"Unknown analyzer type: {analyzer_type}")

        return analyzers[analyzer_type]()
```

## 品質保証とテスト戦略

### テストピラミッドの実践

#### Unit Tests (70%) - 高速で安定

```python
import pytest
from hypothesis import given, strategies as st
from unittest.mock import Mock, patch

class TestSynonymDetector:
    @pytest.fixture
    def detector(self):
        return AcronymDetector()

    def test_detect_simple_acronym(self, detector):
        text = "We use SSO for authentication"
        candidates = ["Single Sign-On", "Server-Side Operations"]

        results = detector.detect(text, candidates)

        assert len(results) == 1
        assert results[0].source_text == "SSO"
        assert results[0].target_text == "Single Sign-On"
        assert results[0].confidence > 0.8

    @given(st.text(min_size=1, max_size=100))
    def test_detect_handles_arbitrary_text(self, detector, text):
        # Property-based testing
        candidates = ["Test Candidate"]
        results = detector.detect(text, candidates)
        assert isinstance(results, list)
        assert all(isinstance(r, SynonymMatch) for r in results)

    @patch('knowledge_base_organizer.nlp.similarity_score')
    def test_detect_uses_similarity_threshold(self, mock_similarity, detector):
        mock_similarity.return_value = 0.3  # 閾値以下

        results = detector.detect("test", ["candidate"])

        assert len(results) == 0  # 閾値以下なので検出されない
```

#### Integration Tests (20%) - コンポーネント連携

```python
class TestAnalysisWorkflow:
    @pytest.fixture
    def temp_vault(self, tmp_path):
        # テスト用のMarkdownファイル群を作成
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()

        (vault_path / "file1.md").write_text("""---
title: Single Sign-On
aliases: [SSO, Single Sign-On]
---
# Single Sign-On
Authentication mechanism...""")

        (vault_path / "file2.md").write_text("""---
title: Authentication Guide
---
# Authentication
We use SSO for user authentication.""")

        return vault_path

    def test_end_to_end_synonym_detection(self, temp_vault):
        config = Config(knowledge_base_path=str(temp_vault))
        analyzer = SynonymAnalyzer(config)

        results = analyzer.analyze_directory(str(temp_vault))

        # SSO → Single Sign-On のリンクが検出されることを確認
        sso_opportunities = [r for r in results if r.keyword_found == "SSO"]
        assert len(sso_opportunities) == 1
        assert sso_opportunities[0].potential_targets[0].title == "Single Sign-On"
```

#### E2E Tests (10%) - ユーザー視点

```python
class TestCLIWorkflow:
    def test_complete_analysis_workflow(self, temp_vault, tmp_path):
        output_dir = tmp_path / "output"

        # CLIコマンドの実行
        result = subprocess.run([
            "uv", "run", "python", "-m", "knowledge_base_organizer.cli",
            "analyze", str(temp_vault), "--output-dir", str(output_dir)
        ], capture_output=True, text=True)

        assert result.returncode == 0
        assert "Analysis complete" in result.stdout

        # 出力ファイルの検証
        assert (output_dir / "frontmatter_analysis.json").exists()
        assert (output_dir / "link_opportunities.json").exists()

        # 結果の内容検証
        with open(output_dir / "link_opportunities.json") as f:
            opportunities = json.load(f)
            assert len(opportunities) > 0
```

### テスト駆動開発 (TDD) の実践

#### Red-Green-Refactor サイクル

```python
# 1. Red: 失敗するテストを書く
def test_multilingual_synonym_detection():
    detector = MultilingualSynonymDetector()
    text = "We use Landing Zone for AWS setup"
    candidates = ["ランディングゾーン(Landing Zone)"]

    results = detector.detect(text, candidates)

    assert len(results) == 1
    assert results[0].source_text == "Landing Zone"
    assert results[0].target_text == "ランディングゾーン(Landing Zone)"
    assert results[0].detection_type == "multilingual"

# 2. Green: テストを通す最小限の実装
class MultilingualSynonymDetector:
    def detect(self, text: str, candidates: List[str]) -> List[SynonymMatch]:
        # 最小限の実装でテストを通す
        if "Landing Zone" in text and "ランディングゾーン(Landing Zone)" in candidates:
            return [SynonymMatch(
                source_text="Landing Zone",
                target_text="ランディングゾーン(Landing Zone)",
                detection_type="multilingual",
                confidence=0.9
            )]
        return []

# 3. Refactor: 実装を改善
class MultilingualSynonymDetector:
    def __init__(self):
        self.multilingual_patterns = self._load_patterns()

    def detect(self, text: str, candidates: List[str]) -> List[SynonymMatch]:
        results = []
        for pattern in self.multilingual_patterns:
            if pattern.matches(text, candidates):
                results.append(pattern.create_match())
        return results
```

## パフォーマンスとスケーラビリティ

### メモリ効率的な実装

#### ストリーミング処理

```python
def analyze_files_streaming(base_path: Path) -> Iterator[AnalysisResult]:
    """大量ファイルをメモリ効率的に処理"""
    for file_path in base_path.rglob("*.md"):
        try:
            # ファイルを1つずつ処理してメモリ使用量を抑制
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                yield analyze_single_file(content, file_path)
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            continue

# 使用例
results = []
for result in analyze_files_streaming(vault_path):
    results.append(result)
    if len(results) >= BATCH_SIZE:
        process_batch(results)
        results.clear()  # メモリ解放
```

#### キャッシュ戦略

```python
from functools import lru_cache
from typing import Dict, Any
import hashlib

class AnalysisCache:
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, Any] = {}
        self.max_size = max_size

    def get_cache_key(self, file_path: Path, content_hash: str) -> str:
        return f"{file_path}:{content_hash}"

    def get_content_hash(self, content: str) -> str:
        return hashlib.md5(content.encode()).hexdigest()

    @lru_cache(maxsize=1000)
    def analyze_with_cache(self, content: str, file_path: str) -> AnalysisResult:
        # 内容が変更されていない場合はキャッシュから返す
        return self._perform_analysis(content, file_path)
```

#### 並列処理

```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from multiprocessing import cpu_count

class ParallelAnalyzer:
    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or min(cpu_count(), 8)

    def analyze_files_parallel(self, files: List[Path]) -> List[AnalysisResult]:
        # I/O集約的なタスクはThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.analyze_file, file) for file in files]
            results = [future.result() for future in futures]
        return results

    def process_heavy_computation(self, data_chunks: List[Any]) -> List[Any]:
        # CPU集約的なタスクはProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.heavy_process, chunk) for chunk in data_chunks]
            results = [future.result() for future in futures]
        return results
```

## エラーハンドリングと復旧戦略

### 段階的フォールバック

```python
class RobustAnalyzer:
    def __init__(self):
        self.primary_analyzer = AdvancedSynonymDetector()
        self.fallback_analyzer = BasicSynonymDetector()
        self.emergency_analyzer = RegexSynonymDetector()

    def analyze_with_fallback(self, text: str, candidates: List[str]) -> List[SynonymMatch]:
        try:
            # 第1段階: 高度な分析を試行
            return self.primary_analyzer.detect(text, candidates)
        except AdvancedAnalysisError as e:
            logger.warning(f"Advanced analysis failed: {e}, falling back to basic")
            try:
                # 第2段階: 基本的な分析にフォールバック
                return self.fallback_analyzer.detect(text, candidates)
            except BasicAnalysisError as e:
                logger.error(f"Basic analysis failed: {e}, using emergency mode")
                # 第3段階: 緊急時の最小限分析
                return self.emergency_analyzer.detect(text, candidates)
```

### 自動復旧メカニズム

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class ResilientFileProcessor:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def process_file_with_retry(self, file_path: Path) -> AnalysisResult:
        try:
            return self._process_file(file_path)
        except FileNotFoundError:
            # ファイルが見つからない場合はリトライしない
            raise
        except PermissionError:
            # 権限エラーの場合はリトライしない
            raise
        except Exception as e:
            # その他のエラーはリトライ対象
            logger.warning(f"Processing failed for {file_path}: {e}, retrying...")
            raise
```

## 継続的改善とメトリクス

### パフォーマンス監視

```python
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict

@dataclass
class PerformanceMetrics:
    execution_time: float
    memory_usage: int
    files_processed: int
    errors_count: int

class PerformanceMonitor:
    def __init__(self):
        self.metrics: Dict[str, PerformanceMetrics] = {}

    @contextmanager
    def measure_performance(self, operation_name: str):
        start_time = time.time()
        start_memory = self._get_memory_usage()

        try:
            yield
        finally:
            end_time = time.time()
            end_memory = self._get_memory_usage()

            self.metrics[operation_name] = PerformanceMetrics(
                execution_time=end_time - start_time,
                memory_usage=end_memory - start_memory,
                files_processed=self._get_processed_count(),
                errors_count=self._get_error_count()
            )

    def get_performance_report(self) -> str:
        report = "Performance Report:\n"
        for operation, metrics in self.metrics.items():
            report += f"{operation}: {metrics.execution_time:.2f}s, "
            report += f"{metrics.memory_usage}MB, "
            report += f"{metrics.files_processed} files\n"
        return report
```

### 品質メトリクス

```python
class QualityMetrics:
    def __init__(self):
        self.precision_scores: List[float] = []
        self.recall_scores: List[float] = []
        self.f1_scores: List[float] = []

    def calculate_synonym_detection_quality(
        self,
        detected: List[SynonymMatch],
        ground_truth: List[SynonymMatch]
    ) -> Dict[str, float]:
        true_positives = len(set(detected) & set(ground_truth))
        false_positives = len(detected) - true_positives
        false_negatives = len(ground_truth) - true_positives

        precision = true_positives / (true_positives + false_positives) if detected else 0
        recall = true_positives / (true_positives + false_negatives) if ground_truth else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        return {
            "precision": precision,
            "recall": recall,
            "f1_score": f1
        }
```

この高度なsteeringガイドラインに基づいて、次の段階的実装を提案します。どの部分から始めたいですか？

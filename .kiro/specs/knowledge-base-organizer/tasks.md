# Implementation Plan - Use Case Driven Approach

## Phase 1: MVP - Basic Vault Analysis (Vertical Slice)

- [x] 1. Set up minimal project structure for vault analysis
    - Create basic project structure with src/knowledge_base_organizer
    - Set up pyproject.toml with essential dependencies (pydantic, typer, rich)
    - Create minimal CLI entry point for vault analysis
    - Set up basic configuration loading
    - _Requirements: 6.1, 6.2_

- [ ] 2. Implement basic vault scanning and file analysis
    - [x] 2.1 Create MarkdownFile entity with frontmatter parsing
        - Implement basic MarkdownFile class with YAML frontmatter parsing
        - Add file content loading and basic validation
        - Handle parsing errors gracefully
        - _Requirements: 1.1, 1.2_

    - [x] 2.2 Create FileRepository for vault scanning
        - Implement recursive markdown file discovery
        - Add basic include/exclude pattern filtering
        - Create file loading with error handling
        - _Requirements: 1.1, 6.1_

    - [x] 2.3 Implement basic CLI command for vault analysis
        - Create `analyze` command that scans vault and reports basic statistics
        - Show file count, frontmatter field distribution, basic link counts
        - Output results in JSON format for automation
        - _Requirements: 5.1, 5.4_

    - [x] 2.4 Test with real vault data
        - Test analysis command with test-myvault sample data
        - Verify frontmatter parsing works with various templates
        - Ensure error handling works with malformed files
        - _Requirements: 1.1_

## Phase 2: Template-Based Frontmatter Validation (Complete Feature)

- [ ] 3. Implement template-based frontmatter validation with type conversion
    - [x] 3.1 Create template schema extraction system
        - Implement TemplateSchemaRepository to scan template directories
        - Parse frontmatter from template files (new-fleeing-note.md, booksearchtemplate.md)
        - Convert template variables to validation rules
        - _Requirements: 1.1, 6.2_

    - [x] 3.2 Implement frontmatter validation logic
        - Create FrontmatterSchema with validation methods
        - Add template type detection (directory-based and content-based)
        - Generate fix suggestions for non-conforming frontmatter
        - _Requirements: 1.3, 1.4, 1.5_

    - [x] 3.2.1 Implement template-based validation with --template option
        - Add single template file schema extraction
        - Implement template-based validation that only modifies files when template is specified
        - Add safety checks to preserve existing valid frontmatter
        - _Requirements: 1.3, 1.4, 1.5, 1.6_

    - [x] 3.2.2 Implement YAML type conversion system
        - Create YAMLTypeConverter for handling automatic YAML type conversion
        - Add intelligent conversion of integers to strings for ID fields
        - Add datetime to ISO string conversion for date fields
        - Add logging of all type conversions performed
        - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.8_

    - [x] 3.3 Create validate-frontmatter CLI command
        - Implement complete CLI command with dry-run and execute modes
        - Add interactive mode for reviewing and applying fixes
        - Support CSV/JSON output for automation
        - _Requirements: 1.5, 1.6, 5.1, 5.4_

    - [x] 3.3.1 Add --template option to validate-frontmatter CLI command
        - Add --template option to specify template file path
        - Implement template-based validation mode vs legacy auto-detection mode
        - Add comprehensive error handling for invalid template paths
        - Add verbose output showing type conversions and fixes applied
        - _Requirements: 1.3, 1.4, 1.5, 1.6, 12.8_

    - [x] 3.4 Test frontmatter validation end-to-end
        - Test with various template types in test vault
        - Verify fix suggestions are accurate and safe
        - Test backup creation and rollback functionality
        - _Requirements: 1.1, 1.3, 1.6_

    - [ ] 3.4.1 Test template-based validation with real vault data
        - Test --template option with ~/work/myvault/900_TemplaterNotes/new-fleeing-note.md
        - Verify that valid frontmatter (like AWS Summit note) is NOT modified
        -
        - Test type conversion with integer IDs and date objects
        - Verify that only missing fields are added, existing valid values preserved
        - Test dry-run vs execute mode behavior
        - _Requirements: 1.3, 1.4, 1.5, 1.6, 12.1, 12.2, 12.3_

## Phase 3: Automatic Organization and Improvement (Priority Feature)

- [ ] 4. Implement automatic knowledge base organization
    - [x] 4.1 Create content analysis and improvement detection
        - Implement ContentAnalysisService for missing field detection
        - Add smart value generation (tags from content, descriptions from text)
        - Create consistency checking (filename-title matching, tag normalization)
        - _Requirements: 8.1, 8.2, 8.3_

    - [x] 4.2 Implement automatic frontmatter enhancement
        - Create FrontmatterEnhancementService for field completion
        - Add intelligent tag suggestion based on content analysis
        - Implement automatic date and metadata population
        - _Requirements: 8.1, 8.2, 8.4_

    - [x] 4.3 Create organize CLI command
        - Implement CLI command for automatic organization
        - Add dry-run mode with detailed preview of changes
        - Support selective application of improvements
        - _Requirements: 8.6, 8.7, 5.1, 5.2_

    - [x] 4.4 Test automatic organization end-to-end
        - Test with test-myvault to apply real improvements
        - Verify backup and rollback functionality works
        - Test improvement report generation and metrics
        - _Requirements: 8.6, 8.7_

## Phase 4: Content Quality Enhancement

- [ ] 5. Implement content quality detection and improvement
    - [ ] 5.1 Create orphaned note detection and connection suggestions
        - Implement OrphanedNoteDetectionService
        - Add content similarity analysis for connection suggestions
        - Create bidirectional link recommendation system
        - _Requirements: 9.1, 9.4_

    - [ ] 5.2 Implement content completeness analysis
        - Create ContentCompletenessService for quality assessment
        - Add incomplete note detection (length, structure, placeholders)
        - Implement duplicate content detection and merge suggestions
        - _Requirements: 9.2, 9.3_

    - [ ] 5.3 Create improve-quality CLI command
        - Implement CLI command for quality improvements
        - Add prioritized improvement suggestions with confidence scores
        - Support preview mode for quality changes
        - _Requirements: 9.5, 9.6, 9.7_

    - [ ] 5.4 Test content quality improvements
        - Test orphaned note detection with real vault data
        - Verify duplicate detection accuracy
        - Test improvement prioritization and application
        - _Requirements: 9.1, 9.2, 9.3_

## Phase 5: Basic Link Detection (Complete Feature)

- [ ] 6. Implement WikiLink and dead link detection
    - [x] 6.1 Create link parsing and analysis
        - Implement WikiLink and RegularLink value objects
        - Create LinkAnalysisService for link extraction
        - Add exclusion zone detection (frontmatter, existing links, Link Reference Definitions)
        - _Requirements: 2.1, 2.2, 2.3, 7.1, 7.2_

    - [x] 6.2 Implement dead link detection
        - Create file registry for link target validation
        - Detect broken WikiLinks and empty regular links
        - Generate comprehensive dead link reports
        - _Requirements: 3.1, 3.2, 3.3_

    - [x] 6.3 Create detect-dead-links CLI command
        - Implement CLI command with structured output
        - Add fix suggestions for common dead link patterns
        - Support filtering and sorting of results
        - _Requirements: 3.4, 3.6, 5.1, 5.4_

    - [x] 6.4 Test link detection with real data
        - Test with test-myvault to find actual dead links
        - Verify exclusion zones work correctly
        - Test performance with large numbers of files
        - _Requirements: 3.1, 3.2_

## Phase 6: Basic Auto-Linking (Complete Feature)

- [ ] 7. Implement basic auto-link generation
    - [x] 7.1 Create content processing for link candidates
        - Implement ContentProcessingService for safe text replacement
        - Add link candidate detection (exact title/alias matches)
        - Create position tracking and conflict resolution
        - _Requirements: 2.1, 2.4, 2.5_

    - [x] 7.2 Implement basic auto-link generation
        - Create AutoLinkGenerationUseCase for orchestrating link creation
        - Add bidirectional file updates (source + target alias updates)
        - Implement dry-run mode with preview
        - _Requirements: 2.8, 2.9_

    - [x] 7.3 Create auto-link CLI command
        - Implement CLI command with safety controls (max links per file)
        - Add progress reporting for large vaults
        - Support configurable exclusion patterns
        - _Requirements: 5.1, 5.2, 5.3_

    - [x] 7.4 Test basic auto-linking
        - Test with test-myvault data to create actual links
        - Verify no existing content is corrupted
        - Test rollback functionality
        - _Requirements: 2.1, 2.8_

## Phase 7: Structural Optimization

- [ ] 8. Implement vault structure optimization
    - [ ] 8.1 Create structural analysis and optimization
        - Implement StructuralAnalysisService for directory evaluation
        - Add file relocation suggestions based on content and relationships
        - Create tag hierarchy analysis and consolidation recommendations
        - _Requirements: 10.1, 10.2, 10.3_

    - [ ] 8.2 Implement safe file reorganization
        - Create FileReorganizationService with link preservation
        - Add impact analysis and change preview functionality
        - Implement automatic link and reference updates
        - _Requirements: 10.4, 10.5, 10.6_

    - [ ] 8.3 Create optimize-structure CLI command
        - Implement CLI command for structural optimization
        - Add comprehensive preview and validation before changes
        - Support selective application of structural improvements
        - _Requirements: 10.5, 10.7, 5.1_

    - [ ] 8.4 Test structural optimization
        - Test file moves with link preservation
        - Verify tag hierarchy optimization
        - Test rollback and validation functionality
        - _Requirements: 10.4, 10.6, 10.7_

## Phase 8: Continuous Maintenance System

- [ ] 9. Implement continuous quality monitoring
    - [ ] 9.1 Create quality metrics and monitoring
        - Implement QualityMetricsService for comprehensive tracking
        - Add trend analysis and quality dashboards
        - Create automated quality degradation detection
        - _Requirements: 11.2, 11.3, 11.4_

    - [ ] 9.2 Implement maintenance scheduling
        - Create MaintenanceSchedulerService for regular quality checks
        - Add configurable maintenance routines and alerts
        - Implement audit trail and improvement history tracking
        - _Requirements: 11.1, 11.6, 11.7_

    - [ ] 9.3 Create maintenance CLI command
        - Implement CLI command for scheduled maintenance
        - Add quality reporting and trend visualization
        - Support automated and manual maintenance modes
        - _Requirements: 11.1, 11.5, 5.1_

    - [ ] 9.4 Test continuous maintenance system
        - Test scheduled quality checks and alerts
        - Verify metrics tracking and trend analysis
        - Test maintenance history and audit functionality
        - _Requirements: 11.2, 11.3, 11.6_

## Phase 9: Advanced Japanese Synonym Detection

- [ ] 10. Implement Japanese language processing
    - [ ] 10.1 Create katakana variation detection
        - Implement JapaneseSynonymService with variation patterns
        - Add long vowel and consonant variation handling
        - Create confidence scoring for matches
        - _Requirements: 2.6, 2.7_

    - [ ] 10.2 Integrate synonym detection with auto-linking
        - Extend AutoLinkGenerationUseCase with synonym support
        - Add configurable confidence thresholds
        - Implement bidirectional alias management
        - _Requirements: 2.6, 2.7, 2.8_

    - [ ] 10.3 Test advanced synonym detection
        - Test katakana variations with Japanese content
        - Verify bidirectional alias updates work correctly
        - Test performance impact of synonym detection
        - _Requirements: 2.6, 2.7_

## Phase 10: Content Aggregation (Complete Feature)

- [ ] 11. Implement content aggregation
    - [ ] 11.1 Create tag-based filtering and aggregation
        - Implement ContentAggregationUseCase
        - Add tag-based note selection and filtering
        - Create content merging with source attribution
        - _Requirements: 4.1, 4.2, 4.3_

    - [ ] 11.2 Create aggregate CLI command
        - Implement CLI command for content aggregation
        - Add deduplication and formatting options
        - Support multiple output formats
        - _Requirements: 4.4, 4.5, 5.1_

    - [ ] 11.3 Test content aggregation
        - Test with various tag combinations
        - Verify merged content maintains readability
        - Test with large content volumes
        - _Requirements: 4.1, 4.2_

## Phase 11: Performance Optimization and Polish

- [ ] 12. Optimize performance and add advanced features
    - [ ] 12.1 Implement caching and indexing
        - Add file registry caching for repeated operations
        - Create synonym pattern indexing
        - Implement incremental processing
        - _Requirements: 2.9, 6.4_

    - [ ] 12.2 Add comprehensive error handling
        - Implement graceful error recovery
        - Add detailed error reporting with suggestions
        - Create automatic retry mechanisms
        - _Requirements: 5.5, 5.6_

    - [ ] 12.3 Create comprehensive test suite
        - Add integration tests for all use cases
        - Create performance benchmarks
        - Add edge case and error condition tests
        - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1_

    - [ ] 12.4 Documentation and examples
        - Create user guide with examples
        - Add configuration templates
        - Create troubleshooting guide
        - _Requirements: 5.6, 6.6_

## Phase 12: 日本語処理大幅強化 (最優先 - 即座に着手可能)

**理由**: 既存の基本的な日本語処理を拡張するだけで大幅な機能向上が可能。重い依存関係不要。

- [ ] 12. 高度日本語言語処理の実装（軽量・即効性重視）
    - [ ] 12.1 カタカナ表記ゆれ検出エンジン（最優先）
        - 既存のTagPatternManagerにカタカナバリエーション機能を追加
        - 長音符パターン辞書（インターフェース ↔ インターフェイス）
        - 子音バリエーション辞書（ヴ ↔ ブ、ティ ↔ テ）
        - 既存のfind_tag_suggestionsメソッドに統合
        - **依存関係**: なし（純粋なPython実装）
        - _Requirements: 19.1, 19.6_
        - _既存コード拡張: TagPatternManager.py 約50行追加_

    - [ ] 12.2 英日対訳システムの実装（高優先）
        - 技術用語辞書をYAMLファイルで管理（API ↔ エーピーアイ）
        - 略語展開辞書（DB → データベース）
        - 既存のFrontmatterEnhancementServiceに統合
        - **依存関係**: なし（辞書ファイル + 既存YAML処理）
        - _Requirements: 19.2, 19.4, 19.5_
        - _既存コード拡張: FrontmatterEnhancementService.py 約30行追加_

    - [ ] 12.3 日本語処理のauto-link統合（中優先）
        - 既存のLinkAnalysisService.find_link_candidatesに日本語バリエーション追加
        - カタカナ・英日対訳を使った候補拡張
        - 双方向エイリアス提案機能
        - **依存関係**: なし（上記12.1, 12.2の機能活用）
        - _Requirements: 19.3, 19.7_
        - _既存コード拡張: LinkAnalysisService.py 約40行追加_

## Phase 13: インテリジェントfrontmatter強化 (中優先)

- [ ] 13. 既存frontmatter機能のAI強化
    - [ ] 13.1 セマンティックタグ提案システム
        - 既存のContentAnalysisServiceにセマンティック分析を統合
        - コンテンツからキーコンセプト抽出
        - 既存タグパターンとの類似度ベース提案
        - TagPatternManagerの階層一貫性チェック強化
        - _Requirements: 17.1, 17.4, 18.5_
        - _既存コード拡張: ContentAnalysisService + TagPatternManager強化_

    - [ ] 13.2 自動説明文生成機能
        - 第一段落からの要約生成（ルールベース）
        - キーセンテンス抽出による説明文作成
        - 品質スコアリングシステム
        - 既存のFrontmatterEnhancementServiceに統合
        - _Requirements: 17.2_
        - _既存コード拡張: FrontmatterEnhancementService強化_

    - [ ] 13.3 enhance-frontmatterコマンドの高度化
        - organizeコマンドにセマンティック強化オプションを追加
        - 信頼度スコアと選択的適用機能
        - ディレクトリ固有の強化ルール
        - _Requirements: 17.5, 17.6, 17.7_
        - _既存コード拡張: organize_command.py強化_

## Phase 14: 自動メンテナンスシステム強化 (中優先)

**理由**: 既存のorganize機能を拡張するだけで大幅な自動化が可能。

- [ ] 14. 既存organize機能の大幅拡張
    - [ ] 14.1 重複ノート検出・統合システム
        - 既存のContentAnalysisServiceに類似度計算機能を追加
        - ファイル名・タイトル・内容の類似度ベース重複検出
        - 統合提案・プレビュー機能
        - **依存関係**: なし（既存の文字列処理拡張）
        - _Requirements: 20.2_
        - _既存コード拡張: ContentAnalysisService.py 約60行追加_

    - [ ] 14.2 孤立ノート自動接続システム
        - 既存のLinkAnalysisServiceに孤立ノート検出機能追加
        - タグ・キーワードベースの関連ノート提案
        - 自動WikiLink作成提案
        - **依存関係**: なし（既存機能の組み合わせ）
        - _Requirements: 20.4_
        - _既存コード拡張: LinkAnalysisService.py 約40行追加_

    - [ ] 14.3 maintainコマンドの実装
        - 既存のorganizeコマンドを拡張してmaintain機能追加
        - 包括的メンテナンスレポート
        - スケジュール実行対応
        - **依存関係**: なし（既存CLI拡張）
        - _Requirements: 20.7_
        - _既存コード拡張: organize_command.py 約50行追加_

## Phase 15: ollama/LLM活用セマンティック分析 (長期・軽量)

**理由**: ollama + local LLMを活用することで、重い依存関係なしでセマンティック分析が可能。

- [ ] 15. ollama統合セマンティック分析サービス
    - [ ] 15.1 ollama連携基盤の構築
        - OllamaServiceクラス新規作成（HTTP API経由）
        - 軽量なembedding生成（ollama/nomic-embed-text使用）
        - シンプルなキャッシュシステム（JSON/pickle）
        - **依存関係**: requests（既存）のみ
        - _Requirements: 13.1, 13.2_
        - _既存コード拡張: 新規サービス約100行_

    - [ ] 15.2 LLMベースコンテンツ分析
        - ollama/llama3.2:3bを使った関連性分析
        - プロンプトベースの類似ノート発見
        - 自然言語での関係性説明生成
        - **依存関係**: ollama（ローカルインストール）
        - _Requirements: 18.1, 18.2, 21.1_
        - _既存コード拡張: 新規分析サービス約80行_

    - [ ] 15.3 セマンティック機能のCLI統合
        - auto-linkコマンドに--semantic-modeオプション追加
        - discover-relationshipsコマンド実装
        - LLM分析結果の可視化
        - **依存関係**: なし（上記サービス活用）
        - _Requirements: 13.3, 18.7, 21.7_
        - _既存コード拡張: CLI約60行追加_

## Phase 16: 自動メンテナンスシステム (長期)

- [ ] 17. 継続的メンテナンスシステムの実装
    - [ ] 17.1 自動メンテナンスエンジン
        - MaintenanceEngineクラス新規作成
        - 壊れた参照の自動検出・修正
        - 重複ノート検出・統合提案
        - 既存のorganizeコマンドとの統合
        - _Requirements: 20.1, 20.2_
        - _既存コード拡張: organize_command.py大幅拡張_

    - [ ] 17.2 構造最適化機能
        - タグ統合・階層メンテナンス
        - 孤立ノート検出・接続提案
        - ファイル組織改善推奨
        - 既存のContentAnalysisServiceとの統合
        - _Requirements: 20.3, 20.4, 20.6_
        - _既存コード拡張: ContentAnalysisService拡張_

    - [ ] 17.3 メンテナンスCLIコマンド
        - maintainコマンド実装
        - 包括的メンテナンスレポート
        - スケジュール実行対応（設定可能間隔）
        - _Requirements: 20.7, 20.5_
        - _既存コード拡張: 新規CLIコマンド_

## Phase 17: 高度コンテキスト理解 (長期・高度)

- [ ] 18. コンテキスト理解システムの実装
    - [ ] 18.1 高度コンテキスト分析システム
        - SemanticAnalysisServiceの高度コンテキスト評価機能
        - ドメイン固有コンテキスト認識（プログラミング vs 料理）
        - 複数段落コンテキスト分析（精度向上）
        - _Requirements: 21.1, 21.5_
        - _既存コード拡張: SemanticAnalysisService大幅拡張_

    - [ ] 18.2 インテリジェント曖昧性解消
        - コンテキスト関連性による高度候補ランキング
        - 曖昧ケース用の曖昧性解消UI
        - リンク作成決定の詳細推論レポート
        - _Requirements: 21.2, 21.3, 21.7_
        - _既存コード拡張: AutoLinkGenerationUseCase高度化_

    - [ ] 18.3 全機能へのコンテキスト理解統合
        - 全auto-link機能のコンテキスト理解対応
        - コンテキスト認識型信頼度閾値管理
        - 包括的コンテキスト認識リンク検証
        - _Requirements: 21.4, 21.6_
        - _既存コード拡張: 全サービスクラス統合_

## Phase 18: 高度機能統合・最適化 (最終段階)

- [ ] 19. セカンドブレイン自動化オーケストレーター
    - [ ] 19.1 統合自動化システム
        - SecondBrainAutomationOrchestratorクラス実装
        - 全機能の統合実行ワークフロー
        - 自動化レベル設定（CONSERVATIVE/AGGRESSIVE）
        - 包括的自動化レポート生成
        - _Requirements: 17.7, 18.7, 20.7_
        - _既存コード拡張: 新規オーケストレーター + 全サービス統合_

    - [ ] 19.2 パフォーマンス最適化
        - 埋め込みキャッシュ最適化
        - バッチ処理・並列処理実装
        - メモリ効率化・ストリーミング処理
        - 大規模vault対応
        - _既存コード拡張: 全サービスのパフォーマンス改善_

    - [ ] 19.3 統合CLIコマンド
        - full-automationコマンド実装
        - 設定可能自動化レベル
        - 包括的品質メトリクス
        - スケジュール実行対応
        - _既存コード拡張: 新規統合CLIコマンド_

## Benefits of This Approach

### ✅ User Value First - Knowledge Base Organization Focus

- **Phase 1**: すぐに使える分析機能 ✅
- **Phase 2**: **完全なテンプレートベースfrontmatter検証機能** (最優先) - `--template`オプション、型変換、安全性確保
- **Phase 3**: **自動整理・改善機能** - frontmatter自動補完、一貫性修正
- **Phase 4**: **コンテンツ品質向上** - 孤立ノート検出、重複検出、品質改善
- **Phase 5**: デッドリンク検出機能
- **Phase 6**: 基本的な自動リンク生成機能

### ✅ Critical Issue Resolution

- **Phase 2.1**: `--template`オプションによる明示的なテンプレート指定
- **Phase 2.2**: YAML型変換システムによる自動型変換の適切な処理
- **Phase 2.4.1**: 実際のvaultデータでの安全性テスト（AWS Summitノートが破壊されないことを確認）

### ✅ Early Feedback

- 各フェーズで実際のvaultデータでテスト
- 問題の早期発見と修正
- ユーザーからのフィードバック収集

### ✅ Risk Mitigation

- 小さな単位での統合テスト
- 段階的な機能追加
- 各フェーズでの品質確保

### ✅ Agile Development

- 各フェーズが独立して価値を提供
- 優先度に応じた開発順序調整可能
- 継続的なデリバリー

### ✅ Technical Benefits

- 実際のデータでの早期検証
- アーキテクチャの段階的進化
- パフォーマンス問題の早期発見

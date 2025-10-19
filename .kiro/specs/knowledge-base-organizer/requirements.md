# Requirements Document

## Introduction

This feature implements a knowledge base organizer specifically designed for Obsidian vaults and markdown-based note systems. The system focuses on note quality improvement through frontmatter validation, automatic link generation, and dead link detection. It provides CLI-based operations with structured output formats (CSV, JSON) for automation and integration with other tools.

The application prioritizes frontmatter standardization, intelligent WikiLink generation from plain text, and comprehensive link validation to maintain a high-quality knowledge base.

## Requirements

### 🎯 実装優先度について

**✅ 完全実装済み (Phase 1-11)**

- Requirements 1-12: 基本機能群（frontmatter検証、auto-link、dead link検出等）

**🚀 最優先実装 (Phase 12-13 - 健全性とノイズ除去)**

- Requirements 19: 日本語処理強化（既存コード拡張、軽量実装）
- Requirements 20: 自動メンテナンスシステム（重複除去・孤立ノート接続）

**🔶 中優先実装 (Phase 14-15 - 基盤強化)**

- Requirements 17: インテリジェントfrontmatter強化（既存サービス拡張）
- Requirements 13-16: セマンティック分析基盤（ollama + local LLM使用）

**⏳ 長期実装 (Phase 16-18 - 創発と高度AI活用)**

- Requirements 22: MOC構築支援（LYT思想の実現）
- Requirements 23: コンセプトベース自動タグ付け（AI合成・推論）
- Requirements 24: 論理的関係性明示（AI推論活用）
- Requirements 18: 関係性発見システム（LLM活用）
- Requirements 21: 高度コンテキスト理解（LLM活用）

### Requirement 1

**User Story:** As an Obsidian user, I want to validate and fix frontmatter in my notes according to template-based schemas, so that my knowledge base maintains consistent metadata structure without corrupting existing valid frontmatter.

#### Acceptance Criteria

1. WHEN I provide a vault directory path THEN the system SHALL scan all markdown files recursively with configurable include/exclude patterns
2. WHEN scanning files THEN the system SHALL parse frontmatter metadata (title, aliases, tags, id, date, publish status)
3. WHEN running without `--template` option THEN the system SHALL only validate and report issues without modifying any files
4. WHEN running with `--template <template_file_path>` option THEN the system SHALL use that template file's frontmatter as the schema reference
5. WHEN a file's frontmatter already matches the template schema THEN the system SHALL not modify that file
6. WHEN a file's frontmatter has valid values that don't conflict with the template THEN the system SHALL preserve those values
7. WHEN frontmatter is invalid THEN the system SHALL identify missing fields and rule violations based on the template schema
8. WHEN I run interactive mode THEN the system SHALL prompt for corrections to frontmatter issues
9. WHEN I run automatic mode with `--execute` THEN the system SHALL apply template-based fixes to frontmatter while preserving existing valid values
10. WHEN validation is complete THEN the system SHALL output results in CSV/JSON format for further processing

### Requirement 2

**User Story:** As an Obsidian user, I want to automatically generate WikiLinks from plain text mentions, so that my notes are properly interconnected without manual linking effort.

#### Acceptance Criteria

1. WHEN scanning note content THEN the system SHALL detect text that matches other notes' titles or aliases
2. WHEN detecting matches THEN the system SHALL exclude text within existing WikiLinks ([[...]])
3. WHEN detecting matches THEN the system SHALL exclude text within regular markdown links ([...](...))
4. WHEN detecting matches THEN the system SHALL exclude text within frontmatter sections
5. WHEN detecting matches THEN the system SHALL exclude text within Link Reference Definitions
6. WHEN detecting matches THEN the system SHALL consider table content as configurable (include/exclude option)
7. WHEN matches are found THEN the system SHALL automatically convert plain text to WikiLink format [[id|alias]]
8. WHEN generating WikiLinks THEN the system SHALL use the file ID and appropriate alias from the target note's frontmatter
9. WHEN link generation is complete THEN the system SHALL output a report of all links created

### Requirement 3

**User Story:** As an Obsidian user, I want to detect and report dead links in my vault, so that I can maintain link integrity and fix broken references.

#### Acceptance Criteria

1. WHEN scanning WikiLinks THEN the system SHALL identify links in format [[id]] and [[id|alias]] that point to non-existent files
2. WHEN scanning regular markdown links THEN the system SHALL identify broken links like [un-link]() with empty or invalid targets
3. WHEN detecting dead links THEN the system SHALL report the source file, line number, and broken link text
4. WHEN generating dead link reports THEN the system SHALL output results in CSV/JSON format with structured data
5. WHEN I run with dry-run mode THEN the system SHALL only report issues without making changes
6. WHEN dead links are found THEN the system SHALL suggest potential fixes based on similar file names or aliases

### Requirement 4

**User Story:** As an Obsidian user, I want to aggregate and merge notes based on tags or search criteria, so that I can create consolidated views of related information.

#### Acceptance Criteria

1. WHEN I specify tag criteria THEN the system SHALL find all notes matching the specified tags
2. WHEN I specify search criteria THEN the system SHALL find notes matching content or metadata patterns
3. WHEN aggregating notes THEN the system SHALL merge content into a single markdown file
4. WHEN merging content THEN the system SHALL preserve source attribution and maintain readability
5. WHEN aggregation is complete THEN the system SHALL output the merged content to a specified file
6. WHEN merging THEN the system SHALL handle duplicate content and provide deduplication options

### Requirement 5

**User Story:** As an Obsidian user, I want a comprehensive CLI interface for all operations, so that I can integrate the tool into scripts and automation workflows.

#### Acceptance Criteria

1. WHEN using the CLI THEN the system SHALL provide commands for validate-frontmatter, auto-link, detect-dead-links, and aggregate operations
2. WHEN running any command THEN the system SHALL support dry-run mode for preview without changes
3. WHEN processing large vaults THEN the system SHALL show progress indicators with rich formatting
4. WHEN operations complete THEN the system SHALL provide structured output in CSV/JSON formats
5. WHEN errors occur THEN the system SHALL provide actionable error messages with suggested solutions
6. WHEN I use help commands THEN the system SHALL display comprehensive usage information with examples
7. WHEN running commands THEN the system SHALL support verbose logging for debugging and audit trails

### Requirement 6

**User Story:** As an Obsidian user, I want flexible configuration options for directory filtering and processing rules, so that I can customize the tool for my specific vault structure.

#### Acceptance Criteria

1. WHEN configuring THEN the system SHALL support multiple include/exclude directory patterns
2. WHEN configuring THEN the system SHALL allow customization of frontmatter schema templates
3. WHEN configuring THEN the system SHALL support custom WikiLink patterns and alias matching rules
4. WHEN configuring THEN the system SHALL allow table content processing to be enabled/disabled
5. WHEN no config exists THEN the system SHALL use sensible defaults for standard Obsidian vaults
6. WHEN config is invalid THEN the system SHALL provide clear validation error messages with examples

### Requirement 12

**User Story:** As an Obsidian user, I want the system to handle YAML type conversion intelligently, so that my frontmatter validation succeeds even when YAML automatically converts my ID numbers and dates to native types.

#### Acceptance Criteria

1. WHEN a frontmatter contains an `id` field with an integer value THEN the system SHALL convert it to a string before validation
2. WHEN a frontmatter contains a `date` field with a date object THEN the system SHALL convert it to an ISO format string before validation
3. WHEN a frontmatter contains boolean values that should be strings THEN the system SHALL convert them to string representations
4. WHEN a frontmatter contains numeric values in fields expecting strings THEN the system SHALL convert them to string representations
5. WHEN a frontmatter field is already a string THEN the system SHALL leave it unchanged
6. WHEN a field contains null/None values THEN the system SHALL handle them appropriately based on the target schema
7. WHEN a field contains values that cannot be converted to the target type THEN the system SHALL provide clear error messages
8. WHEN type conversion occurs THEN the system SHALL log the conversion with original and converted values

### Requirement 7

**User Story:** As an Obsidian user, I want the system to handle Foam Link Reference Definitions correctly, so that automatically generated structural links are not modified inappropriately.

#### Acceptance Criteria

1. WHEN scanning content THEN the system SHALL recognize Link Reference Definitions format: [id|alias]: path "title"
2. WHEN processing WikiLinks THEN the system SHALL exclude text within Link Reference Definitions from auto-linking
3. WHEN detecting dead links THEN the system SHALL validate Link Reference Definition targets separately
4. WHEN generating reports THEN the system SHALL distinguish between WikiLinks and Link Reference Definitions
5. WHEN the system encounters Link Reference Definitions THEN it SHALL preserve them without modification during auto-linking operations

### Requirement 8

**User Story:** As an Obsidian user, I want the system to automatically organize and improve my knowledge base, so that my notes maintain high quality and consistency without manual effort.

#### Acceptance Criteria

1. WHEN analyzing frontmatter THEN the system SHALL identify missing recommended fields based on template schemas and content analysis
2. WHEN missing fields are detected THEN the system SHALL automatically generate appropriate values (tags from content, dates from file metadata, descriptions from first paragraph)
3. WHEN inconsistencies are found THEN the system SHALL fix filename-title mismatches, normalize tag formats, and standardize field values
4. WHEN processing notes THEN the system SHALL detect and suggest related tags based on content similarity and existing tag patterns
5. WHEN organizing content THEN the system SHALL ensure bidirectional linking between related notes
6. WHEN improvements are applied THEN the system SHALL create backups and provide rollback functionality
7. WHEN organization is complete THEN the system SHALL generate a comprehensive improvement report with metrics

### Requirement 9

**User Story:** As an Obsidian user, I want the system to detect and improve content quality issues, so that my knowledge base maintains high standards and usability.

#### Acceptance Criteria

1. WHEN scanning notes THEN the system SHALL identify orphaned notes (no incoming or outgoing links) and suggest connections
2. WHEN analyzing content THEN the system SHALL detect incomplete notes (too short, missing structure, placeholder content)
3. WHEN finding similar content THEN the system SHALL identify potential duplicates and suggest merge operations
4. WHEN processing notes THEN the system SHALL detect broken internal references and suggest fixes
5. WHEN quality issues are found THEN the system SHALL prioritize fixes based on impact and confidence scores
6. WHEN improvements are suggested THEN the system SHALL provide preview mode before applying changes
7. WHEN quality analysis is complete THEN the system SHALL output actionable improvement recommendations

### Requirement 10

**User Story:** As an Obsidian user, I want the system to optimize my vault structure and organization, so that my knowledge base follows best practices and remains maintainable.

#### Acceptance Criteria

1. WHEN analyzing vault structure THEN the system SHALL evaluate directory organization against best practices
2. WHEN structural issues are found THEN the system SHALL suggest file relocations and directory reorganization
3. WHEN processing tags THEN the system SHALL identify tag hierarchy opportunities and suggest consolidation
4. WHEN optimizing structure THEN the system SHALL ensure all file moves preserve existing links and references
5. WHEN reorganization is proposed THEN the system SHALL provide impact analysis and preview of changes
6. WHEN structural changes are applied THEN the system SHALL update all affected links and references automatically
7. WHEN optimization is complete THEN the system SHALL validate that no links are broken and all references remain intact

### Requirement 11

**User Story:** As an Obsidian user, I want continuous maintenance and monitoring of my knowledge base quality, so that I can track improvements and maintain high standards over time.

#### Acceptance Criteria

1. WHEN running maintenance THEN the system SHALL provide scheduled execution capabilities for regular quality checks
2. WHEN tracking quality THEN the system SHALL maintain metrics on note completeness, link density, tag consistency, and structural health
3. WHEN monitoring changes THEN the system SHALL track improvement history and measure impact of organizational changes
4. WHEN quality degrades THEN the system SHALL alert users to emerging issues and suggest preventive actions
5. WHEN generating reports THEN the system SHALL provide trend analysis and quality dashboards
6. WHEN maintenance is complete THEN the system SHALL log all actions taken and provide audit trails
7. WHEN issues are resolved THEN the system SHALL verify fixes and update quality metrics accordingly

## Advanced Auto-Linking Requirements (Semantic Linking)

### Requirement 13: Context-Aware Linking

**User Story:** As an Obsidian user, I want the system to only create links when the text's context matches the target note's meaning, so that links are always relevant and I avoid incorrect connections (e.g., linking "apple" the fruit to "Apple Inc.").

#### Acceptance Criteria

1. WHEN scanning for link candidates, THEN the system SHALL analyze the surrounding text of the candidate (e.g., the paragraph).
2. WHEN a candidate is found, THEN the system SHALL calculate the semantic similarity between the source context and the content of the target note.
3. WHEN a similarity score is calculated, THEN the system SHALL only create a link if the score exceeds a configurable confidence threshold (e.g., 0.7).
4. WHEN a link is created based on semantic similarity, THEN the system's report SHALL indicate the confidence score.

### Requirement 14: Link Disambiguation

**User Story:** As an Obsidian user, when a term like "API" could refer to multiple notes (e.g., "REST API", "AWS API Gateway"), I want the system to intelligently choose the best one or ask me for clarification, so that links are always accurate.

#### Acceptance Criteria

1. WHEN a link candidate could match multiple target notes, THEN the system SHALL use semantic context similarity to rank the potential targets.
2. WHEN running in automatic mode, THEN the system SHALL link to the target with the highest similarity score, provided it is above the confidence threshold.
3. WHEN running in an interactive mode, THEN the system SHALL prompt the user to choose from the top-ranked targets if their similarity scores are close.
4. WHEN no single target has a sufficiently high confidence score, THEN no link SHALL be created.

### Requirement 15: Proactive Alias Suggestion

**User Story:** As an Obsidian user, I want the system to discover and suggest new aliases for my notes, so that my knowledge base's connectivity improves over time as my vocabulary evolves.

#### Acceptance Criteria

1. WHEN analyzing the vault, THEN the system SHALL identify terms that are not existing aliases but frequently appear in contexts semantically similar to a target note.
2. WHEN a potential new alias is identified (e.g., "ML" for "Machine Learning"), THEN the system SHALL suggest adding the new term to the target note's `aliases` frontmatter field.
3. WHEN running in an interactive mode, THEN the user SHALL be prompted to accept or reject the alias suggestion.

### Requirement 16: Section-Level Linking

**User Story:** As an Obsidian user, I want auto-links to point to the specific section of a note being discussed, not just the top of the file, so I can navigate directly to the most relevant information.

#### Acceptance Criteria

1. WHEN analyzing a link candidate, THEN the system SHALL compare the source context's semantic similarity against each section (delimited by headers) of the target note.
2. WHEN the similarity to a specific section is significantly higher than to the note as a whole, THEN the system SHALL generate a header link (e.g., `[[NOTE_ID#Section Title]]`).
3. WHEN generating a header link, THEN the system SHALL ensure the header text is correctly formatted for URL fragments.

### Requirement 17: Intelligent Frontmatter Auto-Enhancement

**User Story:** As an Obsidian user, I want the system to automatically enhance my frontmatter with intelligent suggestions based on content analysis, so that my notes are properly categorized and discoverable without manual effort.

#### Acceptance Criteria

1. WHEN analyzing note content, THEN the system SHALL extract key concepts and suggest relevant tags based on semantic analysis
2. WHEN a note lacks a description field, THEN the system SHALL generate a concise description from the first paragraph or key sentences
3. WHEN detecting related notes through content similarity, THEN the system SHALL suggest bidirectional aliases to improve discoverability
4. WHEN finding notes with similar topics, THEN the system SHALL suggest consistent tag hierarchies and category structures
5. WHEN processing notes in specific directories, THEN the system SHALL apply directory-specific enhancement rules and templates
6. WHEN enhancement suggestions are generated, THEN the system SHALL provide confidence scores and allow selective application
7. WHEN applying enhancements, THEN the system SHALL preserve existing valid metadata and only add missing or improved fields

### Requirement 18: Content-Based Relationship Discovery

**User Story:** As an Obsidian user, I want the system to automatically discover and create relationships between my notes based on content similarity and conceptual connections, so that my knowledge base becomes a truly interconnected second brain.

#### Acceptance Criteria

1. WHEN analyzing vault content, THEN the system SHALL identify conceptually related notes using semantic similarity analysis
2. WHEN related notes are found, THEN the system SHALL suggest automatic WikiLink creation with appropriate context
3. WHEN processing notes, THEN the system SHALL detect implicit references to concepts covered in other notes
4. WHEN finding content gaps, THEN the system SHALL suggest note creation opportunities and provide templates
5. WHEN analyzing note clusters, THEN the system SHALL recommend tag consolidation and hierarchy improvements
6. WHEN discovering relationships, THEN the system SHALL create bidirectional connections and update both source and target notes
7. WHEN relationship confidence is low, THEN the system SHALL present suggestions for user review rather than automatic application

### Requirement 19: Advanced Japanese Language Processing

**User Story:** As an Obsidian user working with Japanese content, I want sophisticated language processing that handles variations, synonyms, and cultural context, so that my Japanese knowledge base maintains the same quality as English content.

#### Acceptance Criteria

1. WHEN processing Japanese text, THEN the system SHALL detect and link katakana variations (e.g., インターフェース ↔ インターフェイス)
2. WHEN finding technical terms, THEN the system SHALL match English-Japanese pairs and create appropriate cross-references
3. WHEN analyzing content, THEN the system SHALL handle honorific variations and formal/informal language differences
4. WHEN processing compound words, THEN the system SHALL break down and match component parts for better linking
5. WHEN detecting abbreviations, THEN the system SHALL expand and link to full forms (e.g., DB → データベース)
6. WHEN finding synonyms, THEN the system SHALL suggest bidirectional alias additions to improve discoverability
7. WHEN processing mixed-language content, THEN the system SHALL maintain context awareness across language boundaries

### Requirement 20: Automated Knowledge Base Maintenance

**User Story:** As an Obsidian user, I want my knowledge base to maintain itself automatically through continuous monitoring and improvement, so that it remains organized and high-quality without constant manual intervention.

#### Acceptance Criteria

1. WHEN running maintenance, THEN the system SHALL detect and fix broken internal references automatically
2. WHEN analyzing content quality, THEN the system SHALL identify and merge duplicate or highly similar notes
3. WHEN processing tags, THEN the system SHALL automatically consolidate synonymous tags and maintain hierarchy consistency
4. WHEN detecting orphaned notes, THEN the system SHALL suggest connections based on content analysis and create appropriate links
5. WHEN finding outdated information, THEN the system SHALL flag notes for review and suggest updates based on newer content
6. WHEN analyzing vault structure, THEN the system SHALL recommend and apply file organization improvements
7. WHEN maintenance is complete, THEN the system SHALL generate comprehensive reports showing all improvements made

### Requirement 21: Contextual Link Intelligence

**User Story:** As an Obsidian user, I want the system to understand context when creating links, so that it only creates meaningful connections and avoids false positives like linking "apple" the fruit to "Apple Inc."

#### Acceptance Criteria

1. WHEN analyzing potential links, THEN the system SHALL evaluate semantic context using surrounding paragraphs and document themes
2. WHEN multiple targets exist for a term, THEN the system SHALL rank candidates by contextual relevance and confidence scores
3. WHEN context is ambiguous, THEN the system SHALL present disambiguation options rather than making incorrect automatic links
4. WHEN creating links, THEN the system SHALL consider document categories, tags, and directory structure for context clues
5. WHEN processing technical content, THEN the system SHALL maintain domain-specific context awareness (e.g., programming vs. cooking)
6. WHEN link confidence is below threshold, THEN the system SHALL skip automatic linking and suggest manual review
7. WHEN context analysis is complete, THEN the system SHALL provide detailed reasoning for link creation decisions

### Requirement 22: MOC (Map of Content) 構築支援

**User Story:** As an LYT practitioner, I want to efficiently construct and maintain MOCs (Maps of Content) that structure related note clusters, so that I can promote emergence and deeper understanding through organized knowledge structures.

#### Acceptance Criteria

1. WHEN analyzing the vault, THEN the system SHALL identify densely connected note clusters that lack MOC organization
2. WHEN MOC candidates are found, THEN the system SHALL propose MOC creation with suggested titles and initial structure
3. WHEN a user specifies a theme, THEN the system SHALL perform semantic search and generate MOC draft files with relevant notes
4. WHEN analyzing existing MOCs, THEN the system SHALL identify contextually isolated notes that should be linked to the MOC
5. WHEN MOC recommendations are made, THEN the system SHALL provide clustering rationale and relationship explanations
6. WHEN generating MOC drafts, THEN the system SHALL organize notes by logical relationships (premise, example, detail, contradiction)
7. WHEN MOC maintenance is performed, THEN the system SHALL suggest structural improvements and missing connections

### Requirement 23: コンセプトベースの自動タグ付け・エイリアス生成

**User Story:** As a note-taker, I want AI to extract core concepts from my note content and automatically generate appropriate tags and aliases, so that my notes are properly categorized without manual effort.

#### Acceptance Criteria

1. WHEN processing note content, THEN the system SHALL use LLM analysis to extract 3-5 core concepts as keywords
2. WHEN core concepts are extracted, THEN the system SHALL normalize them against existing tags and aliases in the vault
3. WHEN concept normalization is complete, THEN the system SHALL resolve synonyms (e.g., "AI" and "人工知能") into consistent terminology
4. WHEN generating tags, THEN the system SHALL respect existing tag hierarchies and suggest appropriate parent-child relationships
5. WHEN creating aliases, THEN the system SHALL ensure bidirectional discoverability between concept variations
6. WHEN concept extraction is uncertain, THEN the system SHALL provide confidence scores and allow user review
7. WHEN frontmatter updates are applied, THEN the system SHALL preserve existing valid metadata while adding enhancements

### Requirement 24: ノート間の論理的関係性の明示

**User Story:** As a knowledge worker, I want to understand not just that two notes are related, but how they are logically connected (premise, example, contradiction, etc.), so that I can build more coherent knowledge structures.

#### Acceptance Criteria

1. WHEN analyzing note relationships, THEN the system SHALL identify logical relationship types (PREMISE, EXAMPLE, CONTRADICTION, DETAIL, ELABORATION)
2. WHEN relationship types are determined, THEN the system SHALL provide natural language explanations for each connection
3. WHEN displaying relationships, THEN the system SHALL use structured formats like "[[Note A]] is a premise for [[Note B]]"
4. WHEN building MOCs, THEN the system SHALL organize notes according to their logical relationships
5. WHEN generating reports, THEN the system SHALL highlight contradictions and knowledge gaps in the relationship network
6. WHEN relationship confidence is low, THEN the system SHALL mark uncertain connections for user verification
7. WHEN logical relationships are established, THEN the system SHALL suggest additional notes that could strengthen the argument chain

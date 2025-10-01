# Requirements Document

## Introduction

This feature implements a knowledge base organizer specifically designed for Obsidian vaults and markdown-based note systems. The system focuses on note quality improvement through frontmatter validation, automatic link generation, and dead link detection. It provides CLI-based operations with structured output formats (CSV, JSON) for automation and integration with other tools.

The application prioritizes frontmatter standardization, intelligent WikiLink generation from plain text, and comprehensive link validation to maintain a high-quality knowledge base.

## Requirements

### Requirement 1

**User Story:** As an Obsidian user, I want to validate and fix frontmatter in my notes according to predefined schemas, so that my knowledge base maintains consistent metadata structure.

#### Acceptance Criteria

1. WHEN I provide a vault directory path THEN the system SHALL scan all markdown files recursively with configurable include/exclude patterns
2. WHEN scanning files THEN the system SHALL parse frontmatter metadata (title, aliases, tags, id, date, publish status)
3. WHEN validating frontmatter THEN the system SHALL check against predefined templates/schemas
4. WHEN frontmatter is invalid THEN the system SHALL identify missing fields and rule violations
5. WHEN I run interactive mode THEN the system SHALL prompt for corrections to frontmatter issues
6. WHEN I run automatic mode THEN the system SHALL apply predefined fixes to frontmatter
7. WHEN validation is complete THEN the system SHALL output results in CSV/JSON format for further processing

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

### Requirement 7

**User Story:** As an Obsidian user, I want the system to handle Foam Link Reference Definitions correctly, so that automatically generated structural links are not modified inappropriately.

#### Acceptance Criteria

1. WHEN scanning content THEN the system SHALL recognize Link Reference Definitions format: [id|alias]: path "title"
2. WHEN processing WikiLinks THEN the system SHALL exclude text within Link Reference Definitions from auto-linking
3. WHEN detecting dead links THEN the system SHALL validate Link Reference Definition targets separately
4. WHEN generating reports THEN the system SHALL distinguish between WikiLinks and Link Reference Definitions
5. WHEN the system encounters Link Reference Definitions THEN it SHALL preserve them without modification during auto-linking operations

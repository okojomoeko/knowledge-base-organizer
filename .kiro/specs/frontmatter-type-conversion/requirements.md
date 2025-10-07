# Requirements Document

## Introduction

The current frontmatter validation system fails because YAML parsing automatically converts certain values to their native Python types (integers, dates, booleans), but the Pydantic models expect string types for consistency and flexibility. This feature will implement intelligent type conversion during frontmatter parsing to ensure compatibility between YAML's automatic type conversion and the application's string-based schema requirements.

## Requirements

### Requirement 1

**User Story:** As a knowledge base user, I want my frontmatter validation to succeed even when YAML automatically converts my ID numbers and dates to native types, so that I don't have to manually quote every numeric ID and date in my files.

#### Acceptance Criteria

1. WHEN a frontmatter contains an `id` field with an integer value THEN the system SHALL convert it to a string before validation
2. WHEN a frontmatter contains a `date` field with a date object THEN the system SHALL convert it to an ISO format string before validation
3. WHEN a frontmatter contains boolean values that should be strings THEN the system SHALL convert them to string representations
4. WHEN a frontmatter contains numeric values in fields expecting strings THEN the system SHALL convert them to string representations
5. WHEN a frontmatter field is already a string THEN the system SHALL leave it unchanged

### Requirement 2

**User Story:** As a developer, I want the type conversion to be configurable per field, so that I can specify which fields should undergo automatic type conversion and which should remain in their original types.

#### Acceptance Criteria

1. WHEN defining a frontmatter schema THEN the system SHALL allow specifying type conversion rules per field
2. WHEN a field has no conversion rule specified THEN the system SHALL use sensible defaults based on the target type
3. WHEN a field is marked as "no conversion" THEN the system SHALL preserve the original YAML-parsed type
4. WHEN multiple conversion strategies are available for a type THEN the system SHALL allow specifying the preferred strategy

### Requirement 3

**User Story:** As a knowledge base maintainer, I want to see clear feedback about type conversions that occurred during validation, so that I can understand what changes were made to my data.

#### Acceptance Criteria

1. WHEN type conversion occurs during validation THEN the system SHALL log the conversion with original and converted values
2. WHEN running in verbose mode THEN the system SHALL display all type conversions performed
3. WHEN a type conversion fails THEN the system SHALL provide a clear error message explaining why the conversion failed
4. WHEN no type conversions are needed THEN the system SHALL not generate unnecessary conversion messages

### Requirement 4

**User Story:** As a system administrator, I want the type conversion to be backward compatible, so that existing configurations and data continue to work without modification.

#### Acceptance Criteria

1. WHEN processing frontmatter that previously worked THEN the system SHALL continue to work without changes
2. WHEN no type conversion is configured THEN the system SHALL behave exactly as before
3. WHEN type conversion is enabled THEN the system SHALL not break existing valid frontmatter
4. WHEN upgrading the system THEN existing frontmatter validation should improve without manual intervention

### Requirement 5

**User Story:** As a knowledge base user, I want the `--execute` mode to actually fix the type issues in my frontmatter files, so that after running the command my files are corrected and validation passes.

#### Acceptance Criteria

1. WHEN running `validate-frontmatter --execute` THEN the system SHALL actually modify files with type conversion issues
2. WHEN type conversion fixes are applied THEN the system SHALL write the corrected frontmatter back to the original files
3. WHEN files are modified THEN the system SHALL preserve the original file structure and formatting as much as possible
4. WHEN running validation after `--execute` THEN previously invalid files SHALL now pass validation
5. WHEN using git-managed directories THEN file modifications SHALL be detectable through git status

### Requirement 6

**User Story:** As a developer, I want the type conversion system to handle edge cases gracefully, so that unusual but valid YAML structures don't cause system failures.

#### Acceptance Criteria

1. WHEN a field contains null/None values THEN the system SHALL handle them appropriately based on the target schema
2. WHEN a field contains complex nested structures THEN the system SHALL apply conversion rules recursively where appropriate
3. WHEN a field contains values that cannot be converted to the target type THEN the system SHALL provide clear error messages
4. WHEN a field contains empty values THEN the system SHALL handle them according to the schema's requirements
5. WHEN a field contains special YAML values (like scientific notation) THEN the system SHALL convert them appropriately

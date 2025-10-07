"""Use case for frontmatter validation against template schemas."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from ..domain.models import FieldType, ValidationResult
from ..domain.services import FrontmatterValidationService
from ..infrastructure.config import ProcessingConfig
from ..infrastructure.file_repository import FileRepository
from ..infrastructure.template_schema_repository import TemplateSchemaRepository


class FrontmatterValidationRequest(BaseModel):
    """Request for frontmatter validation."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    vault_path: Path
    dry_run: bool = True
    include_patterns: list[str] | None = None
    exclude_patterns: list[str] | None = None
    template_name: str | None = None  # Validate against specific template


class FrontmatterValidationResult(BaseModel):
    """Result of frontmatter validation operation."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    results: list[ValidationResult]
    schemas_used: dict[str, Any]
    total_files: int
    valid_files: int
    invalid_files: int
    files_with_warnings: int
    summary: dict[str, Any]


class FrontmatterValidationUseCase:
    """Use case for validating frontmatter against template schemas."""

    def __init__(
        self,
        file_repository: FileRepository,
        template_schema_repository: TemplateSchemaRepository,
        validation_service: FrontmatterValidationService,
        config: ProcessingConfig,
    ) -> None:
        """Initialize frontmatter validation use case."""
        self.file_repository = file_repository
        self.template_schema_repository = template_schema_repository
        self.validation_service = validation_service
        self.config = config

    def execute(
        self, request: FrontmatterValidationRequest
    ) -> FrontmatterValidationResult:
        """Execute frontmatter validation."""
        # 1. Extract schemas from template files (Single Source of Truth)
        schemas = self.template_schema_repository.extract_schemas_from_templates()

        if not schemas:
            return FrontmatterValidationResult(
                results=[],
                schemas_used={},
                total_files=0,
                valid_files=0,
                invalid_files=0,
                files_with_warnings=0,
                summary={"error": "No template schemas found"},
            )

        # 2. Load all markdown files from vault
        files = self.file_repository.load_vault(request.vault_path)

        if not files:
            return FrontmatterValidationResult(
                results=[],
                schemas_used={
                    schema.template_name: schema.template_path
                    for schema in schemas.values()
                },
                total_files=0,
                valid_files=0,
                invalid_files=0,
                files_with_warnings=0,
                summary={"error": "No markdown files found"},
            )

        # 3. Validate each file
        results = []
        valid_count = 0
        invalid_count = 0
        warnings_count = 0

        for file in files:
            # Detect appropriate template type for each file
            if request.template_name:
                template_type = request.template_name
            else:
                template_type = self.template_schema_repository.detect_template_type(
                    file
                )

            if template_type and template_type in schemas:
                schema = schemas[template_type]

                # Use enhanced validation service
                validation_result = (
                    self.validation_service.validate_with_detailed_analysis(
                        file.frontmatter, schema, file.path
                    )
                )

                # Apply fixes if not dry-run
                if not request.dry_run and not validation_result.is_valid:
                    # Use template-based comprehensive fixes
                    self._apply_template_based_fixes(file, schema)

                    # Save the modified file with template order
                    template_order = list(schema.fields.keys())
                    self.file_repository.save_file(file, template_order=template_order)

                    # Re-validate after applying fixes
                    validation_result = (
                        self.validation_service.validate_with_detailed_analysis(
                            file.frontmatter, schema, file.path
                        )
                    )

                results.append(validation_result)

                # Update counters
                if validation_result.is_valid:
                    valid_count += 1
                else:
                    invalid_count += 1

                if validation_result.warnings:
                    warnings_count += 1

            else:
                # No template detected - create a basic validation result
                validation_result = ValidationResult(
                    file_path=file.path,
                    template_type=None,
                    is_valid=True,  # No schema to validate against
                    missing_fields=[],
                    invalid_fields={},
                    suggested_fixes={},
                    warnings=["No template schema detected for this file"],
                )
                results.append(validation_result)
                valid_count += 1
                warnings_count += 1

        # 4. Generate summary
        summary = self._generate_summary(results, schemas)

        return FrontmatterValidationResult(
            results=results,
            schemas_used={
                name: str(schema.template_path) for name, schema in schemas.items()
            },
            total_files=len(files),
            valid_files=valid_count,
            invalid_files=invalid_count,
            files_with_warnings=warnings_count,
            summary=summary,
        )

    def _apply_fixes(self, file: Any, fixes: list[Any]) -> None:
        """Apply suggested fixes to a file's frontmatter."""
        if not fixes:
            return

        # Apply fixes to the file's frontmatter
        for fix in fixes:
            if fix.fix_type in ("add", "modify"):
                setattr(file.frontmatter, fix.field_name, fix.suggested_value)

        # Save the modified file back to disk
        self.file_repository.save_file(file)

    def _apply_template_based_fixes(self, file: Any, schema: Any) -> None:
        """Apply comprehensive template-based fixes to frontmatter."""
        # Get current frontmatter as dict
        current_frontmatter = file.frontmatter.model_dump(exclude_unset=True)

        # Create new frontmatter based on template schema
        new_frontmatter = {}

        # Add all template fields in template order
        for field_name, field_def in schema.fields.items():
            if field_name in current_frontmatter:
                # Keep existing value if it has content, but ensure proper type
                value = current_frontmatter[field_name]
                if value is not None and (
                    not isinstance(value, list) or len(value) > 0
                ):
                    # Keep existing non-empty value
                    new_frontmatter[field_name] = (
                        self._convert_value_to_template_format(value, field_def)
                    )
                elif field_def.required or field_def.default_value is not None:
                    # Use default for empty/null values if field is required or has default
                    if field_name == "published" and "date" in current_frontmatter:
                        new_frontmatter[field_name] = current_frontmatter["date"]
                    else:
                        new_frontmatter[field_name] = field_def.default_value
                else:
                    # For optional fields without defaults, keep the existing value even if empty
                    new_frontmatter[field_name] = (
                        self._convert_value_to_template_format(value, field_def)
                    )
            elif field_def.required or field_def.default_value is not None:
                # Add missing required fields or fields with defaults
                if field_name == "published" and "date" in current_frontmatter:
                    # Use date field value for published if available
                    new_frontmatter[field_name] = current_frontmatter["date"]
                else:
                    new_frontmatter[field_name] = field_def.default_value
            # Add optional fields with appropriate defaults
            elif field_name in ("image", "description", "category"):
                if field_name == "image":
                    new_frontmatter[field_name] = (
                        "../../assets/images/svg/undraw/undraw_scrum_board.svg"
                    )
                elif field_name == "description":
                    new_frontmatter[field_name] = ""
                elif field_name == "category":
                    new_frontmatter[field_name] = []

        # Update the file's frontmatter with new structure
        for field_name, value in new_frontmatter.items():
            setattr(file.frontmatter, field_name, value)

        # Remove fields not in template (optional - could be configurable)
        frontmatter_dict = file.frontmatter.model_dump(exclude_unset=True)
        for field_name in list(frontmatter_dict.keys()):
            if field_name not in schema.fields:
                # Keep unexpected fields for now, but could remove them
                pass

    def _convert_value_to_template_format(self, value: Any, field_def: Any) -> Any:
        """Convert value to match template field format."""
        if field_def.field_type == FieldType.ARRAY and not isinstance(value, list):
            if isinstance(value, str):
                return [item.strip() for item in value.split(",")]
            return [value]

        if field_def.field_type == FieldType.STRING and not isinstance(value, str):
            return str(value)

        if field_def.field_type == FieldType.BOOLEAN and not isinstance(value, bool):
            if isinstance(value, str):
                return value.lower() in ("true", "yes", "1", "on")
            return bool(value)

        return value

    def _generate_summary(
        self, results: list[ValidationResult], schemas: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate validation summary statistics."""
        total_files = len(results)
        valid_files = sum(1 for r in results if r.is_valid)
        invalid_files = total_files - valid_files

        # Count issues by type
        missing_fields_count = sum(len(r.missing_fields) for r in results)
        invalid_fields_count = sum(len(r.invalid_fields) for r in results)
        warnings_count = sum(len(r.warnings) for r in results)

        # Template usage statistics
        template_usage = {}
        for result in results:
            if result.template_type:
                template_usage[result.template_type] = (
                    template_usage.get(result.template_type, 0) + 1
                )

        # Most common issues
        all_missing_fields = []
        all_invalid_fields = []
        for result in results:
            all_missing_fields.extend(result.missing_fields)
            all_invalid_fields.extend(result.invalid_fields.keys())

        missing_field_counts = {}
        for field in all_missing_fields:
            missing_field_counts[field] = missing_field_counts.get(field, 0) + 1

        invalid_field_counts = {}
        for field in all_invalid_fields:
            invalid_field_counts[field] = invalid_field_counts.get(field, 0) + 1

        return {
            "total_files": total_files,
            "valid_files": valid_files,
            "invalid_files": invalid_files,
            "validation_rate": f"{(valid_files / total_files * 100):.1f}%"
            if total_files > 0
            else "0%",
            "issues": {
                "missing_fields": missing_fields_count,
                "invalid_fields": invalid_fields_count,
                "warnings": warnings_count,
            },
            "template_usage": template_usage,
            "schemas_found": len(schemas),
            "most_common_missing_fields": dict(
                sorted(missing_field_counts.items(), key=lambda x: x[1], reverse=True)[
                    :5
                ]
            ),
            "most_common_invalid_fields": dict(
                sorted(invalid_field_counts.items(), key=lambda x: x[1], reverse=True)[
                    :5
                ]
            ),
        }

"""Use case for frontmatter validation against template schemas."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from ..domain.models import FieldType, Frontmatter, ValidationResult
from ..domain.services import FrontmatterValidationService
from ..domain.services.yaml_type_converter import YAMLTypeConverter
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
    template_path: Path | None = None  # Path to specific template file for validation


class FrontmatterValidationResult(BaseModel):
    """Result of frontmatter validation operation."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    results: list[ValidationResult]
    schemas_used: dict[str, Any]
    template_used: Path | None = None  # Template file used for validation
    schema_used: Any | None = None  # Schema extracted from template
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
        type_converter: YAMLTypeConverter | None = None,
    ) -> None:
        """Initialize frontmatter validation use case."""
        self.file_repository = file_repository
        self.template_schema_repository = template_schema_repository
        self.validation_service = validation_service
        self.config = config
        self.type_converter = type_converter or YAMLTypeConverter()

    def execute(
        self, request: FrontmatterValidationRequest
    ) -> FrontmatterValidationResult:
        """Execute frontmatter validation."""
        self._prepare_config_for_request(request)

        # Handle template-based validation (new behavior)
        if request.template_path:
            return self._execute_template_based_validation(request)

        # Handle legacy validation (existing behavior)
        return self._execute_legacy_validation(request)

    def _prepare_config_for_request(self, request: FrontmatterValidationRequest) -> None:
        """Prepare file repository config based on request."""
        if request.include_patterns or request.exclude_patterns:
            # Create a copy to not modify the base config for other operations
            request_config = self.config.model_copy()
            if request.include_patterns:
                request_config.include_patterns = request.include_patterns
            if request.exclude_patterns:
                # Append to existing exclude patterns
                request_config.exclude_patterns.extend(request.exclude_patterns)
            self.file_repository.config = request_config
            self.template_schema_repository.config = request_config
        else:
            # Ensure default config is used if no request-specific patterns
            self.file_repository.config = self.config
            self.template_schema_repository.config = self.config

    def _execute_template_based_validation(
        self, request: FrontmatterValidationRequest
    ) -> FrontmatterValidationResult:
        """Execute validation using specified template file."""
        # 1. Extract schema from specified template file
        try:
            schema = (
                self.template_schema_repository.extract_schema_from_single_template(
                    request.template_path
                )
            )
        except (FileNotFoundError, ValueError) as e:
            return FrontmatterValidationResult(
                results=[],
                schemas_used={},
                template_used=request.template_path,
                schema_used=None,
                total_files=0,
                valid_files=0,
                invalid_files=0,
                files_with_warnings=0,
                summary={"error": f"Template error: {e}"},
            )

        # 2. Load all markdown files from vault
        files = self.file_repository.load_vault(request.vault_path)

        # Exclude the template file itself from validation
        files = [f for f in files if f.path != request.template_path]

        if not files:
            return FrontmatterValidationResult(
                results=[],
                schemas_used={schema.template_name: str(schema.template_path)},
                template_used=request.template_path,
                schema_used=schema,
                total_files=0,
                valid_files=0,
                invalid_files=0,
                files_with_warnings=0,
                summary={"error": "No markdown files found (excluding template)"},
            )

        # 3. Validate each file against the template schema
        results = []
        valid_count = 0
        invalid_count = 0
        warnings_count = 0
        files_modified = 0

        for file in files:
            # Apply type conversion to handle YAML automatic conversion
            frontmatter_dict = file.frontmatter.model_dump(exclude_unset=True)
            converted_frontmatter, type_conversions = (
                self.type_converter.convert_frontmatter_types(frontmatter_dict, schema)
            )

            # Log type conversions if any were performed
            if type_conversions:
                self.type_converter.log_conversions(type_conversions)

            # Create updated frontmatter with converted types
            updated_frontmatter = Frontmatter.model_validate(converted_frontmatter)

            # Validate frontmatter against template schema
            validation_result = self.validation_service.validate_with_detailed_analysis(
                updated_frontmatter, schema, file.path
            )

            # Check if file needs modification (including type conversions and template compliance)
            frontmatter_dict = file.frontmatter.model_dump(exclude_unset=True)
            is_template_compliant = self._is_template_compliant(
                frontmatter_dict, schema
            )

            needs_modification = (
                not validation_result.is_valid
                or bool(validation_result.suggested_fixes)
                or bool(type_conversions)
                or not is_template_compliant
            )

            # Apply fixes if not dry-run and file needs modification
            if not request.dry_run and needs_modification:
                # First apply type conversions to the file's frontmatter
                if type_conversions:
                    for field_name, value in converted_frontmatter.items():
                        setattr(file.frontmatter, field_name, value)

                # Then apply template-based fixes
                if self._apply_template_based_fixes_safely(
                    file, schema, validation_result
                ):
                    files_modified += 1

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

        # 4. Generate summary
        summary = self._generate_template_based_summary(results, schema, files_modified)

        return FrontmatterValidationResult(
            results=results,
            schemas_used={schema.template_name: str(schema.template_path)},
            template_used=request.template_path,
            schema_used=schema,
            total_files=len(files),
            valid_files=valid_count,
            invalid_files=invalid_count,
            files_with_warnings=warnings_count,
            summary=summary,
        )

    def _execute_legacy_validation(
        self, request: FrontmatterValidationRequest
    ) -> FrontmatterValidationResult:
        """Execute legacy validation (existing behavior)."""
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
                summary={
                    "validation_mode": "legacy",
                    "error": "No template schemas found",
                },
            )

        # 2. Load all markdown files from vault
        files = self.file_repository.load_vault(request.vault_path)

        if not files:
            return FrontmatterValidationResult(
                results=[],
                schemas_used={
                    schema.template_name: str(schema.template_path)
                    for schema in schemas.values()
                },
                total_files=0,
                valid_files=0,
                invalid_files=0,
                files_with_warnings=0,
                summary={
                    "validation_mode": "legacy",
                    "error": "No markdown files found",
                },
            )

        # 3. Validate each file
        results = []
        valid_count = 0
        invalid_count = 0
        warnings_count = 0

        for file in files:
            # Detect appropriate template type for each file
            template_type = self.template_schema_repository.detect_template_type(file)

            if template_type and template_type in schemas:
                schema = schemas[template_type]

                # Apply type conversion to handle YAML automatic conversion
                frontmatter_dict = file.frontmatter.model_dump(exclude_unset=True)
                converted_frontmatter, type_conversions = (
                    self.type_converter.convert_frontmatter_types(
                        frontmatter_dict, schema
                    )
                )

                # Log type conversions if any were performed
                if type_conversions:
                    self.type_converter.log_conversions(type_conversions)

                # Create updated frontmatter with converted types
                updated_frontmatter = Frontmatter.model_validate(converted_frontmatter)

                # Use enhanced validation service
                validation_result = (
                    self.validation_service.validate_with_detailed_analysis(
                        updated_frontmatter, schema, file.path
                    )
                )

                # Apply fixes if not dry-run
                if not request.dry_run and (
                    not validation_result.is_valid or type_conversions
                ):
                    # First apply type conversions to the file's frontmatter
                    if type_conversions:
                        for field_name, value in converted_frontmatter.items():
                            setattr(file.frontmatter, field_name, value)

                    # Then apply template-based comprehensive fixes
                    if not validation_result.is_valid:
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
                    # Use default for empty/null values if field is required
                    if field_name == "published" and "date" in current_frontmatter:
                        new_frontmatter[field_name] = current_frontmatter["date"]
                    else:
                        new_frontmatter[field_name] = field_def.default_value
                else:
                    # For optional fields, keep existing value even if empty
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

    def _apply_template_based_fixes_safely(
        self, file: Any, schema: Any, _validation_result: ValidationResult
    ) -> bool:
        """Apply template-based fixes with safety checks to preserve existing frontmatter.

        Args:
            file: The markdown file to modify
            schema: The template schema to apply
            _validation_result: The validation result (unused but kept for interface)

        Returns:
            bool: True if any modifications were made, False otherwise
        """
        # Get current frontmatter as dict
        current_frontmatter = file.frontmatter.model_dump(exclude_unset=True)

        # Track if any changes are made
        changes_made = False

        # Check if file is template-compliant (has all template fields)
        is_template_compliant = self._is_template_compliant(current_frontmatter, schema)

        # Create new frontmatter based on template schema
        new_frontmatter = {}

        # First, preserve ALL existing values
        for field_name, value in current_frontmatter.items():
            new_frontmatter[field_name] = value

        # Add missing template fields if not template-compliant
        if not is_template_compliant:
            for field_name, field_def in schema.fields.items():
                if field_name not in current_frontmatter:
                    # Add missing template field
                    default_value = self._get_safe_default_value(
                        field_name, field_def, current_frontmatter
                    )
                    new_frontmatter[field_name] = default_value
                    changes_made = True
                else:
                    # Field exists - only modify if it's truly invalid
                    existing_value = current_frontmatter[field_name]

                    # Only replace if value is null/None and field is required
                    if (existing_value is None and field_def.required) or (
                        isinstance(existing_value, str)
                        and not existing_value.strip()
                        and field_def.required
                    ):
                        default_value = self._get_safe_default_value(
                            field_name, field_def, current_frontmatter
                        )
                        # Only replace if default value is not None
                        if default_value is not None:
                            new_frontmatter[field_name] = default_value
                            changes_made = True

        # Only update if changes were made
        if changes_made:
            # Update the file's frontmatter with new structure
            for field_name, value in new_frontmatter.items():
                setattr(file.frontmatter, field_name, value)

        return changes_made

    def _is_template_compliant(
        self, current_frontmatter: dict[str, Any], schema: Any
    ) -> bool:
        """Check if the current frontmatter is compliant with the template schema.

        A file is considered template-compliant if it has all the essential template fields.
        """
        # Essential template fields that should be present
        essential_fields = {
            "title",
            "aliases",
            "tags",
            "id",
            "published",
            "image",
            "description",
        }

        # Check if all essential fields are present
        for field_name in essential_fields:
            if field_name in schema.fields and field_name not in current_frontmatter:
                return False

        return True

    def _is_valid_existing_value(self, value: Any, field_def: Any) -> bool:
        """Check if an existing value is valid and should be preserved.

        Args:
            value: The existing value
            field_def: The field definition from schema

        Returns:
            bool: True if the value is valid and should be preserved
        """
        # Null/None values are only invalid for required fields
        if value is None:
            return not field_def.required

        # Empty strings are only invalid for required string fields
        if isinstance(value, str) and not value.strip():
            return not field_def.required

        # All other values (including empty lists, false booleans) are valid
        return True

    def _get_safe_default_value(
        self, field_name: str, field_def: Any, current_frontmatter: dict[str, Any]
    ) -> Any:
        """Get a safe default value for a field, considering existing frontmatter.

        Args:
            field_name: Name of the field
            field_def: Field definition from schema
            current_frontmatter: Current frontmatter values

        Returns:
            Any: Safe default value for the field
        """
        # Use field definition default if available
        if field_def.default_value is not None:
            return field_def.default_value

        # Special handling for specific fields
        if field_name == "published" and "date" in current_frontmatter:
            date_value = current_frontmatter["date"]
            # Only use date if it's not empty
            if date_value and str(date_value).strip():
                return date_value

        # Provide appropriate defaults for template fields
        if field_def.field_type == FieldType.ARRAY:
            return []  # Empty array for missing array fields
        if field_def.field_type == FieldType.BOOLEAN:
            return False
        if field_def.field_type == FieldType.INTEGER:
            return 0
        if field_def.field_type == FieldType.NUMBER:
            return 0.0

        # Special defaults for specific fields
        if field_name == "image":
            return "../../assets/images/svg/undraw/undraw_scrum_board.svg"
        if field_name == "description":
            return ""
        if field_name == "category":
            return []

        return ""

    def _generate_template_based_summary(
        self, results: list[ValidationResult], schema: Any, files_modified: int
    ) -> dict[str, Any]:
        """Generate summary for template-based validation."""
        total_files = len(results)
        valid_files = sum(1 for r in results if r.is_valid)
        invalid_files = total_files - valid_files

        # Count issues by type
        missing_fields_count = sum(len(r.missing_fields) for r in results)
        invalid_fields_count = sum(len(r.invalid_fields) for r in results)
        warnings_count = sum(len(r.warnings) for r in results)

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
            "validation_mode": "template-based",
            "template_name": schema.template_name,
            "template_path": str(schema.template_path),
            "total_files": total_files,
            "valid_files": valid_files,
            "invalid_files": invalid_files,
            "files_modified": files_modified,
            "validation_rate": f"{(valid_files / total_files * 100):.1f}%"
            if total_files > 0
            else "0%",
            "issues": {
                "missing_fields": missing_fields_count,
                "invalid_fields": invalid_fields_count,
                "warnings": warnings_count,
            },
            "template_fields": list(schema.fields.keys()),
            "required_fields": list(schema.required_fields),
            "optional_fields": list(schema.optional_fields),
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
            "validation_mode": "legacy",
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

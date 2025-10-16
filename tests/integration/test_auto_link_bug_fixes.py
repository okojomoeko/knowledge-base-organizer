"""Integration test for fixing auto-link generation bugs.

This test addresses the issues described in FIX_AUTO_LINK.md:
- Frontmatter deletion
- Unwanted linking of H1 headers
- Destruction of HTML links
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from knowledge_base_organizer.application.auto_link_generation_use_case import (
    AutoLinkGenerationRequest,
    AutoLinkGenerationUseCase,
)
from knowledge_base_organizer.domain.services.content_processing_service import (
    ContentProcessingService,
)
from knowledge_base_organizer.domain.services.link_analysis_service import (
    LinkAnalysisService,
)
from knowledge_base_organizer.infrastructure.config import ProcessingConfig
from knowledge_base_organizer.infrastructure.file_repository import FileRepository


@pytest.fixture
def bug_test_vault_path():
    """Create a temporary vault with specific content to test bug fixes."""
    temp_dir = tempfile.mkdtemp()
    vault_path = Path(temp_dir) / "bug_vault"
    vault_path.mkdir()

    # File to be processed
    source_content = """---
title: Source Note
aliases: [Source]
tags: [test, bug]
id: '20251012100000'
---

# Source Note

This note talks about a Target Note.

It also contains an HTML link that should be preserved: <a href="https://example.com">Example Link</a>.
"""

    # File to be linked to
    target_content = """---
title: Target Note
aliases: [Target]
tags: [test, target]
id: '20251012100100'
---

# Target Note

This is the target.
"""

    (vault_path / "source.md").write_text(source_content, encoding="utf-8")
    (vault_path / "target.md").write_text(target_content, encoding="utf-8")

    yield vault_path
    shutil.rmtree(temp_dir)


@pytest.fixture
def config():
    """Processing configuration for testing."""
    return ProcessingConfig.get_default_config()


@pytest.fixture
def auto_link_use_case(config):
    """Auto-link generation use case with dependencies."""
    file_repository = FileRepository(config)
    link_analysis_service = LinkAnalysisService()
    content_processing_service = ContentProcessingService()

    return AutoLinkGenerationUseCase(
        file_repository=file_repository,
        link_analysis_service=link_analysis_service,
        content_processing_service=content_processing_service,
        config=config,
    )


def test_auto_link_bug_fixes(auto_link_use_case, bug_test_vault_path):
    """
    Verify that auto-linking does not delete frontmatter, link H1s, or break HTML.
    """
    source_file_path = bug_test_vault_path / "source.md"
    original_content = source_file_path.read_text(encoding="utf-8")

    try:
        request = AutoLinkGenerationRequest(
            vault_path=bug_test_vault_path,
            dry_run=False,
        )

        # Execute the use case
        result = auto_link_use_case.execute(request)

        # Verify execution was successful
        assert not result.errors, f"Execution failed with errors: {result.errors}"
        assert result.total_links_created == 1

        # Read the modified content
        modified_content = source_file_path.read_text(encoding="utf-8")

        # 1. Verify Frontmatter is preserved
        assert modified_content.startswith("---"), "Frontmatter block was deleted."
        assert "title: Source Note" in modified_content, "Frontmatter content was lost."
        assert "id: 20251012100000" in modified_content, (
            "Frontmatter content was lost."
        )

        # 2. Verify H1 header is not linked
        assert "# Source Note" in modified_content, (
            "H1 header was incorrectly modified."
        )
        assert "# [[20251012100000|Source Note]]" not in modified_content, (
            "H1 header was incorrectly linked."
        )

        # 3. Verify HTML link is preserved
        assert '<a href="https://example.com">Example Link</a>' in modified_content, (
            "HTML link was broken."
        )

        # 4. Verify the intended link was created
        expected_link = "[[20251012100100]]"  # No alias needed for exact title match
        assert f"This note talks about a {expected_link}." in modified_content, (
            "The correct link was not created."
        )

        # 5. Verify original content is different
        assert original_content != modified_content

    finally:
        # Print the content of the file for debugging, even if tests fail
        if source_file_path.exists():
            modified_content_for_debug = source_file_path.read_text(encoding="utf-8")
            print("\n--- Modified Content ---")
            print(modified_content_for_debug)
            print("--- End Modified Content ---")

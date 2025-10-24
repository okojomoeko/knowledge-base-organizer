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
    link_analysis_service = LinkAnalysisService(config_dir=None)
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
        assert (
            "id: 20251012100000" in modified_content
            or "id: '20251012100000'" in modified_content
        ), "Frontmatter content was lost."

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

        # 4. Verify the intended link was created with alias
        expected_link = "[[20251012100100|Target Note]]"  # Alias is now always included
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


@pytest.fixture
def frontmatter_protection_vault_path():
    """Create a temporary vault to test frontmatter protection."""
    temp_dir = tempfile.mkdtemp()
    vault_path = Path(temp_dir) / "frontmatter_vault"
    vault_path.mkdir()

    # File with specific frontmatter formatting that should be preserved
    source_content = """---
title: Test Frontmatter Protection
image: "../../assets/images/svg/undraw/undraw_scrum_board.svg"
tags: [tag1,tag2]
id: 20240913221802
publish: false
---

# Test Frontmatter Protection

This file mentions Amazon API Gateway which should be linked.
"""

    # Target file
    target_content = """---
title: Amazon API Gateway
id: 20230730200042
tags: [aws, api]
---

# Amazon API Gateway

Amazon API Gateway is a fully managed service.
"""

    (vault_path / "source.md").write_text(source_content, encoding="utf-8")
    (vault_path / "target.md").write_text(target_content, encoding="utf-8")

    yield vault_path
    shutil.rmtree(temp_dir)


def test_frontmatter_protection(auto_link_use_case, frontmatter_protection_vault_path):
    """Test that frontmatter formatting is preserved during auto-link processing."""
    source_file_path = frontmatter_protection_vault_path / "source.md"
    original_content = source_file_path.read_text(encoding="utf-8")

    request = AutoLinkGenerationRequest(
        vault_path=frontmatter_protection_vault_path,
        dry_run=False,
    )

    # Execute the use case
    result = auto_link_use_case.execute(request)

    # Verify execution was successful
    assert not result.errors, f"Execution failed with errors: {result.errors}"
    assert result.total_links_created == 1

    # Read the modified content
    modified_content = source_file_path.read_text(encoding="utf-8")

    # Extract frontmatter sections for comparison
    original_fm = original_content.split("---\n")[1]
    modified_fm = modified_content.split("---\n")[1]

    # Verify frontmatter formatting is preserved
    assert original_fm == modified_fm, (
        f"Frontmatter formatting was changed:\n"
        f"Original:\n{original_fm}\n"
        f"Modified:\n{modified_fm}"
    )

    # Verify specific formatting elements are preserved
    assert (
        'image: "../../assets/images/svg/undraw/undraw_scrum_board.svg"'
        in modified_content
    ), "Double quotes in image field were not preserved"
    assert "tags: [tag1,tag2]" in modified_content, (
        "Inline array format was not preserved"
    )
    assert "id: 20240913221802" in modified_content, (
        "Numeric ID format was not preserved"
    )

    # Verify the link was created with proper alias
    assert "[[20230730200042|Amazon API Gateway]]" in modified_content, (
        "Link was not created with proper alias"
    )


@pytest.fixture
def lrd_exclusion_vault_path():
    """Create a temporary vault to test LRD exclusion."""
    temp_dir = tempfile.mkdtemp()
    vault_path = Path(temp_dir) / "lrd_vault"
    vault_path.mkdir()

    # File with Link Reference Definitions that should be excluded
    source_content = """---
title: Test LRD Exclusion
id: 20250123000001
tags: [test, lrd]
---

# Test LRD Exclusion

This file mentions Amazon API Gateway which should be linked.

It also mentions EC2 and ELB which should NOT be linked because they appear in LRDs below.

---

[20230727234718|EC2]: 20230727234718 "Amazon Elastic Compute Cloud (Amazon EC2)"
[20230730201034|ELB]: 20230730201034 "Elastic Load Balancing"
[20230802000730|RDS]: 20230802000730 "Amazon Relational Database Service (Amazon RDS)"
"""

    # Target files
    api_gateway_content = """---
title: Amazon API Gateway
id: 20230730200042
tags: [aws, api]
---

# Amazon API Gateway

Amazon API Gateway is a fully managed service.
"""

    ec2_content = """---
title: Amazon Elastic Compute Cloud (Amazon EC2)
aliases: [EC2, Amazon EC2]
id: 20230727234718
tags: [aws, compute]
---

# Amazon Elastic Compute Cloud (Amazon EC2)

Amazon EC2 provides scalable computing capacity.
"""

    (vault_path / "source.md").write_text(source_content, encoding="utf-8")
    (vault_path / "api_gateway.md").write_text(api_gateway_content, encoding="utf-8")
    (vault_path / "ec2.md").write_text(ec2_content, encoding="utf-8")

    yield vault_path
    shutil.rmtree(temp_dir)


def test_lrd_exclusion(auto_link_use_case, lrd_exclusion_vault_path):
    """Test that text in Link Reference Definitions is not converted to WikiLinks."""
    source_file_path = lrd_exclusion_vault_path / "source.md"

    request = AutoLinkGenerationRequest(
        vault_path=lrd_exclusion_vault_path,
        dry_run=False,
    )

    # Execute the use case
    result = auto_link_use_case.execute(request)

    # Verify execution was successful
    assert not result.errors, f"Execution failed with errors: {result.errors}"
    assert (
        result.total_links_created == 2
    )  # Amazon API Gateway and EC2 in body text should be linked

    # Read the modified content
    modified_content = source_file_path.read_text(encoding="utf-8")

    # Verify Amazon API Gateway was linked
    assert "[[20230730200042|Amazon API Gateway]]" in modified_content, (
        "Amazon API Gateway should be linked"
    )

    # Verify EC2 in body text was linked (this is correct behavior)
    assert "It also mentions [[20230727234718|EC2]] and ELB" in modified_content, (
        "EC2 in body text should be linked"
    )

    # Verify LRDs themselves are preserved and NOT modified
    assert "[20230727234718|EC2]: 20230727234718" in modified_content, (
        "LRD should be preserved exactly as is"
    )
    assert "[20230730201034|ELB]: 20230730201034" in modified_content, (
        "LRD should be preserved exactly as is"
    )

    # Most importantly: verify LRD content was NOT converted to WikiLinks
    assert (
        "[20230727234718|[[20230727234718|EC2]]]: 20230727234718"
        not in modified_content
    ), "LRD content should NOT be converted to WikiLinks"
    assert (
        "Amazon Elastic Compute Cloud ([[20230727234718|Amazon EC2]])"
        not in modified_content
    ), "LRD title should NOT be converted to WikiLinks"


@pytest.fixture
def external_link_protection_vault_path():
    """Create a temporary vault to test external link protection."""
    temp_dir = tempfile.mkdtemp()
    vault_path = Path(temp_dir) / "external_link_vault"
    vault_path.mkdir()

    # File with external links that should be protected
    source_content = """---
title: Test External Link Protection
id: 20250123000002
tags: [test, external]
---

# Test External Link Protection

This file mentions Organizations which should be linked in body text.

But this external link should NOT be modified:
[[Organizations]CloudWatchを別アカウントに共有する際にOrganization account selectorを使ってみた | DevelopersIO](https://dev.classmethod.jp/articles/cloudwatch-organizations-selector/)

And this regular external link should also be protected:
[AWS Organizations Documentation](https://docs.aws.amazon.com/organizations/)

Organizations is mentioned again here and should be linked.
"""

    # Target file
    organizations_content = """---
title: AWS Organizations
aliases: [Organizations, AWS Organizations]
id: 20230709211042
tags: [aws, management]
---

# AWS Organizations

AWS Organizations is a service for managing multiple AWS accounts.
"""

    (vault_path / "source.md").write_text(source_content, encoding="utf-8")
    (vault_path / "organizations.md").write_text(
        organizations_content, encoding="utf-8"
    )

    yield vault_path
    shutil.rmtree(temp_dir)


def test_external_link_protection(
    auto_link_use_case, external_link_protection_vault_path
):
    """Test that text within external links is not converted to WikiLinks."""
    source_file_path = external_link_protection_vault_path / "source.md"

    request = AutoLinkGenerationRequest(
        vault_path=external_link_protection_vault_path,
        dry_run=False,
    )

    # Execute the use case
    result = auto_link_use_case.execute(request)

    # Verify execution was successful
    assert not result.errors, f"Execution failed with errors: {result.errors}"
    assert (
        result.total_links_created == 2
    )  # Two mentions of Organizations in body text should be linked

    # Read the modified content
    modified_content = source_file_path.read_text(encoding="utf-8")

    # Verify Organizations in body text was linked
    assert "This file mentions [[20230709211042|Organizations]]" in modified_content, (
        "Organizations in body text should be linked"
    )
    assert "[[20230709211042|Organizations]] is mentioned again" in modified_content, (
        "Second mention of Organizations should be linked"
    )

    # Most importantly: verify external links are preserved and NOT modified
    assert (
        "[[Organizations]CloudWatchを別アカウントに共有する際にOrganization account selectorを使ってみた | DevelopersIO](https://dev.classmethod.jp/articles/cloudwatch-organizations-selector/)"
        in modified_content
    ), "External link with Organizations in text should be preserved exactly"

    assert (
        "[AWS Organizations Documentation](https://docs.aws.amazon.com/organizations/)"
        in modified_content
    ), "Regular external link should be preserved exactly"

    # Verify that Organizations within external links was NOT converted
    assert (
        "[[[[20230709211042|Organizations]]]CloudWatchを別アカウントに"
        not in modified_content
    ), "Organizations within external link should NOT be converted to WikiLink"

    assert (
        "[[[20230709211042|AWS Organizations]] Documentation]" not in modified_content
    ), "Organizations within regular external link should NOT be converted"

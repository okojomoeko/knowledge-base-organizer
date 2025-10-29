"""
Tests for semantic enhancements to auto-link generation use case.

Tests the semantic linking functionality including:
- Semantic candidate discovery
- Integration with vector store
- Fallback behavior when AI services unavailable
"""

from pathlib import Path
from unittest.mock import MagicMock

from knowledge_base_organizer.application.auto_link_generation_use_case import (
    AutoLinkGenerationUseCase,
)
from knowledge_base_organizer.domain.services.ai_services import (
    EmbeddingResult,
    SearchResult,
)
from knowledge_base_organizer.infrastructure.config import ProcessingConfig


class TestSemanticAutoLinkGeneration:
    """Test cases for semantic auto-link generation."""

    def test_semantic_services_available_check(self):
        """Test checking if semantic services are available."""
        config = ProcessingConfig.get_default_config()

        # Mock services
        mock_file_repository = MagicMock()
        mock_link_analysis_service = MagicMock()
        mock_content_processing_service = MagicMock()
        mock_embedding_service = MagicMock()
        mock_vector_store = MagicMock()

        # Test with both services available
        use_case = AutoLinkGenerationUseCase(
            file_repository=mock_file_repository,
            link_analysis_service=mock_link_analysis_service,
            content_processing_service=mock_content_processing_service,
            config=config,
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
        )

        assert use_case._semantic_services_available() is True

        # Test with missing embedding service
        use_case_no_embedding = AutoLinkGenerationUseCase(
            file_repository=mock_file_repository,
            link_analysis_service=mock_link_analysis_service,
            content_processing_service=mock_content_processing_service,
            config=config,
            embedding_service=None,
            vector_store=mock_vector_store,
        )

        assert use_case_no_embedding._semantic_services_available() is False

    def test_prepare_content_for_semantic_search(self):
        """Test content preparation for semantic search."""
        config = ProcessingConfig.get_default_config()

        # Mock services
        mock_file_repository = MagicMock()
        mock_link_analysis_service = MagicMock()
        mock_content_processing_service = MagicMock()

        use_case = AutoLinkGenerationUseCase(
            file_repository=mock_file_repository,
            link_analysis_service=mock_link_analysis_service,
            content_processing_service=mock_content_processing_service,
            config=config,
        )

        # Create mock file object
        mock_file = MagicMock()
        mock_file.frontmatter = {"title": "Test Note", "tags": ["test", "sample"]}
        mock_file.content = """---
title: Test Note
tags: [test, sample]
---
# Test Note

This is a test note with some content for semantic search.
"""

        result = use_case._prepare_content_for_semantic_search(mock_file)

        # Verify content preparation
        assert "Title: Test Note" in result
        assert "Tags: test, sample" in result
        assert "This is a test note" in result
        assert "---" not in result  # Frontmatter should be removed

    def test_find_semantic_candidates_no_services(self):
        """Test semantic candidate discovery when services are not available."""
        config = ProcessingConfig.get_default_config()

        # Mock services
        mock_file_repository = MagicMock()
        mock_link_analysis_service = MagicMock()
        mock_content_processing_service = MagicMock()

        use_case = AutoLinkGenerationUseCase(
            file_repository=mock_file_repository,
            link_analysis_service=mock_link_analysis_service,
            content_processing_service=mock_content_processing_service,
            config=config,
            embedding_service=None,
            vector_store=None,
        )

        # Mock file and registry
        mock_file = MagicMock()
        file_registry = {}

        # Find semantic candidates
        candidates = use_case._find_semantic_candidates(
            source_file=mock_file,
            file_registry=file_registry,
            exclusion_zones=[],
            threshold=0.7,
            max_candidates=5,
        )

        # Verify no candidates were found
        assert len(candidates) == 0

    def test_find_semantic_candidates_basic_flow(self):
        """Test basic semantic candidate discovery flow."""
        config = ProcessingConfig.get_default_config()

        # Mock services
        mock_file_repository = MagicMock()
        mock_link_analysis_service = MagicMock()
        mock_content_processing_service = MagicMock()
        mock_embedding_service = MagicMock()
        mock_vector_store = MagicMock()

        # Setup mocks to return empty results (simpler test)
        mock_embedding_service.create_embedding.return_value = EmbeddingResult(
            vector=[0.1, 0.2, 0.3] * 256, dimension=768, model_name="test-model"
        )
        mock_vector_store.search.return_value = []

        use_case = AutoLinkGenerationUseCase(
            file_repository=mock_file_repository,
            link_analysis_service=mock_link_analysis_service,
            content_processing_service=mock_content_processing_service,
            config=config,
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
        )

        # Mock file and registry
        mock_source_file = MagicMock()
        file_registry = {}

        # Find semantic candidates (should return empty list)
        candidates = use_case._find_semantic_candidates(
            source_file=mock_source_file,
            file_registry=file_registry,
            exclusion_zones=[],
            threshold=0.7,
            max_candidates=5,
        )

        # Verify no candidates were found (empty search results)
        assert len(candidates) == 0

    def test_create_semantic_link_candidate_self_reference(self):
        """Test that semantic candidates don't link to themselves."""
        config = ProcessingConfig.get_default_config()

        # Mock services
        mock_file_repository = MagicMock()
        mock_link_analysis_service = MagicMock()
        mock_content_processing_service = MagicMock()

        use_case = AutoLinkGenerationUseCase(
            file_repository=mock_file_repository,
            link_analysis_service=mock_link_analysis_service,
            content_processing_service=mock_content_processing_service,
            config=config,
        )

        # Mock source file
        mock_source_file = MagicMock()
        mock_source_file.path = Path("/vault/source.md")

        # Mock target file (same as source)
        mock_target_file = MagicMock()
        mock_target_file.path = Path("/vault/source.md")

        file_registry = {"source_123": mock_target_file}

        # Create search result pointing to the same file
        search_result = SearchResult(
            document_id="source_123",
            similarity_score=0.95,
            metadata={"file_path": "/vault/source.md", "title": "Source Note"},
        )

        # Create semantic link candidate (should return None for self-reference)
        candidate = use_case._create_semantic_link_candidate(
            search_result=search_result,
            source_file=mock_source_file,
            file_registry=file_registry,
        )

        # Verify no candidate is created for self-reference
        assert candidate is None

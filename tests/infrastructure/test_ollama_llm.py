"""
Tests for OllamaLLMService implementation.
"""

from unittest.mock import patch

import pytest

from knowledge_base_organizer.domain.services.ai_services import (
    ConceptExtractionResult,
    LLMError,
    MetadataSuggestion,
    ModelNotAvailableError,
    RelationshipAnalysis,
    SimilarityResult,
)
from knowledge_base_organizer.infrastructure.ollama_llm import OllamaLLMService


class TestOllamaLLMService:
    """Test cases for OllamaLLMService."""

    @pytest.fixture
    def mock_requests(self):
        """Mock requests module for testing."""
        with patch(
            "knowledge_base_organizer.infrastructure.ollama_llm.requests"
        ) as mock:
            # Mock successful service availability check
            mock.get.return_value.json.return_value = {
                "models": [{"name": "llama3.2:3b"}]
            }
            mock.get.return_value.raise_for_status.return_value = None
            yield mock

    @pytest.fixture
    def llm_service(self, mock_requests):
        """Create OllamaLLMService instance for testing."""
        return OllamaLLMService()

    def test_initialization(self, mock_requests):
        """Test service initialization."""
        service = OllamaLLMService(
            base_url="http://test:11434", model_name="test-model", timeout=30
        )

        assert service.base_url == "http://test:11434"
        assert service.model_name == "test-model"
        assert service.timeout == 30

    def test_service_availability_check(self, mock_requests):
        """Test service availability verification."""
        # Should not raise exception with mocked successful response
        service = OllamaLLMService()
        assert service is not None

    def test_service_unavailable_error(self):
        """Test error when Ollama service is unavailable."""
        with patch(
            "knowledge_base_organizer.infrastructure.ollama_llm.requests"
        ) as mock:
            import requests

            mock.get.side_effect = requests.exceptions.RequestException(
                "Connection failed"
            )
            mock.exceptions = requests.exceptions

            with pytest.raises(ModelNotAvailableError):
                OllamaLLMService()

    def test_extract_concepts_empty_content(self, llm_service):
        """Test concept extraction with empty content."""
        result = llm_service.extract_concepts("")

        assert isinstance(result, ConceptExtractionResult)
        assert result.concepts == []
        assert result.confidence_scores == []
        assert result.context == "Empty content provided"

    def test_extract_concepts_success(self, llm_service, mock_requests):
        """Test successful concept extraction."""
        # Mock successful LLM response
        mock_requests.post.return_value.json.return_value = {
            "response": "machine learning, artificial intelligence, neural networks"
        }
        mock_requests.post.return_value.raise_for_status.return_value = None

        result = llm_service.extract_concepts("This is about machine learning and AI.")

        assert isinstance(result, ConceptExtractionResult)
        assert len(result.concepts) > 0
        assert len(result.confidence_scores) == len(result.concepts)

    def test_suggest_metadata_empty_content(self, llm_service):
        """Test metadata suggestion with empty content."""
        result = llm_service.suggest_metadata("")

        assert isinstance(result, MetadataSuggestion)
        assert result.suggested_tags == []
        assert result.suggested_aliases == []
        assert result.suggested_description is None

    def test_suggest_metadata_success(self, llm_service, mock_requests):
        """Test successful metadata suggestion."""
        # Mock successful LLM response
        mock_requests.post.return_value.json.return_value = {
            "response": "TAGS: ai, machine-learning\nALIASES: ML, AI\nDESCRIPTION: About AI concepts"
        }
        mock_requests.post.return_value.raise_for_status.return_value = None

        result = llm_service.suggest_metadata("This is about machine learning.")

        assert isinstance(result, MetadataSuggestion)
        assert "tags" in result.confidence_scores
        assert "aliases" in result.confidence_scores
        assert "description" in result.confidence_scores

    def test_summarize_content_empty(self, llm_service):
        """Test content summarization with empty content."""
        result = llm_service.summarize_content("")
        assert result == ""

    def test_summarize_content_success(self, llm_service, mock_requests):
        """Test successful content summarization."""
        # Mock successful LLM response
        mock_requests.post.return_value.json.return_value = {
            "response": "This is a summary of the content."
        }
        mock_requests.post.return_value.raise_for_status.return_value = None

        result = llm_service.summarize_content("Long content to summarize...")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_analyze_relationship_empty_content(self, llm_service):
        """Test relationship analysis with empty content."""
        result = llm_service.analyze_relationship("", "content")

        assert isinstance(result, RelationshipAnalysis)
        assert result.relationship_type == "UNRELATED"
        assert result.confidence == 0.0

    def test_analyze_relationship_success(self, llm_service, mock_requests):
        """Test successful relationship analysis."""
        # Mock successful LLM response
        mock_requests.post.return_value.json.return_value = {
            "response": "RELATIONSHIP: PREMISE\nCONFIDENCE: 0.8\nBIDIRECTIONAL: true\nEXPLANATION: Content A provides foundation for B"
        }
        mock_requests.post.return_value.raise_for_status.return_value = None

        result = llm_service.analyze_relationship("Content A", "Content B")

        assert isinstance(result, RelationshipAnalysis)
        assert result.relationship_type in [
            "PREMISE",
            "EXAMPLE",
            "CONTRADICTION",
            "DETAIL",
            "ELABORATION",
            "PARALLEL",
            "UNRELATED",
        ]

    def test_evaluate_context_match_empty_input(self, llm_service):
        """Test context evaluation with empty input."""
        result = llm_service.evaluate_context_match("", "context", "target")

        assert isinstance(result, SimilarityResult)
        assert result.score == 0.0
        assert result.confidence == 0.0
        assert result.context_match is False

    def test_evaluate_context_match_success(self, llm_service, mock_requests):
        """Test successful context evaluation."""
        # Mock successful LLM response
        mock_requests.post.return_value.json.return_value = {
            "response": "SCORE: 0.8\nCONFIDENCE: 0.9\nMATCH: true\nREASONING: Good semantic match"
        }
        mock_requests.post.return_value.raise_for_status.return_value = None

        result = llm_service.evaluate_context_match(
            "candidate", "source context", "target content"
        )

        assert isinstance(result, SimilarityResult)

    def test_disambiguate_targets_empty_input(self, llm_service):
        """Test target disambiguation with empty input."""
        result = llm_service.disambiguate_targets("", "context", [])
        assert result == []

    def test_disambiguate_targets_success(self, llm_service, mock_requests):
        """Test successful target disambiguation."""
        # Mock successful LLM response
        mock_requests.post.return_value.json.return_value = {
            "response": "TARGET_1: 0.8\nTARGET_2: 0.6"
        }
        mock_requests.post.return_value.raise_for_status.return_value = None

        targets = [("id1", "content1"), ("id2", "content2")]
        result = llm_service.disambiguate_targets("candidate", "context", targets)

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(item, tuple) and len(item) == 2 for item in result)

    def test_get_model_info(self, llm_service, mock_requests):
        """Test getting model information."""
        # Mock successful model info response
        mock_requests.post.return_value.json.return_value = {
            "details": {"parameter_size": "3B"},
            "parameters": {"temperature": 0.3},
        }
        mock_requests.post.return_value.raise_for_status.return_value = None

        info = llm_service.get_model_info()

        assert isinstance(info, dict)
        assert "model_name" in info
        assert "capabilities" in info
        assert "base_url" in info

    def test_llm_error_handling(self, llm_service, mock_requests):
        """Test LLM error handling."""
        # Mock failed LLM response
        mock_requests.post.side_effect = Exception("LLM request failed")

        with pytest.raises(LLMError):
            llm_service.extract_concepts("test content")

    def test_calculate_concept_confidence(self, llm_service):
        """Test concept confidence calculation."""
        # Test with concept that appears in content
        confidence = llm_service._calculate_concept_confidence(
            "machine learning", "This is about machine learning"
        )
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # Should be boosted for appearing in content

        # Test with concept that doesn't appear in content
        confidence = llm_service._calculate_concept_confidence(
            "unrelated", "This is about machine learning"
        )
        assert 0.0 <= confidence <= 1.0

    def test_extract_section(self, llm_service):
        """Test section extraction from LLM response."""
        text = "TAGS: ai, ml, tech\nDESCRIPTION: About AI technology"

        # Test list extraction
        tags = llm_service._extract_section(text, "TAGS")
        assert isinstance(tags, list)
        assert "ai" in tags

        # Test single value extraction
        description = llm_service._extract_section(
            text, "DESCRIPTION", single_value=True
        )
        assert isinstance(description, str)
        assert "AI technology" in description

        # Test non-existent section
        missing = llm_service._extract_section(text, "MISSING")
        assert missing == []

        missing_single = llm_service._extract_section(
            text, "MISSING", single_value=True
        )
        assert missing_single is None

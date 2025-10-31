"""Tests for OpenAI-compatible LLM service."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from knowledge_base_organizer.domain.services.ai_services import (
    ConceptExtractionResult,
    LLMError,
    MetadataSuggestion,
    ModelNotAvailableError,
    RelationshipAnalysis,
    SimilarityResult,
)
from knowledge_base_organizer.infrastructure.openai_compatible_llm import (
    OpenAICompatibleLLMService,
)


class TestOpenAICompatibleLLMService:
    """Test OpenAI-compatible LLM service."""

    def setup_method(self):
        """Set up test environment."""
        with patch(
            "knowledge_base_organizer.infrastructure.openai_compatible_llm.requests"
        ) as mock_requests:
            # Mock successful service availability check
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": [{"id": "local-model"}, {"id": "gpt-3.5-turbo"}]
            }
            mock_requests.get.return_value = mock_response

            self.llm_service = OpenAICompatibleLLMService(
                base_url="http://localhost:1234", model_name="local-model", timeout=60
            )

    def test_initialization(self):
        """Test service initialization."""
        assert self.llm_service.base_url == "http://localhost:1234"
        assert self.llm_service.model_name == "local-model"
        assert self.llm_service.timeout == 60
        assert self.llm_service.api_key is None
        assert self.llm_service.options["temperature"] == 0.3
        assert self.llm_service.options["max_tokens"] == 2048

    def test_initialization_with_api_key(self):
        """Test service initialization with API key."""
        with patch(
            "knowledge_base_organizer.infrastructure.openai_compatible_llm.requests"
        ):
            service = OpenAICompatibleLLMService(
                base_url="http://localhost:1234",
                model_name="local-model",
                api_key="test-key",
                timeout=60,
            )

            assert service.api_key == "test-key"

    def test_initialization_with_custom_options(self):
        """Test service initialization with custom options."""
        with patch(
            "knowledge_base_organizer.infrastructure.openai_compatible_llm.requests"
        ):
            service = OpenAICompatibleLLMService(
                base_url="http://localhost:1234",
                model_name="local-model",
                temperature=0.5,
                max_tokens=1024,
                top_p=0.8,
            )

            assert service.options["temperature"] == 0.5
            assert service.options["max_tokens"] == 1024
            assert service.options["top_p"] == 0.8

    @patch("knowledge_base_organizer.infrastructure.openai_compatible_llm.requests")
    def test_service_availability_check_success(self, mock_requests):
        """Test successful service availability check."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "local-model"}]}
        mock_requests.get.return_value = mock_response

        # Should not raise exception
        OpenAICompatibleLLMService(
            base_url="http://localhost:1234", model_name="local-model"
        )

        mock_requests.get.assert_called_once()

    @patch("knowledge_base_organizer.infrastructure.openai_compatible_llm.requests")
    def test_service_availability_check_model_not_found(self, mock_requests):
        """Test service availability check when model not found."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": [{"id": "other-model"}]}
        mock_requests.get.return_value = mock_response

        # Should use first available model
        service = OpenAICompatibleLLMService(
            base_url="http://localhost:1234", model_name="missing-model"
        )

        assert service.model_name == "other-model"

    @patch("knowledge_base_organizer.infrastructure.openai_compatible_llm.requests")
    def test_service_unavailable_error(self, mock_requests):
        """Test service unavailable error."""
        mock_requests.get.side_effect = requests.exceptions.ConnectionError(
            "Connection failed"
        )

        with pytest.raises(
            ModelNotAvailableError, match="OpenAI-compatible service not available"
        ):
            OpenAICompatibleLLMService(
                base_url="http://localhost:1234", model_name="local-model"
            )

    def test_get_headers_without_api_key(self):
        """Test getting headers without API key."""
        headers = self.llm_service._get_headers()

        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers

    def test_get_headers_with_api_key(self):
        """Test getting headers with API key."""
        with patch(
            "knowledge_base_organizer.infrastructure.openai_compatible_llm.requests"
        ):
            service = OpenAICompatibleLLMService(
                base_url="http://localhost:1234",
                model_name="local-model",
                api_key="test-key",
            )

            headers = service._get_headers()

            assert headers["Content-Type"] == "application/json"
            assert headers["Authorization"] == "Bearer test-key"

    @patch("knowledge_base_organizer.infrastructure.openai_compatible_llm.requests")
    def test_generate_completion_success(self, mock_requests):
        """Test successful completion generation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "This is a test response."}}]
        }
        mock_requests.post.return_value = mock_response

        result = self.llm_service._generate_completion("Test prompt", "System prompt")

        assert result == "This is a test response."

        # Verify request was made correctly
        mock_requests.post.assert_called_once()
        args, kwargs = mock_requests.post.call_args

        assert args[0] == "http://localhost:1234/v1/chat/completions"
        assert "json" in kwargs

        request_data = kwargs["json"]
        assert request_data["model"] == "local-model"
        assert len(request_data["messages"]) == 2
        assert request_data["messages"][0]["role"] == "system"
        assert request_data["messages"][0]["content"] == "System prompt"
        assert request_data["messages"][1]["role"] == "user"
        assert request_data["messages"][1]["content"] == "Test prompt"

    @patch("knowledge_base_organizer.infrastructure.openai_compatible_llm.requests")
    def test_generate_completion_without_system_prompt(self, mock_requests):
        """Test completion generation without system prompt."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response without system prompt."}}]
        }
        mock_requests.post.return_value = mock_response

        result = self.llm_service._generate_completion("Test prompt")

        assert result == "Response without system prompt."

        # Verify only user message was sent
        args, kwargs = mock_requests.post.call_args
        request_data = kwargs["json"]
        assert len(request_data["messages"]) == 1
        assert request_data["messages"][0]["role"] == "user"

    @patch("knowledge_base_organizer.infrastructure.openai_compatible_llm.requests")
    def test_generate_completion_request_error(self, mock_requests):
        """Test completion generation with request error."""
        mock_requests.post.side_effect = requests.exceptions.RequestException(
            "Request failed"
        )

        with pytest.raises(LLMError, match="Failed to generate completion"):
            self.llm_service._generate_completion("Test prompt")

    @patch("knowledge_base_organizer.infrastructure.openai_compatible_llm.requests")
    def test_generate_completion_no_choices(self, mock_requests):
        """Test completion generation with no choices in response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": []}
        mock_requests.post.return_value = mock_response

        with pytest.raises(LLMError, match="No response choices returned from API"):
            self.llm_service._generate_completion("Test prompt")

    @patch("knowledge_base_organizer.infrastructure.openai_compatible_llm.requests")
    def test_generate_completion_empty_response(self, mock_requests):
        """Test completion generation with empty response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": [{"message": {"content": ""}}]}
        mock_requests.post.return_value = mock_response

        with pytest.raises(LLMError, match="Empty response generated from API"):
            self.llm_service._generate_completion("Test prompt")

    def test_extract_concepts_empty_content(self):
        """Test concept extraction with empty content."""
        result = self.llm_service.extract_concepts("")

        assert isinstance(result, ConceptExtractionResult)
        assert result.concepts == []
        assert result.confidence_scores == []
        assert result.context == "Empty content provided"

    @patch.object(OpenAICompatibleLLMService, "_generate_completion")
    def test_extract_concepts_success(self, mock_generate):
        """Test successful concept extraction."""
        mock_generate.return_value = (
            "programming, python, machine learning, data science, algorithms"
        )

        result = self.llm_service.extract_concepts(
            "This is about programming and machine learning."
        )

        assert isinstance(result, ConceptExtractionResult)
        assert len(result.concepts) == 5
        assert "programming" in result.concepts
        assert "python" in result.concepts
        assert len(result.confidence_scores) == 5
        assert all(0.0 <= score <= 1.0 for score in result.confidence_scores)

    def test_suggest_metadata_empty_content(self):
        """Test metadata suggestion with empty content."""
        result = self.llm_service.suggest_metadata("")

        assert isinstance(result, MetadataSuggestion)
        assert result.suggested_tags == []
        assert result.suggested_aliases == []
        assert result.suggested_description is None

    @patch.object(OpenAICompatibleLLMService, "_generate_completion")
    def test_suggest_metadata_success(self, mock_generate):
        """Test successful metadata suggestion."""
        mock_generate.return_value = """TAGS: python, programming, tutorial
ALIASES: Python Guide, Programming Tutorial, Coding Basics
DESCRIPTION: A comprehensive guide to Python programming for beginners."""

        result = self.llm_service.suggest_metadata(
            "Python programming tutorial content"
        )

        assert isinstance(result, MetadataSuggestion)
        assert "python" in result.suggested_tags
        assert "programming" in result.suggested_tags
        assert "Python Guide" in result.suggested_aliases
        assert "comprehensive guide" in result.suggested_description
        assert result.confidence_scores["tags"] == 0.8

    def test_summarize_content_empty(self):
        """Test content summarization with empty content."""
        result = self.llm_service.summarize_content("")

        assert result == ""

    @patch.object(OpenAICompatibleLLMService, "_generate_completion")
    def test_summarize_content_success(self, mock_generate):
        """Test successful content summarization."""
        mock_generate.return_value = "This is a concise summary of the content."

        result = self.llm_service.summarize_content(
            "Long content to summarize", max_length=100
        )

        assert result == "This is a concise summary of the content."
        mock_generate.assert_called_once()

    @patch.object(OpenAICompatibleLLMService, "_generate_completion")
    def test_summarize_content_truncation(self, mock_generate):
        """Test content summarization with truncation."""
        long_response = "This is a very long summary that exceeds the maximum length limit and should be truncated appropriately."
        mock_generate.return_value = long_response

        result = self.llm_service.summarize_content("Content", max_length=50)

        # Should be truncated at sentence boundary or with ellipsis
        assert len(result) <= 53  # 50 + "..."
        assert result.endswith("...") or result.endswith(".")

    def test_analyze_relationship_empty_content(self):
        """Test relationship analysis with empty content."""
        result = self.llm_service.analyze_relationship("", "content")

        assert isinstance(result, RelationshipAnalysis)
        assert result.relationship_type == "UNRELATED"
        assert result.confidence == 0.0
        assert "empty" in result.explanation.lower()

    @patch.object(OpenAICompatibleLLMService, "_generate_completion")
    def test_analyze_relationship_success(self, mock_generate):
        """Test successful relationship analysis."""
        mock_generate.return_value = """RELATIONSHIP: ELABORATION CONFIDENCE: 0.8 BIDIRECTIONAL: true EXPLANATION: Content B provides detailed explanation of concepts mentioned in Content A."""

        result = self.llm_service.analyze_relationship(
            "Basic concept", "Detailed explanation"
        )

        assert isinstance(result, RelationshipAnalysis)
        assert result.relationship_type == "ELABORATION"
        assert result.confidence == 0.8
        assert result.bidirectional is True
        assert "detailed explanation" in result.explanation

    def test_evaluate_context_match_empty_input(self):
        """Test context match evaluation with empty input."""
        result = self.llm_service.evaluate_context_match("", "context", "target")

        assert isinstance(result, SimilarityResult)
        assert result.score == 0.0
        assert result.confidence == 0.0
        assert result.context_match is False

    @patch.object(OpenAICompatibleLLMService, "_generate_completion")
    def test_evaluate_context_match_success(self, mock_generate):
        """Test successful context match evaluation."""
        mock_generate.return_value = "SCORE: 0.85 CONFIDENCE: 0.9 MATCH: true REASONING: Strong semantic alignment between candidate and target."

        result = self.llm_service.evaluate_context_match(
            "candidate", "source context", "target content"
        )

        assert isinstance(result, SimilarityResult)
        assert result.score == 0.85
        assert result.confidence == 0.9
        assert result.context_match is True

    def test_disambiguate_targets_empty_input(self):
        """Test target disambiguation with empty input."""
        result = self.llm_service.disambiguate_targets("", "context", [])

        assert result == []

    @patch.object(OpenAICompatibleLLMService, "_generate_completion")
    def test_disambiguate_targets_success(self, mock_generate):
        """Test successful target disambiguation."""
        mock_generate.return_value = "TARGET_1: 0.9 TARGET_2: 0.6 TARGET_3: 0.3"

        target_options = [
            ("target1", "content1"),
            ("target2", "content2"),
            ("target3", "content3"),
        ]

        result = self.llm_service.disambiguate_targets(
            "candidate", "context", target_options
        )

        assert len(result) == 3
        assert result[0] == ("target1", 0.9)  # Highest score first
        assert result[1] == ("target2", 0.6)
        assert result[2] == ("target3", 0.3)

    @patch("knowledge_base_organizer.infrastructure.openai_compatible_llm.requests")
    def test_get_model_info_success(self, mock_requests):
        """Test successful model info retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"id": "local-model", "object": "model", "created": 1234567890}]
        }
        mock_requests.get.return_value = mock_response

        model_info = self.llm_service.get_model_info()

        assert model_info["model_name"] == "local-model"
        assert model_info["base_url"] == "http://localhost:1234"
        assert model_info["api_format"] == "openai"
        assert "capabilities" in model_info
        assert "concept_extraction" in model_info["capabilities"]

    @patch("knowledge_base_organizer.infrastructure.openai_compatible_llm.requests")
    def test_get_model_info_failure(self, mock_requests):
        """Test model info retrieval failure."""
        mock_requests.get.side_effect = requests.exceptions.RequestException(
            "Request failed"
        )

        model_info = self.llm_service.get_model_info()

        assert model_info["model_name"] == "local-model"
        assert "error" in model_info
        assert "capabilities" in model_info
        assert model_info["capabilities"] == ["basic_generation"]

    def test_extract_section_single_value(self):
        """Test extracting single value from structured response."""
        text = (
            "TAGS: python, programming DESCRIPTION: A Python tutorial CONFIDENCE: 0.8"
        )

        description = self.llm_service._extract_section(
            text, "DESCRIPTION", single_value=True
        )
        assert description == "A Python tutorial"

        confidence = self.llm_service._extract_section(
            text, "CONFIDENCE", single_value=True
        )
        assert confidence == "0.8"

    def test_extract_section_list_value(self):
        """Test extracting list value from structured response."""
        text = "TAGS: python, programming, tutorial ALIASES: Python Guide, Programming Tutorial"

        tags = self.llm_service._extract_section(text, "TAGS")
        assert tags == ["python", "programming", "tutorial"]

        aliases = self.llm_service._extract_section(text, "ALIASES")
        assert aliases == ["Python Guide", "Programming Tutorial"]

    def test_extract_section_not_found(self):
        """Test extracting section that doesn't exist."""
        text = "TAGS: python, programming"

        description = self.llm_service._extract_section(
            text, "DESCRIPTION", single_value=True
        )
        assert description is None

        aliases = self.llm_service._extract_section(text, "ALIASES")
        assert aliases == []

    def test_calculate_concept_confidence(self):
        """Test concept confidence calculation."""
        content = "This is about Python programming and machine learning algorithms."

        # Concept that appears in content
        confidence1 = self.llm_service._calculate_concept_confidence("Python", content)
        assert confidence1 > 0.5

        # Concept that doesn't appear in content
        confidence2 = self.llm_service._calculate_concept_confidence("Java", content)
        assert confidence2 == 0.6  # Base confidence

        # Long, specific concept
        confidence3 = self.llm_service._calculate_concept_confidence(
            "machine_learning_algorithm", content
        )
        assert confidence3 > 0.5  # Gets boost for length and underscores

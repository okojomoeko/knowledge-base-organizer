"""
Tests for OllamaEmbeddingService

These tests verify the Ollama embedding service implementation.
Note: These tests require a running Ollama instance with nomic-embed-text model.
"""

from unittest.mock import Mock, patch

import pytest
import requests

from knowledge_base_organizer.domain.services.ai_services import (
    EmbeddingError,
    EmbeddingResult,
    ModelNotAvailableError,
    SimilarityResult,
)
from knowledge_base_organizer.infrastructure.ollama_embedding import (
    OllamaEmbeddingService,
)


class TestOllamaEmbeddingService:
    """Test cases for OllamaEmbeddingService"""

    def test_init_with_defaults(self):
        """Test initialization with default parameters"""
        with patch.object(OllamaEmbeddingService, "_verify_service_availability"):
            service = OllamaEmbeddingService()
            assert service.base_url == "http://localhost:11434"
            assert service.model_name == "nomic-embed-text"
            assert service.timeout == 30

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters"""
        with patch.object(OllamaEmbeddingService, "_verify_service_availability"):
            service = OllamaEmbeddingService(
                base_url="http://custom:8080",
                model_name="custom-model",
                timeout=60,
            )
            assert service.base_url == "http://custom:8080"
            assert service.model_name == "custom-model"
            assert service.timeout == 60

    @patch("requests.get")
    def test_verify_service_availability_success(self, mock_get):
        """Test successful service availability verification"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "models": [{"name": "nomic-embed-text"}, {"name": "other-model"}]
        }
        mock_get.return_value = mock_response

        # Should not raise an exception
        service = OllamaEmbeddingService()
        assert service.model_name == "nomic-embed-text"

    @patch("requests.get")
    def test_verify_service_availability_service_down(self, mock_get):
        """Test service availability when Ollama is not running"""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

        with pytest.raises(
            ModelNotAvailableError, match="Ollama service not available"
        ):
            OllamaEmbeddingService()

    @patch("requests.post")
    @patch("requests.get")
    def test_verify_service_availability_model_missing(self, mock_get, mock_post):
        """Test service availability when model is missing but can be pulled"""
        # Mock the tags response (model not available)
        mock_get_response = Mock()
        mock_get_response.raise_for_status.return_value = None
        mock_get_response.json.return_value = {"models": [{"name": "other-model"}]}
        mock_get.return_value = mock_get_response

        # Mock the pull response (successful)
        mock_post_response = Mock()
        mock_post_response.raise_for_status.return_value = None
        mock_post.return_value = mock_post_response

        # Should successfully pull the model
        service = OllamaEmbeddingService()
        assert service.model_name == "nomic-embed-text"
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_create_embedding_success(self, mock_post):
        """Test successful embedding creation"""
        with patch.object(OllamaEmbeddingService, "_verify_service_availability"):
            service = OllamaEmbeddingService()

        # Mock successful embedding response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"embedding": [0.1, 0.2, 0.3, 0.4, 0.5]}
        mock_post.return_value = mock_response

        result = service.create_embedding("test text")

        assert isinstance(result, EmbeddingResult)
        assert result.vector == [0.1, 0.2, 0.3, 0.4, 0.5]
        assert result.dimension == 5
        assert result.model_name == "nomic-embed-text"

    @patch("requests.post")
    def test_create_embedding_empty_text(self, mock_post):
        """Test embedding creation with empty text"""
        with patch.object(OllamaEmbeddingService, "_verify_service_availability"):
            service = OllamaEmbeddingService()

        with pytest.raises(
            EmbeddingError, match="Cannot create embedding for empty text"
        ):
            service.create_embedding("")

    @patch("requests.post")
    def test_create_embedding_request_failure(self, mock_post):
        """Test embedding creation when request fails"""
        with patch.object(OllamaEmbeddingService, "_verify_service_availability"):
            service = OllamaEmbeddingService()

        mock_post.side_effect = requests.exceptions.RequestException("Network error")

        with pytest.raises(EmbeddingError, match="Failed to generate embedding"):
            service.create_embedding("test text")

    @patch("requests.post")
    def test_create_embedding_invalid_response(self, mock_post):
        """Test embedding creation with invalid response"""
        with patch.object(OllamaEmbeddingService, "_verify_service_availability"):
            service = OllamaEmbeddingService()

        # Mock response without embedding field
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"error": "Model not found"}
        mock_post.return_value = mock_response

        with pytest.raises(EmbeddingError, match="No embedding vector returned"):
            service.create_embedding("test text")

    def test_calculate_similarity_success(self):
        """Test successful similarity calculation"""
        with patch.object(OllamaEmbeddingService, "_verify_service_availability"):
            service = OllamaEmbeddingService()

        # Mock create_embedding to return predictable vectors
        embedding1 = EmbeddingResult(
            vector=[1.0, 0.0, 0.0], dimension=3, model_name="test"
        )
        embedding2 = EmbeddingResult(
            vector=[0.0, 1.0, 0.0], dimension=3, model_name="test"
        )

        with patch.object(service, "create_embedding") as mock_create:
            mock_create.side_effect = [embedding1, embedding2]

            result = service.calculate_similarity("text1", "text2")

            assert isinstance(result, SimilarityResult)
            assert result.score == 0.0  # Orthogonal vectors
            assert 0.0 <= result.confidence <= 1.0
            assert not result.context_match  # Low similarity

    def test_cosine_similarity_identical_vectors(self):
        """Test cosine similarity with identical vectors"""
        with patch.object(OllamaEmbeddingService, "_verify_service_availability"):
            service = OllamaEmbeddingService()

        vector = [1.0, 2.0, 3.0]
        similarity = service._cosine_similarity(vector, vector)
        assert abs(similarity - 1.0) < 1e-10  # Should be exactly 1.0

    def test_cosine_similarity_orthogonal_vectors(self):
        """Test cosine similarity with orthogonal vectors"""
        with patch.object(OllamaEmbeddingService, "_verify_service_availability"):
            service = OllamaEmbeddingService()

        vector1 = [1.0, 0.0, 0.0]
        vector2 = [0.0, 1.0, 0.0]
        similarity = service._cosine_similarity(vector1, vector2)
        assert abs(similarity - 0.0) < 1e-10  # Should be exactly 0.0

    def test_cosine_similarity_different_dimensions(self):
        """Test cosine similarity with vectors of different dimensions"""
        with patch.object(OllamaEmbeddingService, "_verify_service_availability"):
            service = OllamaEmbeddingService()

        vector1 = [1.0, 0.0]
        vector2 = [0.0, 1.0, 0.0]

        with pytest.raises(
            EmbeddingError, match="Vectors must have the same dimension"
        ):
            service._cosine_similarity(vector1, vector2)

    def test_calculate_confidence(self):
        """Test confidence calculation"""
        with patch.object(OllamaEmbeddingService, "_verify_service_availability"):
            service = OllamaEmbeddingService()

        # High similarity, high dimension should give high confidence
        confidence_high = service._calculate_confidence(0.9, 1000)
        assert confidence_high > 0.8

        # Low similarity, low dimension should give lower confidence
        confidence_low = service._calculate_confidence(0.1, 100)
        assert confidence_low < confidence_high

        # Confidence should be between 0 and 1
        assert 0.0 <= confidence_high <= 1.0
        assert 0.0 <= confidence_low <= 1.0

    @patch("requests.post")
    def test_get_model_info_success(self, mock_post):
        """Test successful model info retrieval"""
        with patch.object(OllamaEmbeddingService, "_verify_service_availability"):
            service = OllamaEmbeddingService()

        # Mock show response
        mock_show_response = Mock()
        mock_show_response.raise_for_status.return_value = None
        mock_show_response.json.return_value = {
            "details": {"family": "nomic-embed"},
            "parameters": {"embedding_length": 768},
        }

        # Mock embedding response for dimension detection
        mock_embed_response = Mock()
        mock_embed_response.raise_for_status.return_value = None
        mock_embed_response.json.return_value = {"embedding": [0.1] * 768}

        mock_post.side_effect = [mock_show_response, mock_embed_response]

        info = service.get_model_info()

        assert info["model_name"] == "nomic-embed-text"
        assert info["dimension"] == 768
        assert info["base_url"] == "http://localhost:11434"
        assert "model_details" in info
        assert "parameters" in info

    @patch("requests.post")
    def test_get_model_info_failure(self, mock_post):
        """Test model info retrieval when request fails"""
        with patch.object(OllamaEmbeddingService, "_verify_service_availability"):
            service = OllamaEmbeddingService()

        mock_post.side_effect = requests.exceptions.RequestException("Network error")

        info = service.get_model_info()

        assert info["model_name"] == "nomic-embed-text"
        assert info["dimension"] == "unknown"
        assert "error" in info

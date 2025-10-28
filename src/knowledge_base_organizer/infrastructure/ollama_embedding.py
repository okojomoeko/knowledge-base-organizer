"""
Ollama Embedding Service Implementation

This module provides an implementation of the EmbeddingService interface
using Ollama's nomic-embed-text model for generating vector embeddings.

Supports:
- Requirement 13.1, 13.2: Context-aware linking with semantic similarity
- Vector embedding generation for semantic analysis
- Similarity calculation between text content
"""

import json
import logging
from typing import Any

import requests

from knowledge_base_organizer.domain.services.ai_services import (
    EmbeddingError,
    EmbeddingResult,
    EmbeddingService,
    ModelNotAvailableError,
    SimilarityResult,
)

logger = logging.getLogger(__name__)


class OllamaEmbeddingService(EmbeddingService):
    """
    Ollama-based embedding service using nomic-embed-text model.

    This service connects to a local Ollama instance to generate
    vector embeddings for semantic analysis and similarity calculations.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model_name: str = "nomic-embed-text",
        timeout: int = 30,
    ):
        """
        Initialize the Ollama embedding service.

        Args:
            base_url: Base URL for Ollama API (default: http://localhost:11434)
            model_name: Name of the embedding model (default: nomic-embed-text)
            timeout: Request timeout in seconds (default: 30)
        """
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout
        self._model_info: dict[str, Any] | None = None

        # Verify Ollama is available and model is accessible
        self._verify_service_availability()

    def _verify_service_availability(self) -> None:
        """
        Verify that Ollama service is running and the model is available.

        Raises:
            ModelNotAvailableError: If Ollama service or model is not available
        """
        try:
            # Check if Ollama service is running
            response = requests.get(f"{self.base_url}/api/tags", timeout=self.timeout)
            response.raise_for_status()

            # Check if the embedding model is available
            models_data = response.json()
            available_models = [
                model["name"] for model in models_data.get("models", [])
            ]

            if self.model_name not in available_models:
                logger.warning(
                    f"Model {self.model_name} not found in available models: "
                    f"{available_models}"
                )
                # Try to pull the model
                self._pull_model()

        except requests.exceptions.RequestException as e:
            raise ModelNotAvailableError(
                f"Ollama service not available at {self.base_url}: {e}"
            ) from e

    def _pull_model(self) -> None:
        """
        Attempt to pull the embedding model if it's not available.

        Raises:
            ModelNotAvailableError: If model cannot be pulled
        """
        try:
            logger.info(f"Attempting to pull model: {self.model_name}")
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": self.model_name},
                timeout=300,  # Longer timeout for model pulling
            )
            response.raise_for_status()
            logger.info(f"Successfully pulled model: {self.model_name}")

        except requests.exceptions.RequestException as e:
            raise ModelNotAvailableError(
                f"Failed to pull model {self.model_name}: {e}"
            ) from e

    def create_embedding(self, text: str) -> EmbeddingResult:
        """
        Generate a vector embedding for the given text using Ollama.

        Args:
            text: Input text to embed

        Returns:
            EmbeddingResult containing the vector and metadata

        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not text.strip():
            raise EmbeddingError("Cannot create embedding for empty text")

        try:
            # Call Ollama embeddings API
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.model_name,
                    "prompt": text,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()
            embedding_vector = data.get("embedding")

            if not embedding_vector:
                raise EmbeddingError("No embedding vector returned from Ollama")

            return EmbeddingResult(
                vector=embedding_vector,
                dimension=len(embedding_vector),
                model_name=self.model_name,
            )

        except requests.exceptions.RequestException as e:
            raise EmbeddingError(f"Failed to generate embedding: {e}") from e
        except (KeyError, json.JSONDecodeError) as e:
            raise EmbeddingError(f"Invalid response from Ollama: {e}") from e

    def calculate_similarity(self, text1: str, text2: str) -> SimilarityResult:
        """
        Calculate semantic similarity between two texts using cosine similarity.

        Args:
            text1: First text for comparison
            text2: Second text for comparison

        Returns:
            SimilarityResult with score and confidence
        """
        try:
            # Generate embeddings for both texts
            embedding1 = self.create_embedding(text1)
            embedding2 = self.create_embedding(text2)

            # Calculate cosine similarity
            similarity_score = self._cosine_similarity(
                embedding1.vector, embedding2.vector
            )

            # Determine confidence based on vector dimensions and similarity
            confidence = self._calculate_confidence(
                similarity_score, embedding1.dimension
            )

            # Context match is true if similarity is above a reasonable threshold
            context_match = similarity_score > 0.7

            return SimilarityResult(
                score=similarity_score,
                confidence=confidence,
                context_match=context_match,
            )

        except EmbeddingError:
            # Re-raise embedding errors
            raise
        except Exception as e:
            raise EmbeddingError(f"Failed to calculate similarity: {e}") from e

    def _cosine_similarity(self, vector1: list[float], vector2: list[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vector1: First vector
            vector2: Second vector

        Returns:
            Cosine similarity score between -1 and 1
        """
        if len(vector1) != len(vector2):
            raise EmbeddingError("Vectors must have the same dimension")

        # Calculate dot product
        dot_product: float = sum(a * b for a, b in zip(vector1, vector2, strict=False))

        # Calculate magnitudes
        magnitude1: float = sum(a * a for a in vector1) ** 0.5
        magnitude2: float = sum(b * b for b in vector2) ** 0.5

        # Avoid division by zero
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return float(dot_product / (magnitude1 * magnitude2))

    def _calculate_confidence(self, similarity_score: float, dimension: int) -> float:
        """
        Calculate confidence score based on similarity and vector dimension.

        Higher dimensional vectors and more extreme similarity scores
        generally indicate higher confidence.

        Args:
            similarity_score: Cosine similarity score
            dimension: Vector dimension

        Returns:
            Confidence score between 0 and 1
        """
        # Base confidence from similarity score (absolute value for extremes)
        similarity_confidence = abs(similarity_score)

        # Dimension confidence (higher dimensions are more reliable)
        # Normalize based on typical embedding dimensions (256-1536)
        dimension_confidence = min(1.0, dimension / 1000.0)

        # Combine confidences with weighted average
        confidence = (0.8 * similarity_confidence) + (0.2 * dimension_confidence)

        return min(1.0, confidence)

    def get_model_info(self) -> dict[str, Any]:
        """
        Get information about the embedding model.

        Returns:
            Dictionary with model name, dimension, and other metadata
        """
        if self._model_info is None:
            try:
                # Get model information from Ollama
                response = requests.post(
                    f"{self.base_url}/api/show",
                    json={"name": self.model_name},
                    timeout=self.timeout,
                )
                response.raise_for_status()

                model_data = response.json()

                # Create a test embedding to determine dimension
                test_embedding = self.create_embedding("test")

                self._model_info = {
                    "model_name": self.model_name,
                    "dimension": test_embedding.dimension,
                    "base_url": self.base_url,
                    "model_details": model_data.get("details", {}),
                    "parameters": model_data.get("parameters", {}),
                }

            except (requests.exceptions.RequestException, EmbeddingError) as e:
                logger.warning(f"Could not retrieve model info: {e}")
                self._model_info = {
                    "model_name": self.model_name,
                    "dimension": "unknown",
                    "base_url": self.base_url,
                    "error": str(e),
                }

        return self._model_info.copy()

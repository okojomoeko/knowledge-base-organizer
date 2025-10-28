"""
AI Services Domain Interfaces

This module defines the abstract base classes for AI-powered services that enable
semantic analysis, vector storage, and LLM-based reasoning capabilities.

These interfaces support:
- Requirement 13.1, 13.2: Context-aware linking with semantic similarity
- Requirement 17.1: Intelligent frontmatter auto-enhancement
- Requirement 23.1: Concept-based automatic tagging and alias generation
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class EmbeddingResult:
    """Result of text embedding generation"""

    vector: list[float]
    dimension: int
    model_name: str


@dataclass
class SimilarityResult:
    """Result of semantic similarity calculation"""

    score: float
    confidence: float
    context_match: bool


@dataclass
class SearchResult:
    """Result from vector search"""

    document_id: str
    similarity_score: float
    metadata: dict[str, Any]


@dataclass
class ConceptExtractionResult:
    """Result of concept extraction from content"""

    concepts: list[str]
    confidence_scores: list[float]
    context: str


@dataclass
class MetadataSuggestion:
    """AI-generated metadata suggestions"""

    suggested_tags: list[str]
    suggested_aliases: list[str]
    suggested_description: str | None
    confidence_scores: dict[str, float]


@dataclass
class RelationshipAnalysis:
    """Analysis of logical relationships between content"""

    relationship_type: str  # PREMISE, EXAMPLE, CONTRADICTION, DETAIL, ELABORATION
    confidence: float
    explanation: str
    bidirectional: bool


class EmbeddingService(ABC):
    """
    Service for generating vector embeddings from text content.

    Supports semantic similarity analysis for context-aware linking
    and content-based relationship discovery.
    """

    @abstractmethod
    def create_embedding(self, text: str) -> EmbeddingResult:
        """
        Generate a vector embedding for the given text.

        Args:
            text: Input text to embed

        Returns:
            EmbeddingResult containing the vector and metadata

        Raises:
            EmbeddingError: If embedding generation fails
        """

    @abstractmethod
    def calculate_similarity(self, text1: str, text2: str) -> SimilarityResult:
        """
        Calculate semantic similarity between two texts.

        Args:
            text1: First text for comparison
            text2: Second text for comparison

        Returns:
            SimilarityResult with score and confidence
        """

    @abstractmethod
    def get_model_info(self) -> dict[str, Any]:
        """
        Get information about the embedding model.

        Returns:
            Dictionary with model name, dimension, and other metadata
        """


class VectorStore(ABC):
    """
    Service for storing and searching vector embeddings.

    Provides efficient similarity search capabilities for semantic
    content discovery and relationship analysis.
    """

    @abstractmethod
    def index_document(
        self,
        document_id: str,
        vector: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Index a document vector with optional metadata.

        Args:
            document_id: Unique identifier for the document
            vector: Document embedding vector
            metadata: Optional metadata to store with the vector
        """

    @abstractmethod
    def search(
        self, query_vector: list[float], k: int = 10, threshold: float | None = None
    ) -> list[SearchResult]:
        """
        Search for similar documents using vector similarity.

        Args:
            query_vector: Query embedding vector
            k: Number of results to return
            threshold: Minimum similarity threshold

        Returns:
            List of SearchResult objects ordered by similarity
        """

    @abstractmethod
    def get_document_vector(self, document_id: str) -> list[float] | None:
        """
        Retrieve the vector for a specific document.

        Args:
            document_id: Document identifier

        Returns:
            Document vector or None if not found
        """

    @abstractmethod
    def remove_document(self, document_id: str) -> bool:
        """
        Remove a document from the index.

        Args:
            document_id: Document identifier to remove

        Returns:
            True if document was removed, False if not found
        """

    @abstractmethod
    def save_index(self, path: Path) -> None:
        """
        Save the vector index to disk.

        Args:
            path: Path where to save the index
        """

    @abstractmethod
    def load_index(self, path: Path) -> None:
        """
        Load a vector index from disk.

        Args:
            path: Path to the saved index
        """

    @abstractmethod
    def get_index_stats(self) -> dict[str, Any]:
        """
        Get statistics about the current index.

        Returns:
            Dictionary with index size, dimension, and other stats
        """


class LLMService(ABC):
    """
    Service for Large Language Model inference and reasoning.

    Provides AI-powered content analysis, metadata generation,
    and logical relationship discovery capabilities.
    """

    @abstractmethod
    def extract_concepts(self, content: str) -> ConceptExtractionResult:
        """
        Extract core concepts from content for tagging and categorization.

        Supports Requirement 23.1: Concept-based automatic tagging.

        Args:
            content: Text content to analyze

        Returns:
            ConceptExtractionResult with extracted concepts and confidence scores
        """

    @abstractmethod
    def suggest_metadata(
        self, content: str, existing_metadata: dict[str, Any] | None = None
    ) -> MetadataSuggestion:
        """
        Generate intelligent metadata suggestions for frontmatter enhancement.

        Supports Requirement 17.1: Intelligent frontmatter auto-enhancement.

        Args:
            content: Note content to analyze
            existing_metadata: Current frontmatter metadata

        Returns:
            MetadataSuggestion with tags, aliases, and description
        """

    @abstractmethod
    def summarize_content(self, content: str, max_length: int = 100) -> str:
        """
        Generate a concise summary of the content.

        Args:
            content: Text content to summarize
            max_length: Maximum length of summary in characters

        Returns:
            Generated summary text
        """

    @abstractmethod
    def analyze_relationship(
        self, content_a: str, content_b: str
    ) -> RelationshipAnalysis:
        """
        Analyze logical relationships between two pieces of content.

        Supports Requirement 24: Logical relationship identification.

        Args:
            content_a: First content for comparison
            content_b: Second content for comparison

        Returns:
            RelationshipAnalysis with relationship type and confidence
        """

    @abstractmethod
    def evaluate_context_match(
        self, candidate_text: str, source_context: str, target_content: str
    ) -> SimilarityResult:
        """
        Evaluate if a link candidate matches the context appropriately.

        Supports Requirement 13.1, 13.2: Context-aware linking.

        Args:
            candidate_text: Text that could become a link
            source_context: Surrounding context in source document
            target_content: Content of potential target document

        Returns:
            SimilarityResult indicating context match quality
        """

    @abstractmethod
    def disambiguate_targets(
        self,
        candidate_text: str,
        source_context: str,
        target_options: list[tuple[str, str]],
    ) -> list[tuple[str, float]]:
        """
        Rank multiple potential link targets by contextual relevance.

        Supports Requirement 14: Link disambiguation.

        Args:
            candidate_text: Text that could become a link
            source_context: Context around the candidate text
            target_options: List of (target_id, target_content) tuples

        Returns:
            List of (target_id, confidence_score) tuples, ranked by relevance
        """

    @abstractmethod
    def get_model_info(self) -> dict[str, Any]:
        """
        Get information about the LLM model.

        Returns:
            Dictionary with model name, capabilities, and configuration
        """


class AIServiceError(Exception):
    """Base exception for AI service operations"""


class EmbeddingError(AIServiceError):
    """Raised when embedding generation fails"""


class VectorStoreError(AIServiceError):
    """Raised when vector store operations fail"""


class LLMError(AIServiceError):
    """Raised when LLM inference fails"""


class ModelNotAvailableError(AIServiceError):
    """Raised when required AI model is not available"""

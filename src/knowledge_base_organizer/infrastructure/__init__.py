"""Infrastructure layer for knowledge base organizer."""

from knowledge_base_organizer.infrastructure.faiss_vector_store import FaissVectorStore
from knowledge_base_organizer.infrastructure.ollama_embedding import (
    OllamaEmbeddingService,
)

__all__ = ["FaissVectorStore", "OllamaEmbeddingService"]

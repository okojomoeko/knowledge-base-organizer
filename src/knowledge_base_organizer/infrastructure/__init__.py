"""Infrastructure layer for knowledge base organizer."""

from knowledge_base_organizer.infrastructure.di_container import (
    AIServiceConfig,
    DIContainer,
    create_di_container,
)
from knowledge_base_organizer.infrastructure.faiss_vector_store import FaissVectorStore
from knowledge_base_organizer.infrastructure.ollama_embedding import (
    OllamaEmbeddingService,
)
from knowledge_base_organizer.infrastructure.ollama_llm import OllamaLLMService

__all__ = [
    "AIServiceConfig",
    "DIContainer",
    "FaissVectorStore",
    "OllamaEmbeddingService",
    "OllamaLLMService",
    "create_di_container",
]

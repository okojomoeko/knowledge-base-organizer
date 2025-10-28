"""
Dependency Injection Container for AI Services

This module provides a DI container that manages the creation and injection
of AI service implementations (Ollama/Faiss) into use cases.

Supports configuration-driven service selection and lifecycle management.
"""

from pathlib import Path
from typing import Any, Protocol

import yaml

from knowledge_base_organizer.domain.services.ai_services import (
    EmbeddingService,
    LLMService,
    VectorStore,
)
from knowledge_base_organizer.infrastructure.config import ProcessingConfig


class ServiceFactory(Protocol):
    """Protocol for service factory functions"""

    def __call__(self, config: dict[str, Any]) -> Any:
        """Create a service instance with the given configuration"""


class DIContainer:
    """
    Dependency Injection Container for AI Services

    Manages the creation and lifecycle of AI service implementations
    based on configuration settings.
    """

    def __init__(self, config: ProcessingConfig, vault_path: Path):
        """
        Initialize the DI container.

        Args:
            config: Processing configuration
            vault_path: Path to the vault (for index storage)
        """
        self.config = config
        self.vault_path = vault_path
        self._services: dict[str, Any] = {}
        self._factories: dict[str, ServiceFactory] = {}

        # Register default factories
        self._register_default_factories()

    def _register_default_factories(self) -> None:
        """Register default service factories"""
        # Embedding service factories
        self._factories["ollama_embedding"] = self._create_ollama_embedding

        # Vector store factories
        self._factories["faiss_vector_store"] = self._create_faiss_vector_store

        # LLM service factories
        self._factories["ollama_llm"] = self._create_ollama_llm

    def _create_ollama_embedding(self, config: dict[str, Any]) -> EmbeddingService:
        """Create Ollama embedding service"""
        # Import here to avoid circular imports
        from knowledge_base_organizer.infrastructure.ollama_embedding import (
            OllamaEmbeddingService,
        )

        return OllamaEmbeddingService(
            base_url=config.get("base_url", "http://localhost:11434"),
            model_name=config.get("model_name", "nomic-embed-text"),
            timeout=config.get("timeout", 30.0),
        )

    def _create_faiss_vector_store(self, config: dict[str, Any]) -> VectorStore:
        """Create FAISS vector store"""
        # Import here to avoid circular imports
        from knowledge_base_organizer.infrastructure.faiss_vector_store import (
            FaissVectorStore,
        )

        index_path = self.vault_path / ".kbo_index" / "vault.index"
        return FaissVectorStore(
            dimension=config.get("dimension", 768),
            index_path=index_path,
            metric=config.get("metric", "cosine"),
        )

    def _create_ollama_llm(self, config: dict[str, Any]) -> LLMService:
        """Create Ollama LLM service"""
        # Import here to avoid circular imports
        from knowledge_base_organizer.infrastructure.ollama_llm import OllamaLLMService

        return OllamaLLMService(
            base_url=config.get("base_url", "http://localhost:11434"),
            model_name=config.get("model_name", "llama3.2:3b"),
            timeout=config.get("timeout", 60.0),
            temperature=config.get("temperature", 0.1),
        )

    def register_factory(self, service_type: str, factory: ServiceFactory) -> None:
        """
        Register a custom service factory.

        Args:
            service_type: Type identifier for the service
            factory: Factory function to create the service
        """
        self._factories[service_type] = factory

    def get_embedding_service(
        self, service_type: str = "ollama_embedding", **kwargs: Any
    ) -> EmbeddingService:
        """
        Get or create an embedding service instance.

        Args:
            service_type: Type of embedding service to create
            **kwargs: Additional configuration parameters

        Returns:
            EmbeddingService instance

        Raises:
            ValueError: If service type is not registered
        """
        cache_key = f"embedding_{service_type}"

        if cache_key not in self._services:
            if service_type not in self._factories:
                raise ValueError(f"Unknown embedding service type: {service_type}")

            factory = self._factories[service_type]
            self._services[cache_key] = factory(kwargs)

        return self._services[cache_key]

    def get_vector_store(
        self, service_type: str = "faiss_vector_store", **kwargs: Any
    ) -> VectorStore:
        """
        Get or create a vector store instance.

        Args:
            service_type: Type of vector store to create
            **kwargs: Additional configuration parameters

        Returns:
            VectorStore instance

        Raises:
            ValueError: If service type is not registered
        """
        cache_key = f"vector_store_{service_type}"

        if cache_key not in self._services:
            if service_type not in self._factories:
                raise ValueError(f"Unknown vector store type: {service_type}")

            factory = self._factories[service_type]
            self._services[cache_key] = factory(kwargs)

        return self._services[cache_key]

    def get_llm_service(
        self, service_type: str = "ollama_llm", **kwargs: Any
    ) -> LLMService:
        """
        Get or create an LLM service instance.

        Args:
            service_type: Type of LLM service to create
            **kwargs: Additional configuration parameters

        Returns:
            LLMService instance

        Raises:
            ValueError: If service type is not registered
        """
        cache_key = f"llm_{service_type}"

        if cache_key not in self._services:
            if service_type not in self._factories:
                raise ValueError(f"Unknown LLM service type: {service_type}")

            factory = self._factories[service_type]
            self._services[cache_key] = factory(kwargs)

        return self._services[cache_key]

    def clear_cache(self) -> None:
        """Clear all cached service instances"""
        self._services.clear()

    def get_service_info(self) -> dict[str, Any]:
        """
        Get information about registered services and factories.

        Returns:
            Dictionary with service type information
        """
        return {
            "registered_factories": list(self._factories.keys()),
            "cached_services": list(self._services.keys()),
            "vault_path": str(self.vault_path),
        }


class AIServiceConfig:
    """Configuration for AI services"""

    def __init__(self, config_dict: dict[str, Any] | None = None):
        """
        Initialize AI service configuration.

        Args:
            config_dict: Configuration dictionary
        """
        self.config = config_dict or {}

    @classmethod
    def from_file(cls, config_path: Path) -> "AIServiceConfig":
        """
        Load AI service configuration from file.

        Args:
            config_path: Path to configuration file

        Returns:
            AIServiceConfig instance
        """
        if not config_path.exists():
            return cls()

        with config_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return cls(data.get("ai_services", {}))

    @classmethod
    def get_default_config(cls) -> "AIServiceConfig":
        """
        Get default AI service configuration.

        Returns:
            Default AIServiceConfig
        """
        return cls(
            {
                "embedding": {
                    "type": "ollama_embedding",
                    "base_url": "http://localhost:11434",
                    "model_name": "nomic-embed-text",
                    "timeout": 30.0,
                },
                "vector_store": {
                    "type": "faiss_vector_store",
                    "dimension": 768,
                    "metric": "cosine",
                },
                "llm": {
                    "type": "ollama_llm",
                    "base_url": "http://localhost:11434",
                    "model_name": "llama3.2:3b",
                    "timeout": 60.0,
                    "temperature": 0.1,
                },
            }
        )

    def get_embedding_config(self) -> dict[str, Any]:
        """Get embedding service configuration"""
        return self.config.get("embedding", {})

    def get_vector_store_config(self) -> dict[str, Any]:
        """Get vector store configuration"""
        return self.config.get("vector_store", {})

    def get_llm_config(self) -> dict[str, Any]:
        """Get LLM service configuration"""
        return self.config.get("llm", {})


def create_di_container(
    vault_path: Path,
    config: ProcessingConfig | None = None,
    ai_config: AIServiceConfig | None = None,
) -> DIContainer:
    """
    Factory function to create a configured DI container.

    Args:
        vault_path: Path to the vault
        config: Processing configuration (optional)
        ai_config: AI service configuration (optional)

    Returns:
        Configured DIContainer instance
    """
    if config is None:
        config = ProcessingConfig.get_default_config()

    if ai_config is None:
        # Try to load from vault config directory
        config_path = vault_path / ".kiro" / "ai_config.yaml"
        ai_config = AIServiceConfig.from_file(config_path)

        # Don't fall back to default config automatically - let it be empty
        # This allows the container to be created without trying to connect to services

    container = DIContainer(config, vault_path)

    # Configure services based on ai_config (only if explicitly configured)
    embedding_config = ai_config.get_embedding_config()
    if embedding_config and "type" in embedding_config:
        embedding_type = embedding_config.pop("type", "ollama_embedding")
        # Pre-configure the embedding service
        container.get_embedding_service(embedding_type, **embedding_config)

    vector_store_config = ai_config.get_vector_store_config()
    if vector_store_config and "type" in vector_store_config:
        vector_store_type = vector_store_config.pop("type", "faiss_vector_store")
        # Pre-configure the vector store
        container.get_vector_store(vector_store_type, **vector_store_config)

    llm_config = ai_config.get_llm_config()
    if llm_config and "type" in llm_config:
        llm_type = llm_config.pop("type", "ollama_llm")
        # Pre-configure the LLM service
        container.get_llm_service(llm_type, **llm_config)

    return container

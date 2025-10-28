"""
Dependency Injection Setup for CLI Commands

This module provides helper functions to set up dependency injection
for CLI commands that need AI services.
"""

from pathlib import Path
from typing import Any

import yaml

from knowledge_base_organizer.domain.services.ai_services import (
    EmbeddingService,
    LLMService,
    VectorStore,
)
from knowledge_base_organizer.infrastructure.config import ProcessingConfig
from knowledge_base_organizer.infrastructure.di_container import (
    AIServiceConfig,
    DIContainer,
    create_di_container,
)


class CLIDependencies:
    """
    Container for CLI command dependencies including AI services.

    This class provides a convenient interface for CLI commands to access
    configured AI services without directly managing the DI container.
    """

    def __init__(self, container: DIContainer):
        """
        Initialize CLI dependencies.

        Args:
            container: Configured DI container
        """
        self.container = container
        self._embedding_service: EmbeddingService | None = None
        self._vector_store: VectorStore | None = None
        self._llm_service: LLMService | None = None

    @property
    def embedding_service(self) -> EmbeddingService:
        """Get the embedding service (lazy initialization)"""
        if self._embedding_service is None:
            self._embedding_service = self.container.get_embedding_service()
        return self._embedding_service

    @property
    def vector_store(self) -> VectorStore:
        """Get the vector store (lazy initialization)"""
        if self._vector_store is None:
            self._vector_store = self.container.get_vector_store()
        return self._vector_store

    @property
    def llm_service(self) -> LLMService:
        """Get the LLM service (lazy initialization)"""
        if self._llm_service is None:
            self._llm_service = self.container.get_llm_service()
        return self._llm_service

    def is_ai_available(self) -> bool:
        """
        Check if AI services are available and configured.

        Returns:
            True if AI services can be used, False otherwise
        """
        try:
            # Try to get model info to verify services are working
            self.embedding_service.get_model_info()
            self.llm_service.get_model_info()
            return True
        except Exception:
            return False

    def get_service_status(self) -> dict[str, Any]:
        """
        Get status information about AI services.

        Returns:
            Dictionary with service availability and configuration
        """
        status = {
            "ai_available": False,
            "embedding_service": {"available": False, "error": None},
            "vector_store": {"available": False, "error": None},
            "llm_service": {"available": False, "error": None},
        }

        # Check embedding service
        try:
            info = self.embedding_service.get_model_info()
            status["embedding_service"] = {
                "available": True,
                "model_info": info,
                "error": None,
            }
        except Exception as e:
            status["embedding_service"]["error"] = str(e)

        # Check vector store
        try:
            stats = self.vector_store.get_index_stats()
            status["vector_store"] = {
                "available": True,
                "index_stats": stats,
                "error": None,
            }
        except Exception as e:
            status["vector_store"]["error"] = str(e)

        # Check LLM service
        try:
            info = self.llm_service.get_model_info()
            status["llm_service"] = {
                "available": True,
                "model_info": info,
                "error": None,
            }
        except Exception as e:
            status["llm_service"]["error"] = str(e)

        # Overall availability
        status["ai_available"] = all(
            service["available"]
            for service in [
                status["embedding_service"],
                status["vector_store"],
                status["llm_service"],
            ]
        )

        return status


def setup_cli_dependencies(
    vault_path: Path,
    config: ProcessingConfig | None = None,
    ai_config_override: dict[str, Any] | None = None,
) -> CLIDependencies:
    """
    Set up dependencies for CLI commands.

    Args:
        vault_path: Path to the vault
        config: Processing configuration (optional)
        ai_config_override: Override AI configuration (optional)

    Returns:
        Configured CLIDependencies instance
    """
    # Load AI configuration
    ai_config = None
    if ai_config_override:
        ai_config = AIServiceConfig(ai_config_override)
    else:
        # Try to load from vault config
        config_path = vault_path / ".kiro" / "ai_config.yaml"
        ai_config = AIServiceConfig.from_file(config_path)

        # Fall back to default if no config found
        if not ai_config.config:
            ai_config = AIServiceConfig.get_default_config()

    # Create DI container
    container = create_di_container(vault_path, config, ai_config)

    return CLIDependencies(container)


def create_ai_config_file(
    vault_path: Path, config: dict[str, Any] | None = None
) -> Path:
    """
    Create an AI configuration file in the vault.

    Args:
        vault_path: Path to the vault
        config: Configuration to write (uses default if None)

    Returns:
        Path to the created configuration file
    """

    config_dir = vault_path / ".kiro"
    config_dir.mkdir(exist_ok=True)

    config_path = config_dir / "ai_config.yaml"

    if config is None:
        config = AIServiceConfig.get_default_config().config

    config_data = {"ai_services": config}

    with config_path.open("w", encoding="utf-8") as f:
        yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

    return config_path


def get_ai_config_template() -> dict[str, Any]:
    """
    Get a template AI configuration for documentation purposes.

    Returns:
        Template configuration dictionary
    """
    return {
        "ai_services": {
            "embedding": {
                "type": "ollama_embedding",
                "base_url": "http://localhost:11434",
                "model_name": "nomic-embed-text",
                "timeout": 30.0,
            },
            "vector_store": {
                "type": "faiss_vector_store",
                "dimension": 768,  # Must match embedding model dimension
                "metric": "cosine",  # cosine, euclidean, or inner_product
            },
            "llm": {
                "type": "ollama_llm",
                "base_url": "http://localhost:11434",
                "model_name": "llama3.2:3b",
                "timeout": 60.0,
                "temperature": 0.1,  # Lower = more deterministic
            },
        }
    }

"""
LLM Service Factory

This module provides a factory for creating LLM service instances
based on configuration, supporting multiple providers like Ollama,
LM Studio, and OpenAI-compatible APIs.
"""

import logging
from pathlib import Path

from knowledge_base_organizer.domain.services.ai_services import LLMService

from .llm_config import LLMConfigManager, LLMProviderConfig, get_llm_config_manager

logger = logging.getLogger(__name__)


class LLMServiceFactory:
    """Factory for creating LLM service instances based on configuration."""

    def __init__(self, config_manager: LLMConfigManager | None = None):
        """
        Initialize LLM service factory.

        Args:
            config_manager: Optional config manager. If None, uses global instance.
        """
        self.config_manager = config_manager or get_llm_config_manager()

    def create_llm_service(
        self, provider_name: str | None = None, model_name: str | None = None, **kwargs
    ) -> LLMService:
        """
        Create an LLM service instance.

        Args:
            provider_name: Name of the provider to use. If None, uses default.
            model_name: Name of the model to use. If None, uses provider default.
            **kwargs: Additional arguments to override configuration

        Returns:
            LLMService instance

        Raises:
            ValueError: If provider is not supported or configuration is invalid
            ImportError: If required dependencies are not available
        """
        # Get provider configuration
        provider_config = self.config_manager.get_provider_config(provider_name)

        # Override model name if specified
        if model_name:
            provider_config.model_name = model_name

        # Prepare service arguments
        service_kwargs = {
            "base_url": provider_config.base_url,
            "model_name": provider_config.model_name,
            "timeout": provider_config.timeout,
            **provider_config.options,
            **kwargs,  # Override with any provided kwargs
        }

        # Add API key for OpenAI-compatible services
        if provider_config.api_key:
            service_kwargs["api_key"] = provider_config.api_key

        # Create service based on API format
        api_format = provider_config.api_format.lower()

        if api_format == "ollama":
            return self._create_ollama_service(service_kwargs)
        if api_format == "openai":
            return self._create_openai_compatible_service(service_kwargs)
        raise ValueError(f"Unsupported API format: {api_format}")

    def _create_ollama_service(self, service_kwargs: dict) -> LLMService:
        """Create Ollama LLM service."""
        try:
            from .ollama_llm import OllamaLLMService

            # Remove api_key if present (not needed for Ollama)
            service_kwargs.pop("api_key", None)
            return OllamaLLMService(**service_kwargs)
        except ImportError as e:
            raise ImportError(f"Ollama service dependencies not available: {e}") from e

    def _create_openai_compatible_service(self, service_kwargs: dict) -> LLMService:
        """Create OpenAI-compatible LLM service."""
        try:
            from .openai_compatible_llm import OpenAICompatibleLLMService

            return OpenAICompatibleLLMService(**service_kwargs)
        except ImportError as e:
            raise ImportError(
                f"OpenAI-compatible service dependencies not available: {e}"
            ) from e

    def list_available_providers(self) -> list[str]:
        """Get list of available provider names."""
        return self.config_manager.list_available_providers()

    def list_available_models(self, provider_name: str | None = None) -> list[str]:
        """Get list of available models for a provider."""
        return self.config_manager.list_available_models(provider_name)

    def test_provider_connection(self, provider_name: str | None = None) -> bool:
        """
        Test connection to a provider.

        Args:
            provider_name: Name of the provider to test. If None, uses default.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            service = self.create_llm_service(provider_name)
            # Try to get model info as a connection test
            model_info = service.get_model_info()
            logger.info(f"Successfully connected to provider: {provider_name}")
            logger.debug(f"Model info: {model_info}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to provider {provider_name}: {e}")
            return False

    def get_provider_config(
        self, provider_name: str | None = None
    ) -> LLMProviderConfig:
        """
        Get provider configuration.

        Args:
            provider_name: Name of the provider. If None, uses default.

        Returns:
            Provider configuration

        Raises:
            ValueError: If provider is not configured
        """
        return self.config_manager.get_provider_config(provider_name)

    def list_providers(self) -> list[str]:
        """Get list of configured provider names."""
        return self.config_manager.list_available_providers()

    def get_default_provider(self) -> str:
        """Get the default provider name."""
        return self.config_manager.load_config().default_provider


# Global factory instance
_factory: LLMServiceFactory | None = None


def get_llm_service_factory(config_path: Path | None = None) -> LLMServiceFactory:
    """
    Get the global LLM service factory instance.

    Args:
        config_path: Optional path to config file (only used on first call)

    Returns:
        LLMServiceFactory instance
    """
    global _factory

    if _factory is None:
        config_manager = get_llm_config_manager(config_path)
        _factory = LLMServiceFactory(config_manager)

    return _factory


def create_llm_service(
    provider_name: str | None = None,
    model_name: str | None = None,
    config_path: Path | None = None,
    **kwargs,
) -> LLMService:
    """
    Convenience function to create an LLM service instance.

    Args:
        provider_name: Name of the provider to use. If None, uses default.
        model_name: Name of the model to use. If None, uses provider default.
        config_path: Optional path to config file
        **kwargs: Additional arguments to override configuration

    Returns:
        LLM service instance
    """
    factory = get_llm_service_factory(config_path)
    return factory.create_llm_service(provider_name, model_name, **kwargs)


def list_available_providers(config_path: Path | None = None) -> list[str]:
    """
    Get list of available provider names.

    Args:
        config_path: Optional path to config file

    Returns:
        List of provider names
    """
    factory = get_llm_service_factory(config_path)
    return factory.list_available_providers()


def list_available_models(
    provider_name: str | None = None, config_path: Path | None = None
) -> list[str]:
    """
    Get list of available models for a provider.

    Args:
        provider_name: Name of the provider. If None, uses default.
        config_path: Optional path to config file

    Returns:
        List of model names
    """
    factory = get_llm_service_factory(config_path)
    return factory.list_available_models(provider_name)

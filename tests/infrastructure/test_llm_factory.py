"""Tests for LLM service factory."""

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import yaml

from knowledge_base_organizer.infrastructure.llm_config import (
    LLMConfig,
    LLMConfigManager,
    LLMProviderConfig,
)
from knowledge_base_organizer.infrastructure.llm_factory import (
    LLMServiceFactory,
    create_llm_service,
)


class TestLLMServiceFactory:
    """Test LLM service factory."""

    def setup_method(self) -> None:
        """Set up test environment."""
        # Create temporary config file
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_file = self.temp_dir / "test_llm_config.yaml"

        # Create test configuration
        test_config = {
            "default_provider": "ollama",
            "providers": {
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "model_name": "qwen2.5:7b",
                    "timeout": 120,
                    "api_format": "ollama",
                    "options": {"temperature": 0.3},
                },
                "lm_studio": {
                    "base_url": "http://localhost:1234",
                    "model_name": "local-model",
                    "timeout": 60,
                    "api_format": "openai",
                    "options": {"temperature": 0.5, "max_tokens": 2048},
                },
            },
        }

        with open(self.config_file, "w") as f:
            yaml.dump(test_config, f)

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("knowledge_base_organizer.infrastructure.ollama_llm.OllamaLLMService")
    def test_create_ollama_service(self, mock_ollama_service: Any) -> None:
        """Test creating Ollama LLM service."""

        config_manager = LLMConfigManager(self.config_file)
        factory = LLMServiceFactory(config_manager)

        mock_service = MagicMock()
        mock_ollama_service.return_value = mock_service

        service = factory.create_llm_service("ollama")

        assert service is mock_service
        mock_ollama_service.assert_called_once_with(
            base_url="http://localhost:11434",
            model_name="qwen2.5:7b",
            timeout=120,
            temperature=0.3,
        )

    @patch(
        "knowledge_base_organizer.infrastructure.openai_compatible_llm.OpenAICompatibleLLMService"
    )
    def test_create_openai_compatible_service(self, mock_openai_service: Any) -> None:
        """Test creating OpenAI-compatible LLM service."""

        config_manager = LLMConfigManager(self.config_file)
        factory = LLMServiceFactory(config_manager)

        mock_service = MagicMock()
        mock_openai_service.return_value = mock_service

        service = factory.create_llm_service("lm_studio")

        assert service is mock_service
        mock_openai_service.assert_called_once_with(
            base_url="http://localhost:1234",
            model_name="local-model",
            timeout=60,
            api_key=None,
            temperature=0.5,
            max_tokens=2048,
        )

    def test_create_service_with_model_override(self) -> None:
        """Test creating service with model name override."""

        config_manager = LLMConfigManager(self.config_file)
        factory = LLMServiceFactory(config_manager)

        with patch(
            "knowledge_base_organizer.infrastructure.ollama_llm.OllamaLLMService"
        ) as mock_service:
            factory.create_llm_service("ollama", model_name="custom-model")
            mock_service.assert_called_once_with(
                base_url="http://localhost:11434",
                model_name="custom-model",  # Overridden
                timeout=120,
                temperature=0.3,
            )

    def test_create_service_with_kwargs_override(self) -> None:
        """Test creating service with additional kwargs."""

        config_manager = LLMConfigManager(self.config_file)
        factory = LLMServiceFactory(config_manager)

        with patch(
            "knowledge_base_organizer.infrastructure.ollama_llm.OllamaLLMService"
        ) as mock_service:
            factory.create_llm_service("ollama", timeout=300, custom_param="value")
            mock_service.assert_called_once_with(
                base_url="http://localhost:11434",
                model_name="qwen2.5:7b",
                timeout=300,  # Overridden
                temperature=0.3,
                custom_param="value",  # Additional parameter
            )

    def test_create_service_unknown_provider(self) -> None:
        """Test error handling for unknown provider."""

        config_manager = LLMConfigManager(self.config_file)
        factory = LLMServiceFactory(config_manager)

        with pytest.raises(ValueError, match="Unknown provider: unknown"):
            factory.create_llm_service("unknown")

    def test_get_provider_config(self) -> None:
        """Test getting provider configuration."""

        config_manager = LLMConfigManager(self.config_file)
        factory = LLMServiceFactory(config_manager)

        config = factory.get_provider_config("ollama")
        assert config.base_url == "http://localhost:11434"
        assert config.model_name == "qwen2.5:7b"
        assert config.timeout == 120

    def test_get_provider_config_unknown(self) -> None:
        """Test error handling for unknown provider config."""

        config_manager = LLMConfigManager(self.config_file)
        factory = LLMServiceFactory(config_manager)

        with pytest.raises(ValueError, match="Unknown provider: unknown"):
            factory.get_provider_config("unknown")

    def test_list_providers(self) -> None:
        """Test listing available providers."""

        config_manager = LLMConfigManager(self.config_file)
        factory = LLMServiceFactory(config_manager)

        providers = factory.list_providers()
        assert "ollama" in providers
        assert "lm_studio" in providers
        assert len(providers) == 2

    def test_get_default_provider(self) -> None:
        """Test getting default provider."""

        config_manager = LLMConfigManager(self.config_file)
        factory = LLMServiceFactory(config_manager)

        default_provider = factory.get_default_provider()
        assert default_provider == "ollama"

    def test_create_service_import_error_ollama(self) -> None:
        """Test handling import error for Ollama service."""

        config_manager = LLMConfigManager(self.config_file)
        factory = LLMServiceFactory(config_manager)

        with (
            patch(
                "knowledge_base_organizer.infrastructure.ollama_llm.OllamaLLMService",
                side_effect=ImportError("Module not found"),
            ),
            pytest.raises(ImportError),
        ):
            factory.create_llm_service("ollama")

    def test_create_service_import_error_openai(self) -> None:
        """Test handling import error for OpenAI service."""

        config_manager = LLMConfigManager(self.config_file)
        factory = LLMServiceFactory(config_manager)

        with patch(
            "knowledge_base_organizer.infrastructure.openai_compatible_llm.OpenAICompatibleLLMService",
            side_effect=ImportError("Module not found"),
        ):
            with pytest.raises(ImportError):
                factory.create_llm_service("lm_studio")


class TestCreateLLMServiceFunction:
    """Test create_llm_service convenience function."""

    def setup_method(self) -> None:
        """Set up test environment."""
        # Create temporary config file
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_file = self.temp_dir / "test_llm_config.yaml"

        # Create test configuration
        test_config = {
            "default_provider": "ollama",
            "providers": {
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "model_name": "qwen2.5:7b",
                    "timeout": 120,
                    "api_format": "ollama",
                    "options": {"temperature": 0.3},
                }
            },
        }

        with open(self.config_file, "w") as f:
            yaml.dump(test_config, f)

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("knowledge_base_organizer.infrastructure.llm_config.get_llm_config")
    def test_create_llm_service_function_default_provider(
        self, mock_get_config: Any
    ) -> None:
        """Test create_llm_service function with default provider."""
        # Mock configuration
        mock_config = LLMConfig(
            default_provider="ollama",
            providers={
                "ollama": LLMProviderConfig(
                    base_url="http://localhost:11434",
                    model_name="qwen2.5:7b",
                    timeout=120,
                    api_format="ollama",
                    options={"temperature": 0.3},
                )
            },
        )
        mock_get_config.return_value = mock_config

        with patch(
            "knowledge_base_organizer.infrastructure.ollama_llm.OllamaLLMService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            # Test with default provider (no provider specified)
            service = create_llm_service()

            assert service is mock_service
            mock_service_class.assert_called_once_with(
                base_url="http://localhost:11434",
                model_name="qwen2.5:7b",
                timeout=120,
                temperature=0.3,
            )

    @patch("knowledge_base_organizer.infrastructure.llm_config.get_llm_config")
    def test_create_llm_service_function_specific_provider(
        self, mock_get_config: Any
    ) -> None:
        """Test create_llm_service function with specific provider."""
        # Mock configuration
        mock_config = LLMConfig(
            default_provider="ollama",
            providers={
                "ollama": LLMProviderConfig(
                    base_url="http://localhost:11434",
                    model_name="qwen2.5:7b",
                    timeout=120,
                    api_format="ollama",
                    options={"temperature": 0.3},
                )
            },
        )
        mock_get_config.return_value = mock_config

        with patch(
            "knowledge_base_organizer.infrastructure.ollama_llm.OllamaLLMService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            # Test with specific provider
            service = create_llm_service(provider="ollama", model_name="custom-model")

            assert service is mock_service
            mock_service_class.assert_called_once_with(
                base_url="http://localhost:11434",
                model_name="custom-model",  # Overridden
                timeout=120,
                temperature=0.3,
            )


class TestFactoryIntegration:
    """Integration tests for LLM factory."""

    def setup_method(self) -> None:
        """Set up test environment."""
        # Create temporary config file
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_file = self.temp_dir / "test_llm_config.yaml"

        # Create comprehensive test configuration
        test_config = {
            "default_provider": "ollama",
            "providers": {
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "model_name": "qwen2.5:7b",
                    "timeout": 120,
                    "api_format": "ollama",
                    "options": {"temperature": 0.3},
                },
                "lm_studio": {
                    "base_url": "http://localhost:1234",
                    "model_name": "local-model",
                    "timeout": 60,
                    "api_format": "openai",
                    "api_key": "test-key",
                    "options": {"temperature": 0.5, "max_tokens": 2048},
                },
            },
        }

        with open(self.config_file, "w") as f:
            yaml.dump(test_config, f)

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_end_to_end_service_creation(self) -> None:
        """Test end-to-end service creation workflow."""

        config_manager = LLMConfigManager(self.config_file)
        factory = LLMServiceFactory(config_manager)

        # Test service creation (mocked to avoid actual network calls)
        with patch(
            "knowledge_base_organizer.infrastructure.ollama_llm.OllamaLLMService"
        ) as mock_ollama:
            mock_service = MagicMock()
            mock_ollama.return_value = mock_service

            # Create service using factory
            service = factory.create_llm_service("ollama")

            # Verify service was created correctly
            assert service is mock_service
            mock_ollama.assert_called_once()

            # Verify configuration was passed correctly
            call_args = mock_ollama.call_args
            assert call_args[1]["base_url"] == "http://localhost:11434"
            assert call_args[1]["model_name"] == "qwen2.5:7b"
            assert call_args[1]["timeout"] == 120
            assert call_args[1]["temperature"] == 0.3

    def test_multiple_provider_support(self) -> None:
        """Test support for multiple providers."""

        config_manager = LLMConfigManager(self.config_file)
        factory = LLMServiceFactory(config_manager)

        # Test that factory can handle multiple providers
        providers = factory.list_providers()
        assert "ollama" in providers
        assert "lm_studio" in providers

        # Test getting configurations for different providers
        ollama_config = factory.get_provider_config("ollama")
        lm_studio_config = factory.get_provider_config("lm_studio")

        assert ollama_config.api_format == "ollama"
        assert lm_studio_config.api_format == "openai"
        assert lm_studio_config.api_key == "test-key"

    def test_configuration_validation(self) -> None:
        """Test configuration validation."""

        config_manager = LLMConfigManager(self.config_file)
        factory = LLMServiceFactory(config_manager)

        # Test that factory validates provider existence
        with pytest.raises(ValueError):
            factory.create_llm_service("nonexistent_provider")

        # Test that factory validates configuration completeness
        config = factory.get_provider_config("ollama")
        assert config.base_url is not None
        assert config.model_name is not None
        assert config.timeout > 0

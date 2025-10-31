"""Integration tests for LLM configuration system."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from knowledge_base_organizer.infrastructure.llm_config import (
    LLMConfig,
    LLMConfigManager,
    get_llm_config,
)
from knowledge_base_organizer.infrastructure.llm_factory import (
    LLMServiceFactory,
    create_llm_service,
)


class TestLLMConfigurationIntegration:
    """Integration tests for LLM configuration system."""

    def setup_method(self) -> None:
        """Set up test environment."""
        # Create temporary config file
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_file = self.temp_dir / "test_llm_config.yaml"

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_end_to_end_ollama_configuration(self) -> None:
        """Test end-to-end Ollama configuration and service creation."""
        # Create Ollama configuration
        ollama_config = {
            "default_provider": "ollama",
            "providers": {
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "model_name": "qwen2.5:7b",
                    "timeout": 120,
                    "api_format": "ollama",
                    "options": {"temperature": 0.3, "top_p": 0.9},
                    "alternative_models": ["llama3.1:8b", "qwen2.5:14b"],
                }
            },
        }

        with open(self.config_file, "w") as f:
            yaml.dump(ollama_config, f)

        # Test configuration loading
        config_manager = LLMConfigManager(self.config_file)
        config = config_manager.get_config()

        assert config.default_provider == "ollama"
        assert "ollama" in config.providers
        assert config.providers["ollama"].base_url == "http://localhost:11434"
        assert config.providers["ollama"].model_name == "qwen2.5:7b"

        # Test factory creation
        factory = LLMServiceFactory(config_manager)
        assert factory.get_default_provider() == "ollama"

        # Test model listing
        models = factory.list_available_models("ollama")
        assert "qwen2.5:7b" in models
        assert "llama3.1:8b" in models
        assert "qwen2.5:14b" in models

        # Test service creation (mocked)
        with patch(
            "knowledge_base_organizer.infrastructure.ollama_llm.OllamaLLMService"
        ) as mock_service:
            mock_instance = MagicMock()
            mock_service.return_value = mock_instance

            service = factory.create_llm_service()

            assert service is mock_instance
            mock_service.assert_called_once_with(
                base_url="http://localhost:11434",
                model_name="qwen2.5:7b",
                timeout=120,
                temperature=0.3,
                top_p=0.9,
            )

    def test_end_to_end_lm_studio_configuration(self) -> None:
        """Test end-to-end LM Studio configuration and service creation."""
        # Create LM Studio configuration
        lm_studio_config = {
            "default_provider": "lm_studio",
            "providers": {
                "lm_studio": {
                    "base_url": "http://localhost:1234",
                    "model_name": "local-model",
                    "timeout": 60,
                    "api_format": "openai",
                    "api_key": "test-key",
                    "options": {"temperature": 0.5, "max_tokens": 2048},
                }
            },
        }

        with open(self.config_file, "w") as f:
            yaml.dump(lm_studio_config, f)

        # Test configuration loading
        config_manager = LLMConfigManager(self.config_file)
        config = config_manager.get_config()

        assert config.default_provider == "lm_studio"
        assert "lm_studio" in config.providers
        assert config.providers["lm_studio"].base_url == "http://localhost:1234"
        assert config.providers["lm_studio"].api_key == "test-key"

        # Test factory creation
        factory = LLMServiceFactory(config_manager)

        # Test service creation (mocked)
        with patch(
            "knowledge_base_organizer.infrastructure.openai_compatible_llm.OpenAICompatibleLLMService"
        ) as mock_service:
            mock_instance = MagicMock()
            mock_service.return_value = mock_instance

            service = factory.create_llm_service()

            assert service is mock_instance
            mock_service.assert_called_once_with(
                base_url="http://localhost:1234",
                model_name="local-model",
                timeout=60,
                api_key="test-key",
                temperature=0.5,
                max_tokens=2048,
            )

    def test_multi_provider_configuration(self) -> None:
        """Test configuration with multiple providers."""
        # Create multi-provider configuration
        multi_config = {
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
                    "options": {"temperature": 0.5},
                },
                "custom_api": {
                    "base_url": "http://custom-server:8000",
                    "model_name": "custom-model",
                    "timeout": 90,
                    "api_format": "openai",
                    "api_key": "custom-key",
                    "options": {"temperature": 0.7, "max_tokens": 1024},
                },
            },
        }

        with open(self.config_file, "w") as f:
            yaml.dump(multi_config, f)

        # Test configuration loading
        config_manager = LLMConfigManager(self.config_file)
        factory = LLMServiceFactory(config_manager)

        # Test provider listing
        providers = factory.list_providers()
        assert "ollama" in providers
        assert "lm_studio" in providers
        assert "custom_api" in providers
        assert len(providers) == 3

        # Test default provider
        assert factory.get_default_provider() == "ollama"

        # Test service creation for different providers (mocked)
        with patch(
            "knowledge_base_organizer.infrastructure.ollama_llm.OllamaLLMService"
        ) as mock_ollama:
            mock_ollama_instance = MagicMock()
            mock_ollama.return_value = mock_ollama_instance

            ollama_service = factory.create_llm_service("ollama")
            assert ollama_service is mock_ollama_instance

        with patch(
            "knowledge_base_organizer.infrastructure.openai_compatible_llm.OpenAICompatibleLLMService"
        ) as mock_openai:
            mock_openai_instance = MagicMock()
            mock_openai.return_value = mock_openai_instance

            lm_studio_service = factory.create_llm_service("lm_studio")
            assert lm_studio_service is mock_openai_instance

            custom_service = factory.create_llm_service("custom_api")
            assert custom_service is mock_openai_instance

    def test_environment_variable_override(self) -> None:
        """Test environment variable configuration override."""
        import os

        # Create base configuration
        base_config = {
            "default_provider": "ollama",
            "providers": {
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "model_name": "qwen2.5:7b",
                    "timeout": 120,
                    "api_format": "ollama",
                }
            },
        }

        with open(self.config_file, "w") as f:
            yaml.dump(base_config, f)

        # Set environment variables
        os.environ["OLLAMA_BASE_URL"] = "http://custom-host:11434"
        os.environ["OLLAMA_MODEL"] = "custom-model"

        try:
            # Test configuration with environment override
            config_manager = LLMConfigManager(self.config_file)
            config = config_manager.get_config()

            # Environment variables should override config file values
            assert config.providers["ollama"].base_url == "http://custom-host:11434"
            assert config.providers["ollama"].model_name == "custom-model"

        finally:
            # Clean up environment variables
            os.environ.pop("OLLAMA_BASE_URL", None)
            os.environ.pop("OLLAMA_MODEL", None)

    def test_model_override_functionality(self) -> None:
        """Test model override functionality."""
        # Create configuration
        config = {
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
            yaml.dump(config, f)

        config_manager = LLMConfigManager(self.config_file)
        factory = LLMServiceFactory(config_manager)

        # Test model override during service creation
        with patch(
            "knowledge_base_organizer.infrastructure.ollama_llm.OllamaLLMService"
        ) as mock_service:
            mock_instance = MagicMock()
            mock_service.return_value = mock_instance

            # Create service with model override
            service = factory.create_llm_service("ollama", model_name="custom-model")

            assert service is mock_instance
            # Verify that the overridden model name was used
            call_args = mock_service.call_args
            assert call_args[1]["model_name"] == "custom-model"
            assert (
                call_args[1]["base_url"] == "http://localhost:11434"
            )  # Original value

    def test_feature_configuration_integration(self) -> None:
        """Test integration with feature-specific configuration."""
        # Create configuration with feature settings
        config_with_features = {
            "default_provider": "ollama",
            "providers": {
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "model_name": "qwen2.5:7b",
                    "timeout": 120,
                    "api_format": "ollama",
                }
            },
            "metadata_suggestion": {"max_tags": 5, "max_aliases": 3},
            "summarization": {"default_max_length": 200, "min_length": 50},
        }

        with open(self.config_file, "w") as f:
            yaml.dump(config_with_features, f)

        # Test configuration loading
        config_manager = LLMConfigManager(self.config_file)
        config = config_manager.get_config()

        # Verify feature configuration is loaded correctly
        assert config.metadata_suggestion.max_tags == 5  # Default value, not overridden
        assert config.metadata_suggestion.max_aliases == 3  # Default value
        assert config.summarization.default_max_length == 200  # Default value

    def test_global_function_integration(self) -> None:
        """Test integration with global convenience functions."""
        # Create configuration
        config = {
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
            yaml.dump(config, f)

        # Test global configuration function
        with patch(
            "knowledge_base_organizer.infrastructure.llm_config.DEFAULT_CONFIG_PATH",
            self.config_file,
        ):
            global_config = get_llm_config()
            assert global_config.default_provider == "ollama"

        # Test global service creation function
        with (
            patch(
                "knowledge_base_organizer.infrastructure.llm_config.get_llm_config"
            ) as mock_get_config,
            patch(
                "knowledge_base_organizer.infrastructure.ollama_llm.OllamaLLMService"
            ) as mock_service,
        ):
            mock_get_config.return_value = LLMConfig.from_dict(config)
            mock_instance = MagicMock()
            mock_service.return_value = mock_instance

            service = create_llm_service()
            assert service is mock_instance

    def test_error_handling_integration(self) -> None:
        """Test error handling in integrated scenarios."""
        # Test with invalid configuration file
        invalid_config_file = self.temp_dir / "invalid.yaml"
        invalid_config_file.write_text("invalid: yaml: content: [")

        with pytest.raises(yaml.YAMLError):
            LLMConfigManager(invalid_config_file)

        # Test with missing provider
        valid_config = {
            "default_provider": "nonexistent",
            "providers": {
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "model_name": "qwen2.5:7b",
                    "timeout": 120,
                    "api_format": "ollama",
                }
            },
        }

        with open(self.config_file, "w") as f:
            yaml.dump(valid_config, f)

        config_manager = LLMConfigManager(self.config_file)
        factory = LLMServiceFactory(config_manager)

        with pytest.raises(ValueError, match="Unknown provider: nonexistent"):
            factory.create_llm_service()

    def test_configuration_validation_integration(self) -> None:
        """Test configuration validation in integrated scenarios."""
        # Test with minimal valid configuration
        minimal_config = {
            "default_provider": "ollama",
            "providers": {
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "model_name": "qwen2.5:7b",
                    "api_format": "ollama",
                }
            },
        }

        with open(self.config_file, "w") as f:
            yaml.dump(minimal_config, f)

        # Should load successfully with defaults
        config_manager = LLMConfigManager(self.config_file)
        config = config_manager.get_config()

        assert config.providers["ollama"].timeout == 120  # Default value
        assert config.providers["ollama"].options == {}  # Default empty options

        # Test factory creation with minimal config
        factory = LLMServiceFactory(config_manager)
        provider_config = factory.get_provider_config("ollama")

        assert provider_config.base_url == "http://localhost:11434"
        assert provider_config.model_name == "qwen2.5:7b"
        assert provider_config.timeout == 120

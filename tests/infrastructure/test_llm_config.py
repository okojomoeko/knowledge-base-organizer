"""Tests for LLM configuration management."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from knowledge_base_organizer.infrastructure.llm_config import (
    LLMConfig,
    LLMConfigManager,
    LLMProviderConfig,
    get_llm_config,
    get_llm_config_manager,
)


class TestLLMProviderConfig:
    """Test LLM provider configuration."""

    def test_provider_config_creation(self):
        """Test creating provider configuration."""
        config = LLMProviderConfig(
            base_url="http://localhost:11434",
            model_name="qwen2.5:7b",
            timeout=120,
            api_format="ollama",
            options={"temperature": 0.3},
        )

        assert config.base_url == "http://localhost:11434"
        assert config.model_name == "qwen2.5:7b"
        assert config.timeout == 120
        assert config.api_format == "ollama"
        assert config.options["temperature"] == 0.3

    def test_provider_config_defaults(self):
        """Test provider configuration with defaults."""
        config = LLMProviderConfig(
            base_url="http://localhost:11434", model_name="qwen2.5:7b"
        )

        assert config.timeout == 120
        assert config.api_format == "ollama"
        assert config.api_key is None
        assert config.options == {}
        assert config.alternative_models == []


class TestLLMConfig:
    """Test LLM configuration."""

    def test_llm_config_creation(self):
        """Test creating LLM configuration."""
        providers = {
            "ollama": LLMProviderConfig(
                base_url="http://localhost:11434", model_name="qwen2.5:7b"
            )
        }

        config = LLMConfig(default_provider="ollama", providers=providers)

        assert config.default_provider == "ollama"
        assert "ollama" in config.providers
        assert config.providers["ollama"].model_name == "qwen2.5:7b"

    def test_llm_config_with_feature_settings(self):
        """Test LLM configuration with feature settings."""
        providers = {
            "ollama": LLMProviderConfig(
                base_url="http://localhost:11434", model_name="qwen2.5:7b"
            )
        }

        config = LLMConfig(default_provider="ollama", providers=providers)

        # Test default feature settings
        assert config.metadata_suggestion.max_tags == 5
        assert config.summarization.default_max_length == 200
        assert config.performance.retry_attempts == 3


class TestLLMConfigManager:
    """Test LLM configuration manager."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_file = self.temp_dir / "llm_config.yaml"

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_config_manager_initialization(self):
        """Test config manager initialization."""
        manager = LLMConfigManager()
        assert manager.config_path is None
        assert manager._config is None

    def test_config_manager_with_custom_path(self):
        """Test config manager with custom path."""
        manager = LLMConfigManager(self.config_file)
        assert manager.config_path == self.config_file

    def test_load_config_from_file(self):
        """Test loading configuration from file."""
        # Create test config file
        config_data = {
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
            yaml.dump(config_data, f)

        manager = LLMConfigManager(self.config_file)
        config = manager.load_config()

        assert config.default_provider == "ollama"
        assert "ollama" in config.providers
        assert config.providers["ollama"].model_name == "qwen2.5:7b"

    def test_load_config_default_when_no_file(self):
        """Test loading default configuration when no file exists."""
        non_existent_file = self.temp_dir / "non_existent.yaml"
        manager = LLMConfigManager(non_existent_file)
        config = manager.load_config()

        assert config.default_provider == "ollama"
        assert "ollama" in config.providers

    def test_apply_env_overrides(self):
        """Test applying environment variable overrides."""
        manager = LLMConfigManager()

        config_data = {
            "default_provider": "ollama",
            "providers": {
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "model_name": "qwen2.5:7b",
                }
            },
        }

        with patch.dict(
            os.environ,
            {
                "OLLAMA_BASE_URL": "http://custom:11434",
                "OLLAMA_MODEL": "llama3.1:8b",
                "LLM_PROVIDER": "custom_ollama",
            },
        ):
            result = manager._apply_env_overrides(config_data)

            assert result["default_provider"] == "custom_ollama"
            assert result["providers"]["ollama"]["base_url"] == "http://custom:11434"
            assert result["providers"]["ollama"]["model_name"] == "llama3.1:8b"

    def test_get_provider_config(self):
        """Test getting provider configuration."""
        config_data = {
            "default_provider": "ollama",
            "providers": {
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "model_name": "qwen2.5:7b",
                },
                "lm_studio": {
                    "base_url": "http://localhost:1234",
                    "model_name": "local-model",
                    "api_format": "openai",
                },
            },
        }

        with open(self.config_file, "w") as f:
            yaml.dump(config_data, f)

        manager = LLMConfigManager(self.config_file)

        # Test default provider
        default_config = manager.get_provider_config()
        assert default_config.base_url == "http://localhost:11434"

        # Test specific provider
        lm_studio_config = manager.get_provider_config("lm_studio")
        assert lm_studio_config.base_url == "http://localhost:1234"
        assert lm_studio_config.api_format == "openai"

    def test_get_provider_config_invalid_provider(self):
        """Test getting configuration for invalid provider."""
        manager = LLMConfigManager(self.config_file)

        with pytest.raises(ValueError, match="Provider 'invalid' not configured"):
            manager.get_provider_config("invalid")

    def test_list_available_providers(self):
        """Test listing available providers."""
        config_data = {
            "default_provider": "ollama",
            "providers": {
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "model_name": "qwen2.5:7b",
                },
                "lm_studio": {
                    "base_url": "http://localhost:1234",
                    "model_name": "local-model",
                },
            },
        }

        with open(self.config_file, "w") as f:
            yaml.dump(config_data, f)

        manager = LLMConfigManager(self.config_file)
        providers = manager.list_available_providers()

        assert "ollama" in providers
        assert "lm_studio" in providers
        assert len(providers) == 2

    def test_list_available_models(self):
        """Test listing available models for a provider."""
        config_data = {
            "default_provider": "ollama",
            "providers": {
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "model_name": "qwen2.5:7b",
                    "alternative_models": ["llama3.1:8b", "qwen2.5:14b"],
                }
            },
        }

        with open(self.config_file, "w") as f:
            yaml.dump(config_data, f)

        manager = LLMConfigManager(self.config_file)
        models = manager.list_available_models("ollama")

        assert "qwen2.5:7b" in models
        assert "llama3.1:8b" in models
        assert "qwen2.5:14b" in models
        assert len(models) == 3

    def test_create_user_config_template(self):
        """Test creating user configuration template."""
        manager = LLMConfigManager()
        template_file = self.temp_dir / "template.yaml"

        manager.create_user_config_template(template_file)

        assert template_file.exists()

        with open(template_file) as f:
            template_data = yaml.safe_load(f)

        assert template_data["default_provider"] == "ollama"
        assert "ollama" in template_data["providers"]
        assert "lm_studio" in template_data["providers"]

    def test_config_caching(self):
        """Test configuration caching."""
        config_data = {
            "default_provider": "ollama",
            "providers": {
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "model_name": "qwen2.5:7b",
                }
            },
        }

        with open(self.config_file, "w") as f:
            yaml.dump(config_data, f)

        manager = LLMConfigManager(self.config_file)

        # First load
        config1 = manager.load_config()
        # Second load (should use cache)
        config2 = manager.load_config()

        assert config1 is config2  # Same object due to caching


class TestGlobalFunctions:
    """Test global configuration functions."""

    def test_get_llm_config_manager(self):
        """Test getting global config manager."""
        # Reset global state
        import knowledge_base_organizer.infrastructure.llm_config as llm_config_module

        llm_config_module._config_manager = None

        manager1 = get_llm_config_manager()
        manager2 = get_llm_config_manager()

        assert manager1 is manager2  # Same instance

    def test_get_llm_config(self):
        """Test getting LLM configuration."""
        # Reset global state
        import knowledge_base_organizer.infrastructure.llm_config as llm_config_module

        llm_config_module._config_manager = None

        config = get_llm_config()

        assert isinstance(config, LLMConfig)
        assert config.default_provider == "ollama"

    def test_get_llm_config_with_custom_path(self):
        """Test getting LLM configuration with custom path."""
        temp_dir = Path(tempfile.mkdtemp())
        config_file = temp_dir / "custom_config.yaml"

        try:
            config_data = {
                "default_provider": "custom",
                "providers": {
                    "custom": {
                        "base_url": "http://custom:8000",
                        "model_name": "custom-model",
                    }
                },
            }

            with open(config_file, "w") as f:
                yaml.dump(config_data, f)

            config = get_llm_config(config_file)

            assert config.default_provider == "ollama"  # Default from built-in config
            assert "custom" in config.providers

        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)


class TestConfigValidation:
    """Test configuration validation."""

    def test_invalid_yaml_file(self):
        """Test handling of invalid YAML file."""
        temp_dir = Path(tempfile.mkdtemp())
        config_file = temp_dir / "invalid.yaml"

        try:
            # Create invalid YAML
            with open(config_file, "w") as f:
                f.write("invalid: yaml: content: [")

            manager = LLMConfigManager(config_file)
            config = manager.load_config()  # Should fall back to default

            assert config.default_provider == "ollama"

        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_missing_required_fields(self):
        """Test handling of missing required fields."""
        temp_dir = Path(tempfile.mkdtemp())
        config_file = temp_dir / "incomplete.yaml"

        try:
            # Create config with missing required fields
            config_data = {
                "providers": {
                    "ollama": {
                        "base_url": "http://localhost:11434"
                        # Missing model_name
                    }
                }
            }

            with open(config_file, "w") as f:
                yaml.dump(config_data, f)

            manager = LLMConfigManager(config_file)

            # Should raise validation error when creating LLMConfig
            with pytest.raises(Exception):  # Pydantic validation error
                manager.load_config()

        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

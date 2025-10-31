"""
LLM Configuration Management

This module provides configuration management for different LLM providers,
allowing users to easily switch between Ollama, LM Studio, and other
OpenAI-compatible APIs.
"""

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class LLMProviderConfig(BaseModel):
    """Configuration for a specific LLM provider."""

    base_url: str
    model_name: str
    timeout: int = 120
    api_format: str = "ollama"  # "ollama", "openai", etc.
    api_key: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)
    alternative_models: list[str] = Field(default_factory=list)


class LLMFeatureConfig(BaseModel):
    """Configuration for LLM features."""

    max_tags: int = 5
    max_aliases: int = 3
    description_max_length: int = 200


class LLMSummarizationConfig(BaseModel):
    """Configuration for summarization features."""

    default_max_length: int = 200
    min_length: int = 50
    preserve_structure: bool = True


class LLMConceptConfig(BaseModel):
    """Configuration for concept extraction."""

    max_concepts: int = 5
    min_confidence: float = 0.6


class LLMRelationshipConfig(BaseModel):
    """Configuration for relationship analysis."""

    confidence_threshold: float = 0.7
    max_relationships: int = 10


class LLMPerformanceConfig(BaseModel):
    """Configuration for performance and reliability."""

    retry_attempts: int = 3
    retry_delay: float = 1.0
    connection_timeout: int = 30
    read_timeout: int = 120
    fallback_on_error: bool = True
    fallback_provider: str = "ollama"


class LLMLoggingConfig(BaseModel):
    """Configuration for logging and debugging."""

    log_requests: bool = False
    log_responses: bool = False
    log_errors: bool = True
    debug_mode: bool = False


class LLMConfig(BaseModel):
    """Complete LLM configuration."""

    default_provider: str = "ollama"
    providers: dict[str, LLMProviderConfig]
    model_settings: dict[str, Any] = Field(default_factory=dict)

    # Feature configurations
    metadata_suggestion: LLMFeatureConfig = Field(default_factory=LLMFeatureConfig)
    summarization: LLMSummarizationConfig = Field(
        default_factory=LLMSummarizationConfig
    )
    concept_extraction: LLMConceptConfig = Field(default_factory=LLMConceptConfig)
    relationship_analysis: LLMRelationshipConfig = Field(
        default_factory=LLMRelationshipConfig
    )

    # System configurations
    performance: LLMPerformanceConfig = Field(default_factory=LLMPerformanceConfig)
    logging: LLMLoggingConfig = Field(default_factory=LLMLoggingConfig)


class LLMConfigManager:
    """Manager for LLM configuration loading and validation."""

    def __init__(self, config_path: Path | None = None):
        """
        Initialize LLM configuration manager.

        Args:
            config_path: Path to custom config file. If None, uses default locations.
        """
        self.config_path = config_path
        self._config: LLMConfig | None = None

    def load_config(self) -> LLMConfig:
        """
        Load LLM configuration from file or environment.

        Returns:
            LLMConfig object with loaded configuration
        """
        if self._config is not None:
            return self._config

        # Try to load from various sources
        config_data = self._load_config_data()

        # Apply environment variable overrides
        config_data = self._apply_env_overrides(config_data)

        # Validate and create config object
        self._config = LLMConfig(**config_data)

        return self._config

    def _load_config_data(self) -> dict[str, Any]:
        """Load configuration data from file."""
        config_paths = self._get_config_paths()

        for config_path in config_paths:
            if config_path.exists():
                try:
                    with Path(config_path).open(encoding="utf-8") as f:
                        return yaml.safe_load(f) or {}
                except Exception as e:
                    print(f"Warning: Failed to load config from {config_path}: {e}")
                    continue

        # Return default configuration if no file found
        return self._get_default_config()

    def _get_config_paths(self) -> list[Path]:
        """Get list of potential configuration file paths in order of priority."""
        paths = []

        # 1. Explicitly provided path
        if self.config_path:
            paths.append(self.config_path)

        # 2. Environment variable
        env_config_path = os.getenv("LLM_CONFIG_PATH")
        if env_config_path:
            paths.append(Path(env_config_path))

        # 3. Current directory
        paths.append(Path.cwd() / "llm_config.yaml")
        paths.append(Path.cwd() / ".kiro" / "llm_config.yaml")

        # 4. User home directory
        home_dir = Path.home()
        paths.append(home_dir / ".kiro" / "llm_config.yaml")

        # 5. Package default
        package_dir = Path(__file__).parent.parent / "config"
        paths.append(package_dir / "llm_config.yaml")

        return paths

    def _apply_env_overrides(self, config_data: dict[str, Any]) -> dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        # Override default provider
        if os.getenv("LLM_PROVIDER"):
            config_data["default_provider"] = os.getenv("LLM_PROVIDER")

        # Override Ollama settings
        if os.getenv("OLLAMA_BASE_URL"):
            if "providers" not in config_data:
                config_data["providers"] = {}
            if "ollama" not in config_data["providers"]:
                config_data["providers"]["ollama"] = {}
            config_data["providers"]["ollama"]["base_url"] = os.getenv(
                "OLLAMA_BASE_URL"
            )

        if os.getenv("OLLAMA_MODEL"):
            if "providers" not in config_data:
                config_data["providers"] = {}
            if "ollama" not in config_data["providers"]:
                config_data["providers"]["ollama"] = {}
            config_data["providers"]["ollama"]["model_name"] = os.getenv("OLLAMA_MODEL")

        # Override LM Studio settings
        if os.getenv("LM_STUDIO_BASE_URL"):
            if "providers" not in config_data:
                config_data["providers"] = {}
            if "lm_studio" not in config_data["providers"]:
                config_data["providers"]["lm_studio"] = {}
            config_data["providers"]["lm_studio"]["base_url"] = os.getenv(
                "LM_STUDIO_BASE_URL"
            )

        # Override OpenAI API settings
        if os.getenv("OPENAI_API_KEY"):
            if "providers" not in config_data:
                config_data["providers"] = {}
            if "openai_compatible" not in config_data["providers"]:
                config_data["providers"]["openai_compatible"] = {}
            config_data["providers"]["openai_compatible"]["api_key"] = os.getenv(
                "OPENAI_API_KEY"
            )

        if os.getenv("OPENAI_BASE_URL"):
            if "providers" not in config_data:
                config_data["providers"] = {}
            if "openai_compatible" not in config_data["providers"]:
                config_data["providers"]["openai_compatible"] = {}
            config_data["providers"]["openai_compatible"]["base_url"] = os.getenv(
                "OPENAI_BASE_URL"
            )

        return config_data

    def _get_default_config(self) -> dict[str, Any]:
        """Get default configuration when no config file is found."""
        return {
            "default_provider": "ollama",
            "providers": {
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "model_name": "qwen2.5:7b",
                    "timeout": 120,
                    "api_format": "ollama",
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "top_k": 40,
                    },
                }
            },
        }

    def get_provider_config(
        self, provider_name: str | None = None
    ) -> LLMProviderConfig:
        """
        Get configuration for a specific provider.

        Args:
            provider_name: Name of the provider. If None, uses default provider.

        Returns:
            LLMProviderConfig for the specified provider

        Raises:
            ValueError: If provider is not configured
        """
        config = self.load_config()

        if provider_name is None:
            provider_name = config.default_provider

        if provider_name not in config.providers:
            raise ValueError(f"Unknown provider: {provider_name}")

        return config.providers[provider_name]

    def list_available_providers(self) -> list[str]:
        """Get list of available provider names."""
        config = self.load_config()
        return list(config.providers.keys())

    def list_available_models(self, provider_name: str | None = None) -> list[str]:
        """
        Get list of available models for a provider.

        Args:
            provider_name: Name of the provider. If None, uses default provider.

        Returns:
            List of model names
        """
        provider_config = self.get_provider_config(provider_name)
        models = [provider_config.model_name]
        models.extend(provider_config.alternative_models)
        return models

    def create_user_config_template(self, output_path: Path) -> None:
        """
        Create a user configuration template file.

        Args:
            output_path: Path where to create the template file
        """
        template_config = {
            "default_provider": "ollama",
            "providers": {
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "model_name": "qwen2.5:7b",
                    "timeout": 120,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "top_k": 40,
                    },
                },
                "lm_studio": {
                    "base_url": "http://localhost:1234",
                    "model_name": "local-model",
                    "timeout": 120,
                    "api_format": "openai",
                    "options": {
                        "temperature": 0.3,
                        "max_tokens": 2048,
                    },
                },
            },
            "features": {
                "metadata_suggestion": {
                    "max_tags": 5,
                    "max_aliases": 3,
                },
                "summarization": {
                    "default_max_length": 200,
                },
            },
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with Path(output_path).open("w", encoding="utf-8") as f:
            yaml.dump(template_config, f, default_flow_style=False, allow_unicode=True)

        print(f"Created LLM configuration template at: {output_path}")


# Global configuration manager instance
_config_manager: LLMConfigManager | None = None


def get_llm_config_manager(config_path: Path | None = None) -> LLMConfigManager:
    """
    Get the global LLM configuration manager instance.

    Args:
        config_path: Optional path to config file (only used on first call)

    Returns:
        LLMConfigManager instance
    """
    global _config_manager

    if _config_manager is None:
        _config_manager = LLMConfigManager(config_path)

    return _config_manager


def get_llm_config(config_path: Path | None = None) -> LLMConfig:
    """
    Get the current LLM configuration.

    Args:
        config_path: Optional path to config file

    Returns:
        LLMConfig object
    """
    manager = get_llm_config_manager(config_path)
    return manager.load_config()

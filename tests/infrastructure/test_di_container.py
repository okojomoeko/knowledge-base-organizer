"""Tests for the DI container implementation."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

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


class TestDIContainer:
    """Test cases for DIContainer"""

    def test_init_container(self):
        """Test container initialization"""
        config = ProcessingConfig.get_default_config()
        vault_path = Path("/tmp/test_vault")

        container = DIContainer(config, vault_path)

        assert container.config == config
        assert container.vault_path == vault_path
        assert len(container._services) == 0
        assert len(container._factories) > 0

    def test_register_custom_factory(self):
        """Test registering custom service factory"""
        config = ProcessingConfig.get_default_config()
        vault_path = Path("/tmp/test_vault")
        container = DIContainer(config, vault_path)

        mock_factory = Mock()
        container.register_factory("custom_service", mock_factory)

        assert "custom_service" in container._factories

    def test_get_service_info(self):
        """Test getting service information"""
        config = ProcessingConfig.get_default_config()
        vault_path = Path("/tmp/test_vault")
        container = DIContainer(config, vault_path)

        info = container.get_service_info()

        assert "registered_factories" in info
        assert "cached_services" in info
        assert "vault_path" in info
        assert len(info["registered_factories"]) > 0

    def test_clear_cache(self):
        """Test clearing service cache"""
        config = ProcessingConfig.get_default_config()
        vault_path = Path("/tmp/test_vault")
        container = DIContainer(config, vault_path)

        # Add something to cache
        container._services["test"] = Mock()
        assert len(container._services) == 1

        container.clear_cache()
        assert len(container._services) == 0

    def test_unknown_service_type_error(self):
        """Test error handling for unknown service types"""
        config = ProcessingConfig.get_default_config()
        vault_path = Path("/tmp/test_vault")
        container = DIContainer(config, vault_path)

        with pytest.raises(ValueError, match="Unknown embedding service type"):
            container.get_embedding_service("unknown_type")

        with pytest.raises(ValueError, match="Unknown vector store type"):
            container.get_vector_store("unknown_type")

        with pytest.raises(ValueError, match="Unknown LLM service type"):
            container.get_llm_service("unknown_type")

    def test_get_embedding_service_caching(self):
        """Test that embedding service is cached properly"""
        config = ProcessingConfig.get_default_config()
        vault_path = Path("/tmp/test_vault")
        container = DIContainer(config, vault_path)

        # Mock the factory method instead of the class
        mock_service = Mock(spec=EmbeddingService)
        container._factories["test_embedding"] = Mock(return_value=mock_service)

        # First call should create the service
        service1 = container.get_embedding_service("test_embedding")
        assert service1 == mock_service
        assert container._factories["test_embedding"].call_count == 1

        # Second call should return cached service
        service2 = container.get_embedding_service("test_embedding")
        assert service2 == mock_service
        assert (
            container._factories["test_embedding"].call_count == 1
        )  # No additional calls

    def test_get_vector_store_caching(self):
        """Test that vector store is cached properly"""
        config = ProcessingConfig.get_default_config()
        vault_path = Path("/tmp/test_vault")
        container = DIContainer(config, vault_path)

        # Mock the factory method instead of the class
        mock_service = Mock(spec=VectorStore)
        container._factories["test_vector_store"] = Mock(return_value=mock_service)

        # First call should create the service
        service1 = container.get_vector_store("test_vector_store")
        assert service1 == mock_service
        assert container._factories["test_vector_store"].call_count == 1

        # Second call should return cached service
        service2 = container.get_vector_store("test_vector_store")
        assert service2 == mock_service
        assert (
            container._factories["test_vector_store"].call_count == 1
        )  # No additional calls

    def test_get_llm_service_caching(self):
        """Test that LLM service is cached properly"""
        config = ProcessingConfig.get_default_config()
        vault_path = Path("/tmp/test_vault")
        container = DIContainer(config, vault_path)

        # Mock the factory method instead of the class
        mock_service = Mock(spec=LLMService)
        container._factories["test_llm"] = Mock(return_value=mock_service)

        # First call should create the service
        service1 = container.get_llm_service("test_llm")
        assert service1 == mock_service
        assert container._factories["test_llm"].call_count == 1

        # Second call should return cached service
        service2 = container.get_llm_service("test_llm")
        assert service2 == mock_service
        assert container._factories["test_llm"].call_count == 1  # No additional calls


class TestAIServiceConfig:
    """Test cases for AIServiceConfig"""

    def test_init_empty_config(self):
        """Test initialization with empty config"""
        config = AIServiceConfig()
        assert config.config == {}

    def test_init_with_config(self):
        """Test initialization with provided config"""
        config_dict = {"embedding": {"type": "test"}}
        config = AIServiceConfig(config_dict)
        assert config.config == config_dict

    def test_get_default_config(self):
        """Test getting default configuration"""
        config = AIServiceConfig.get_default_config()

        assert "embedding" in config.config
        assert "vector_store" in config.config
        assert "llm" in config.config

        # Check embedding config
        embedding_config = config.get_embedding_config()
        assert embedding_config["type"] == "ollama_embedding"
        assert "base_url" in embedding_config
        assert "model_name" in embedding_config

    def test_from_file_nonexistent(self):
        """Test loading from non-existent file"""
        config = AIServiceConfig.from_file(Path("/nonexistent/file.yaml"))
        assert config.config == {}

    def test_from_file_existing(self):
        """Test loading from existing file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
ai_services:
  embedding:
    type: test_embedding
    param: value
""")
            f.flush()

            config = AIServiceConfig.from_file(Path(f.name))

            assert "embedding" in config.config
            assert config.config["embedding"]["type"] == "test_embedding"
            assert config.config["embedding"]["param"] == "value"

        # Clean up
        Path(f.name).unlink()

    def test_get_service_configs(self):
        """Test getting individual service configurations"""
        config_dict = {
            "embedding": {"type": "test_embedding"},
            "vector_store": {"type": "test_vector_store"},
            "llm": {"type": "test_llm"},
        }
        config = AIServiceConfig(config_dict)

        assert config.get_embedding_config() == {"type": "test_embedding"}
        assert config.get_vector_store_config() == {"type": "test_vector_store"}
        assert config.get_llm_config() == {"type": "test_llm"}


class TestCreateDIContainer:
    """Test cases for create_di_container factory function"""

    def test_create_with_defaults(self):
        """Test creating container with default configuration"""
        vault_path = Path("/tmp/test_vault")

        # Create empty AI config to avoid trying to connect to Ollama
        ai_config = AIServiceConfig({})
        container = create_di_container(vault_path, ai_config=ai_config)

        assert isinstance(container, DIContainer)
        assert container.vault_path == vault_path

    def test_create_with_custom_config(self):
        """Test creating container with custom configuration"""
        vault_path = Path("/tmp/test_vault")
        config = ProcessingConfig.get_default_config()

        # Create empty AI config to avoid trying to connect to Ollama
        ai_config = AIServiceConfig({})

        container = create_di_container(vault_path, config, ai_config)

        assert isinstance(container, DIContainer)
        assert container.config == config
        assert container.vault_path == vault_path

    def test_create_loads_config_from_vault(self):
        """Test that container loads config from vault directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_path = Path(temp_dir)
            kiro_dir = vault_path / ".kiro"
            kiro_dir.mkdir()

            # Create AI config file with empty services to avoid connection attempts
            config_file = kiro_dir / "ai_config.yaml"
            config_file.write_text("""
ai_services: {}
""")

            container = create_di_container(vault_path)

            assert isinstance(container, DIContainer)
            assert container.vault_path == vault_path

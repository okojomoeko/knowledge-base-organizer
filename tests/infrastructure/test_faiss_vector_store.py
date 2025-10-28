"""
Tests for FaissVectorStore implementation.

Tests cover:
- Vector indexing and retrieval
- Similarity search functionality
- Metadata storage and retrieval
- Index persistence (save/load)
- Error handling and edge cases
"""

import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from knowledge_base_organizer.domain.services.ai_services import VectorStoreError
from knowledge_base_organizer.infrastructure.faiss_vector_store import FaissVectorStore


class TestFaissVectorStore:
    """Test suite for FaissVectorStore functionality."""

    @pytest.fixture
    def vector_store(self) -> FaissVectorStore:
        """Create a fresh vector store for testing."""
        return FaissVectorStore(dimension=384)

    @pytest.fixture
    def sample_vectors(self) -> list[list[float]]:
        """Generate sample vectors for testing."""
        np.random.seed(42)  # For reproducible tests
        return [
            np.random.rand(384).tolist(),
            np.random.rand(384).tolist(),
            np.random.rand(384).tolist(),
        ]

    @pytest.fixture
    def sample_metadata(self) -> list[dict[str, Any]]:
        """Generate sample metadata for testing."""
        return [
            {"title": "Document 1", "tags": ["test", "sample"]},
            {"title": "Document 2", "tags": ["test", "example"]},
            {"title": "Document 3", "tags": ["sample", "demo"]},
        ]

    def test_initialization(self) -> None:
        """Test vector store initialization."""
        store = FaissVectorStore(dimension=512)
        assert store.dimension == 512
        assert store.index is not None
        assert len(store.document_ids) == 0
        assert len(store.metadata_store) == 0

    def test_index_document_basic(
        self, vector_store: FaissVectorStore, sample_vectors: list[list[float]]
    ) -> None:
        """Test basic document indexing."""
        doc_id = "doc1"
        vector = sample_vectors[0]

        vector_store.index_document(doc_id, vector)

        assert doc_id in vector_store.document_ids
        assert vector_store.index.ntotal == 1

    def test_index_document_with_metadata(
        self,
        vector_store: FaissVectorStore,
        sample_vectors: list[list[float]],
        sample_metadata: list[dict[str, Any]],
    ) -> None:
        """Test document indexing with metadata."""
        doc_id = "doc1"
        vector = sample_vectors[0]
        metadata = sample_metadata[0]

        vector_store.index_document(doc_id, vector, metadata)

        assert doc_id in vector_store.document_ids
        assert vector_store.metadata_store[doc_id] == metadata

    def test_index_document_wrong_dimension(
        self, vector_store: FaissVectorStore
    ) -> None:
        """Test indexing with wrong vector dimension."""
        doc_id = "doc1"
        wrong_vector = [1.0, 2.0, 3.0]  # Wrong dimension

        with pytest.raises(VectorStoreError, match="Vector dimension"):
            vector_store.index_document(doc_id, wrong_vector)

    def test_index_document_update_existing(
        self, vector_store: FaissVectorStore, sample_vectors: list[list[float]]
    ) -> None:
        """Test updating an existing document."""
        doc_id = "doc1"
        vector1 = sample_vectors[0]
        vector2 = sample_vectors[1]
        metadata1 = {"version": 1}
        metadata2 = {"version": 2}

        # Index first version
        vector_store.index_document(doc_id, vector1, metadata1)
        assert vector_store.index.ntotal == 1
        assert vector_store.metadata_store[doc_id]["version"] == 1

        # Update with second version
        vector_store.index_document(doc_id, vector2, metadata2)
        assert vector_store.index.ntotal == 1  # Should still be 1
        assert vector_store.metadata_store[doc_id]["version"] == 2

    def test_search_basic(
        self,
        vector_store: FaissVectorStore,
        sample_vectors: list[list[float]],
        sample_metadata: list[dict[str, Any]],
    ) -> None:
        """Test basic similarity search."""
        # Index multiple documents
        for i, (vector, metadata) in enumerate(
            zip(sample_vectors, sample_metadata, strict=False)
        ):
            vector_store.index_document(f"doc{i}", vector, metadata)

        # Search with first vector (should return itself as top result)
        results = vector_store.search(sample_vectors[0], k=3)

        assert len(results) == 3
        assert results[0].document_id == "doc0"  # Should be most similar to itself
        assert results[0].similarity_score > results[1].similarity_score

    def test_search_with_threshold(
        self, vector_store: FaissVectorStore, sample_vectors: list[list[float]]
    ) -> None:
        """Test search with similarity threshold."""
        # Index documents
        for i, vector in enumerate(sample_vectors):
            vector_store.index_document(f"doc{i}", vector)

        # Search with high threshold (should return fewer results)
        results = vector_store.search(sample_vectors[0], k=3, threshold=0.9)

        # Should return at least the exact match (itself)
        assert len(results) >= 1
        assert all(result.similarity_score >= 0.9 for result in results)

    def test_search_empty_index(self, vector_store: FaissVectorStore) -> None:
        """Test search on empty index."""
        query_vector = [1.0] * 384
        results = vector_store.search(query_vector, k=5)
        assert len(results) == 0

    def test_search_wrong_dimension(
        self, vector_store: FaissVectorStore, sample_vectors: list[list[float]]
    ) -> None:
        """Test search with wrong query dimension."""
        # Index a document first
        vector_store.index_document("doc1", sample_vectors[0])

        # Search with wrong dimension
        wrong_query = [1.0, 2.0, 3.0]
        with pytest.raises(VectorStoreError, match="Query vector dimension"):
            vector_store.search(wrong_query, k=1)

    def test_get_document_vector(
        self, vector_store: FaissVectorStore, sample_vectors: list[list[float]]
    ) -> None:
        """Test retrieving document vectors."""
        doc_id = "doc1"
        original_vector = sample_vectors[0]

        vector_store.index_document(doc_id, original_vector)
        retrieved_vector = vector_store.get_document_vector(doc_id)

        assert retrieved_vector is not None
        # Vectors should be similar (allowing for normalization differences)
        assert len(retrieved_vector) == len(original_vector)

    def test_get_document_vector_not_found(
        self, vector_store: FaissVectorStore
    ) -> None:
        """Test retrieving non-existent document vector."""
        result = vector_store.get_document_vector("nonexistent")
        assert result is None

    def test_remove_document(
        self, vector_store: FaissVectorStore, sample_vectors: list[list[float]]
    ) -> None:
        """Test document removal."""
        # Index multiple documents
        for i, vector in enumerate(sample_vectors):
            vector_store.index_document(f"doc{i}", vector, {"index": i})

        initial_count = vector_store.index.ntotal
        assert initial_count == 3

        # Remove middle document
        success = vector_store.remove_document("doc1")
        assert success is True
        assert vector_store.index.ntotal == initial_count - 1
        assert "doc1" not in vector_store.document_ids
        assert "doc1" not in vector_store.metadata_store

        # Verify remaining documents are still searchable
        results = vector_store.search(sample_vectors[0], k=5)
        doc_ids = {result.document_id for result in results}
        assert "doc0" in doc_ids
        assert "doc2" in doc_ids
        assert "doc1" not in doc_ids

    def test_remove_document_not_found(self, vector_store: FaissVectorStore) -> None:
        """Test removing non-existent document."""
        success = vector_store.remove_document("nonexistent")
        assert success is False

    def test_save_and_load_index(
        self,
        vector_store: FaissVectorStore,
        sample_vectors: list[list[float]],
        sample_metadata: list[dict[str, Any]],
    ) -> None:
        """Test index persistence (save and load)."""
        # Index documents
        for i, (vector, metadata) in enumerate(
            zip(sample_vectors, sample_metadata, strict=False)
        ):
            vector_store.index_document(f"doc{i}", vector, metadata)

        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = Path(temp_dir) / ".kbo_index" / "vault"

            # Save index
            vector_store.save_index(index_path)

            # Verify files were created
            assert index_path.with_suffix(".faiss").exists()
            assert index_path.with_suffix(".json").exists()

            # Create new store and load index
            new_store = FaissVectorStore(dimension=384)
            new_store.load_index(index_path)

            # Verify loaded data
            assert new_store.index.ntotal == vector_store.index.ntotal
            assert new_store.document_ids == vector_store.document_ids
            assert new_store.metadata_store == vector_store.metadata_store

            # Verify search works on loaded index
            results = new_store.search(sample_vectors[0], k=3)
            assert len(results) == 3
            assert results[0].document_id == "doc0"

    def test_load_nonexistent_index(self, vector_store: FaissVectorStore) -> None:
        """Test loading non-existent index."""
        nonexistent_path = Path("/nonexistent/path/index")

        with pytest.raises(VectorStoreError, match="Index file not found"):
            vector_store.load_index(nonexistent_path)

    def test_save_empty_index(self, vector_store: FaissVectorStore) -> None:
        """Test saving empty index."""
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = Path(temp_dir) / "empty_index"

            # Should be able to save empty index
            vector_store.save_index(index_path)

            # Load it back
            new_store = FaissVectorStore(dimension=384)
            new_store.load_index(index_path)

            assert new_store.index.ntotal == 0
            assert len(new_store.document_ids) == 0

    def test_get_index_stats_empty(self, vector_store: FaissVectorStore) -> None:
        """Test index statistics for empty index."""
        stats = vector_store.get_index_stats()

        assert stats["total_documents"] == 0
        assert stats["dimension"] == 384
        assert stats["index_type"] == "IndexFlatIP"
        assert stats["memory_usage_bytes"] == 0
        assert stats["has_metadata"] is False

    def test_get_index_stats_with_data(
        self,
        vector_store: FaissVectorStore,
        sample_vectors: list[list[float]],
        sample_metadata: list[dict[str, Any]],
    ) -> None:
        """Test index statistics with data."""
        # Index documents
        for i, (vector, metadata) in enumerate(
            zip(sample_vectors, sample_metadata, strict=False)
        ):
            vector_store.index_document(f"doc{i}", vector, metadata)

        stats = vector_store.get_index_stats()

        assert stats["total_documents"] == 3
        assert stats["dimension"] == 384
        assert stats["index_type"] == "IndexFlatIP"
        assert stats["memory_usage_bytes"] == 3 * 384 * 4  # 3 docs * 384 dim * 4 bytes
        assert stats["has_metadata"] is True
        assert stats["documents_with_metadata"] == 3

    def test_vector_normalization(self, vector_store: FaissVectorStore) -> None:
        """Test that vectors are properly normalized for cosine similarity."""
        # Create a simple vector
        vector = [3.0, 4.0] + [0.0] * 382  # Length 5 vector padded to 384

        # Normalize it manually
        normalized = vector_store._normalize_vector(vector)

        # Check that it's normalized (length should be 1)
        length = np.linalg.norm(normalized)
        assert abs(length - 1.0) < 1e-6

    def test_metadata_consistency_after_operations(
        self,
        vector_store: FaissVectorStore,
        sample_vectors: list[list[float]],
        sample_metadata: list[dict[str, Any]],
    ) -> None:
        """Test that metadata remains consistent after various operations."""
        # Index documents
        for i, (vector, metadata) in enumerate(
            zip(sample_vectors, sample_metadata, strict=False)
        ):
            vector_store.index_document(f"doc{i}", vector, metadata)

        # Remove one document
        vector_store.remove_document("doc1")

        # Verify metadata consistency
        assert len(vector_store.document_ids) == len(vector_store.metadata_store)
        assert "doc1" not in vector_store.metadata_store

        # Search and verify metadata is returned correctly
        results = vector_store.search(sample_vectors[0], k=5)
        for result in results:
            if result.document_id in vector_store.metadata_store:
                expected_metadata = vector_store.metadata_store[result.document_id]
                assert result.metadata == expected_metadata

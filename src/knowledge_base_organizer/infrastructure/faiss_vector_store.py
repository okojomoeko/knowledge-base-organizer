"""
Faiss-based Vector Store Implementation

This module provides a concrete implementation of the VectorStore interface
using Facebook AI Similarity Search (Faiss) for efficient vector storage
and similarity search operations.

Features:
- In-memory vector indexing with Faiss
- Persistent storage to disk (.kbo_index/vault.index)
- Efficient similarity search with configurable thresholds
- Metadata storage alongside vectors
- Index statistics and management

Supports:
- Requirement 13.1, 13.2: Context-aware linking with semantic similarity
- Requirement 18.1: Content-based relationship discovery
"""

import json
import logging
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from knowledge_base_organizer.domain.services.ai_services import (
    SearchResult,
    VectorStore,
    VectorStoreError,
)

logger = logging.getLogger(__name__)


class FaissVectorStore(VectorStore):
    """
    Faiss-based implementation of VectorStore for efficient vector similarity search.

    Uses Faiss IndexFlatIP (Inner Product) for exact similarity search with
    L2-normalized vectors, which is equivalent to cosine similarity.
    """

    def __init__(self, dimension: int = 384) -> None:
        """
        Initialize the Faiss vector store.

        Args:
            dimension: Vector dimension (default 384 for nomic-embed-text)
        """
        self.dimension = dimension
        self.index: faiss.Index | None = None
        self.document_ids: list[str] = []
        self.metadata_store: dict[str, dict[str, Any]] = {}
        self._initialize_index()

    def _initialize_index(self) -> None:
        """Initialize a new Faiss index for vector storage."""
        # Use IndexFlatIP for exact cosine similarity search
        # (requires L2-normalized vectors)
        self.index = faiss.IndexFlatIP(self.dimension)
        self.document_ids = []
        self.metadata_store = {}
        logger.debug(f"Initialized Faiss index with dimension {self.dimension}")

    def _normalize_vector(self, vector: list[float]) -> np.ndarray:
        """
        Normalize vector for cosine similarity using IndexFlatIP.

        Args:
            vector: Input vector to normalize

        Returns:
            L2-normalized numpy array
        """
        vec_array = np.array(vector, dtype=np.float32).reshape(1, -1)
        # L2 normalize for cosine similarity with IndexFlatIP
        faiss.normalize_L2(vec_array)
        return vec_array

    def index_document(
        self,
        document_id: str,
        vector: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Index a document vector with optional metadata.

        Args:
            document_id: Unique identifier for the document
            vector: Document embedding vector
            metadata: Optional metadata to store with the vector

        Raises:
            VectorStoreError: If indexing fails
        """
        if self.index is None:
            raise VectorStoreError("Index not initialized")

        if len(vector) != self.dimension:
            raise VectorStoreError(
                f"Vector dimension {len(vector)} does not match "
                f"index dimension {self.dimension}"
            )

        try:
            # Check if document already exists and update
            if document_id in self.document_ids:
                # Remove existing document
                self.remove_document(document_id)

            # Normalize and add vector
            normalized_vector = self._normalize_vector(vector)
            self.index.add(normalized_vector)

            # Store document ID and metadata
            self.document_ids.append(document_id)
            if metadata:
                self.metadata_store[document_id] = metadata

            logger.debug(f"Indexed document {document_id}")

        except Exception as e:
            raise VectorStoreError(
                f"Failed to index document {document_id}: {e}"
            ) from e

    def search(
        self, query_vector: list[float], k: int = 10, threshold: float | None = None
    ) -> list[SearchResult]:
        """
        Search for similar documents using vector similarity.

        Args:
            query_vector: Query embedding vector
            k: Number of results to return
            threshold: Minimum similarity threshold (cosine similarity)

        Returns:
            List of SearchResult objects ordered by similarity

        Raises:
            VectorStoreError: If search fails
        """
        if self.index is None or self.index.ntotal == 0:
            return []

        if len(query_vector) != self.dimension:
            raise VectorStoreError(
                f"Query vector dimension {len(query_vector)} does not match "
                f"index dimension {self.dimension}"
            )

        try:
            # Normalize query vector
            normalized_query = self._normalize_vector(query_vector)

            # Search for k nearest neighbors
            search_k = min(k, self.index.ntotal)
            similarities, indices = self.index.search(normalized_query, search_k)

            # Convert results to SearchResult objects
            results = []
            for similarity, idx in zip(similarities[0], indices[0], strict=False):
                # Skip invalid indices
                if idx == -1 or idx >= len(self.document_ids):
                    continue

                # Apply threshold filter if specified
                if threshold is not None and similarity < threshold:
                    continue

                document_id = self.document_ids[idx]
                metadata = self.metadata_store.get(document_id, {})

                results.append(
                    SearchResult(
                        document_id=document_id,
                        similarity_score=float(similarity),
                        metadata=metadata,
                    )
                )

            logger.debug(f"Found {len(results)} results for query")
            return results

        except Exception as e:
            raise VectorStoreError(f"Search failed: {e}") from e

    def get_document_vector(self, document_id: str) -> list[float] | None:
        """
        Retrieve the vector for a specific document.

        Args:
            document_id: Document identifier

        Returns:
            Document vector or None if not found
        """
        if document_id not in self.document_ids:
            return None

        try:
            # Find document index
            doc_index = self.document_ids.index(document_id)

            # Reconstruct vector from index
            if self.index is not None and doc_index < self.index.ntotal:
                vector = self.index.reconstruct(doc_index)
                return vector.tolist()

            return None

        except Exception as e:
            logger.warning(f"Failed to retrieve vector for {document_id}: {e}")
            return None

    def remove_document(self, document_id: str) -> bool:
        """
        Remove a document from the index.

        Note: Faiss doesn't support efficient removal, so we rebuild the index
        without the target document.

        Args:
            document_id: Document identifier to remove

        Returns:
            True if document was removed, False if not found
        """
        if document_id not in self.document_ids:
            return False

        try:
            # Find document index
            doc_index = self.document_ids.index(document_id)

            # Rebuild index without the target document
            if self.index is not None and self.index.ntotal > 0:
                # Extract all vectors except the target
                all_vectors = []
                new_document_ids = []
                new_metadata_store = {}

                for i, doc_id in enumerate(self.document_ids):
                    if i != doc_index:
                        vector = self.index.reconstruct(i)
                        all_vectors.append(vector)
                        new_document_ids.append(doc_id)
                        if doc_id in self.metadata_store:
                            new_metadata_store[doc_id] = self.metadata_store[doc_id]

                # Rebuild index
                self._initialize_index()
                if all_vectors:
                    vectors_array = np.vstack(all_vectors)
                    self.index.add(vectors_array)

                self.document_ids = new_document_ids
                self.metadata_store = new_metadata_store

            # Remove from metadata if it exists
            self.metadata_store.pop(document_id, None)

            logger.debug(f"Removed document {document_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to remove document {document_id}: {e}")
            return False

    def save_index(self, path: Path) -> None:
        """
        Save the vector index to disk.

        Saves both the Faiss index and associated metadata to separate files.

        Args:
            path: Path where to save the index (without extension)

        Raises:
            VectorStoreError: If saving fails
        """
        if self.index is None:
            raise VectorStoreError("No index to save")

        try:
            # Ensure directory exists
            path.parent.mkdir(parents=True, exist_ok=True)

            # Save Faiss index
            index_path = path.with_suffix(".faiss")
            faiss.write_index(self.index, str(index_path))

            # Save metadata (document IDs and metadata store)
            metadata_path = path.with_suffix(".json")
            metadata = {
                "document_ids": self.document_ids,
                "metadata_store": self.metadata_store,
                "dimension": self.dimension,
                "index_type": "IndexFlatIP",
            }

            with metadata_path.open("w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved index to {index_path} and metadata to {metadata_path}")

        except Exception as e:
            raise VectorStoreError(f"Failed to save index: {e}") from e

    def load_index(self, path: Path) -> None:
        """
        Load a vector index from disk.

        Loads both the Faiss index and associated metadata from separate files.

        Args:
            path: Path to the saved index (without extension)

        Raises:
            VectorStoreError: If loading fails
        """
        index_path = path.with_suffix(".faiss")
        metadata_path = path.with_suffix(".json")

        if not index_path.exists():
            raise VectorStoreError(f"Index file not found: {index_path}")

        if not metadata_path.exists():
            raise VectorStoreError(f"Metadata file not found: {metadata_path}")

        try:
            # Load Faiss index
            self.index = faiss.read_index(str(index_path))

            # Load metadata
            with metadata_path.open(encoding="utf-8") as f:
                metadata = json.load(f)

            self.document_ids = metadata["document_ids"]
            self.metadata_store = metadata["metadata_store"]
            self.dimension = metadata["dimension"]

            # Validate consistency
            if self.index.ntotal != len(self.document_ids):
                raise VectorStoreError(
                    f"Index size ({self.index.ntotal}) does not match "
                    f"document count ({len(self.document_ids)})"
                )

            logger.info(
                f"Loaded index from {index_path} with {self.index.ntotal} documents"
            )

        except Exception as e:
            raise VectorStoreError(f"Failed to load index: {e}") from e

    def get_index_stats(self) -> dict[str, Any]:
        """
        Get statistics about the current index.

        Returns:
            Dictionary with index size, dimension, and other stats
        """
        if self.index is None:
            return {
                "total_documents": 0,
                "dimension": self.dimension,
                "index_type": "IndexFlatIP",
                "memory_usage_bytes": 0,
                "has_metadata": False,
            }

        return {
            "total_documents": self.index.ntotal,
            "dimension": self.dimension,
            "index_type": "IndexFlatIP",
            "memory_usage_bytes": self.index.ntotal * self.dimension * 4,  # float32
            "has_metadata": len(self.metadata_store) > 0,
            "documents_with_metadata": len(self.metadata_store),
        }

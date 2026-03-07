# backend/rag/vector_store.py
"""ChromaDB vector store wrapper for the RAG pipeline."""

import chromadb
from chromadb.config import Settings


class FinanceVectorStore:
    """Wrapper around ChromaDB for storing and retrieving finance document embeddings."""

    def __init__(self, persist_dir: str = "./chroma_db", collection_name: str = "finance_docs"):
        """Initialize or load a ChromaDB collection.

        Args:
            persist_dir: Directory for persistent storage.
            collection_name: Name of the ChromaDB collection.
        """
        self._client = chromadb.Client(Settings(
            anonymized_telemetry=False,
            is_persistent=True,
            persist_directory=persist_dir,
        ))
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def collection(self):
        return self._collection

    def upsert(self, ids: list, documents: list, metadatas: list, embeddings: list = None):
        """Add or update documents in the vector store.

        Args:
            ids: Unique IDs for each document.
            documents: Text content for each document.
            metadatas: Metadata dicts for each document.
            embeddings: Optional pre-computed embedding vectors.
        """
        kwargs = {
            "ids": ids,
            "documents": documents,
            "metadatas": metadatas,
        }
        if embeddings:
            kwargs["embeddings"] = embeddings
        self._collection.upsert(**kwargs)

    def query(
        self,
        query_embeddings: list = None,
        query_texts: list = None,
        n_results: int = 10,
        where_filter: dict = None,
    ) -> dict:
        """Query the vector store for similar documents.

        Args:
            query_embeddings: Embedding vector(s) to search with.
            query_texts: Text(s) to search with (if no embeddings provided).
            n_results: Number of results to return.
            where_filter: Optional metadata filter (e.g., {"doc_type": "transaction"}).

        Returns:
            Dict with keys: ids, documents, metadatas, distances.
        """
        kwargs = {"n_results": min(n_results, self.count() or n_results)}

        if query_embeddings is not None:
            kwargs["query_embeddings"] = query_embeddings
        elif query_texts is not None:
            kwargs["query_texts"] = query_texts

        if where_filter:
            kwargs["where"] = where_filter

        return self._collection.query(**kwargs)

    def delete(self, ids: list):
        """Delete documents by ID.

        Args:
            ids: List of document IDs to delete.
        """
        self._collection.delete(ids=ids)

    def count(self) -> int:
        """Return the number of documents in the collection."""
        return self._collection.count()

    def reset(self):
        """Delete all documents from the collection."""
        if self.count() > 0:
            # Get all IDs and delete them
            all_docs = self._collection.get()
            if all_docs["ids"]:
                self._collection.delete(ids=all_docs["ids"])

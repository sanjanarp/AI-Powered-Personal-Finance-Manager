import unittest
from unittest.mock import patch, MagicMock
from backend.rag.vector_store import FinanceVectorStore


class TestFinanceVectorStore(unittest.TestCase):

    @patch("backend.rag.vector_store.chromadb")
    def test_init_creates_collection(self, mock_chromadb):
        mock_client = MagicMock()
        mock_chromadb.Client.return_value = mock_client
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        store = FinanceVectorStore(persist_dir="./test_db", collection_name="test_col")

        mock_chromadb.Client.assert_called_once()
        mock_client.get_or_create_collection.assert_called_once_with(
            name="test_col",
            metadata={"hnsw:space": "cosine"},
        )
        self.assertEqual(store.collection, mock_collection)

    @patch("backend.rag.vector_store.chromadb")
    def test_upsert_without_embeddings(self, mock_chromadb):
        mock_client = MagicMock()
        mock_chromadb.Client.return_value = mock_client
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        store = FinanceVectorStore()
        store.upsert(
            ids=["id1", "id2"],
            documents=["doc1", "doc2"],
            metadatas=[{"type": "a"}, {"type": "b"}],
        )

        mock_collection.upsert.assert_called_once_with(
            ids=["id1", "id2"],
            documents=["doc1", "doc2"],
            metadatas=[{"type": "a"}, {"type": "b"}],
        )

    @patch("backend.rag.vector_store.chromadb")
    def test_upsert_with_embeddings(self, mock_chromadb):
        mock_client = MagicMock()
        mock_chromadb.Client.return_value = mock_client
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        store = FinanceVectorStore()
        embeddings = [[0.1, 0.2], [0.3, 0.4]]
        store.upsert(
            ids=["id1"],
            documents=["doc1"],
            metadatas=[{"type": "a"}],
            embeddings=embeddings,
        )

        mock_collection.upsert.assert_called_once_with(
            ids=["id1"],
            documents=["doc1"],
            metadatas=[{"type": "a"}],
            embeddings=embeddings,
        )

    @patch("backend.rag.vector_store.chromadb")
    def test_query_with_embeddings(self, mock_chromadb):
        mock_client = MagicMock()
        mock_chromadb.Client.return_value = mock_client
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_collection.count.return_value = 10
        mock_collection.query.return_value = {
            "ids": [["id1"]],
            "documents": [["doc1"]],
            "metadatas": [[{"type": "a"}]],
            "distances": [[0.1]],
        }

        store = FinanceVectorStore()
        result = store.query(query_embeddings=[[0.1, 0.2]], n_results=5)

        mock_collection.query.assert_called_once_with(
            query_embeddings=[[0.1, 0.2]],
            n_results=5,
        )
        self.assertEqual(result["ids"], [["id1"]])

    @patch("backend.rag.vector_store.chromadb")
    def test_query_with_metadata_filter(self, mock_chromadb):
        mock_client = MagicMock()
        mock_chromadb.Client.return_value = mock_client
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_collection.count.return_value = 10
        mock_collection.query.return_value = {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        store = FinanceVectorStore()
        store.query(query_texts=["test"], n_results=3, where_filter={"doc_type": "transaction"})

        mock_collection.query.assert_called_once_with(
            query_texts=["test"],
            n_results=3,
            where={"doc_type": "transaction"},
        )

    @patch("backend.rag.vector_store.chromadb")
    def test_delete(self, mock_chromadb):
        mock_client = MagicMock()
        mock_chromadb.Client.return_value = mock_client
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        store = FinanceVectorStore()
        store.delete(ids=["id1", "id2"])

        mock_collection.delete.assert_called_once_with(ids=["id1", "id2"])

    @patch("backend.rag.vector_store.chromadb")
    def test_count(self, mock_chromadb):
        mock_client = MagicMock()
        mock_chromadb.Client.return_value = mock_client
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_collection.count.return_value = 42

        store = FinanceVectorStore()
        self.assertEqual(store.count(), 42)

    @patch("backend.rag.vector_store.chromadb")
    def test_reset(self, mock_chromadb):
        mock_client = MagicMock()
        mock_chromadb.Client.return_value = mock_client
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_collection.count.return_value = 5
        mock_collection.get.return_value = {"ids": ["id1", "id2", "id3", "id4", "id5"]}

        store = FinanceVectorStore()
        store.reset()

        mock_collection.delete.assert_called_once_with(ids=["id1", "id2", "id3", "id4", "id5"])


if __name__ == "__main__":
    unittest.main()

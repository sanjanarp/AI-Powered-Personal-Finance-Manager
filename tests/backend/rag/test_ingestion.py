import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
from backend.rag.ingestion import (
    ingest_transactions,
    ingest_monthly_summary,
    ingest_budgets,
    ingest_policy_docs,
    ingest_all,
)


class TestIngestTransactions(unittest.TestCase):

    @patch("backend.rag.ingestion.get_embeddings_batch")
    @patch("backend.rag.ingestion.chunk_transactions")
    def test_ingest_transactions(self, mock_chunk, mock_embed):
        mock_chunk.return_value = [
            {"id": "tx1", "text": "2025-03-01 | Uber | $18.25", "metadata": {"doc_type": "transaction"}},
            {"id": "tx2", "text": "2025-03-02 | Netflix | $15.99", "metadata": {"doc_type": "transaction"}},
        ]
        mock_embed.return_value = [[0.1, 0.2], [0.3, 0.4]]

        mock_store = MagicMock()
        transactions = [{"name": "Uber"}, {"name": "Netflix"}]

        ingest_transactions(transactions, mock_store, "fake-key")

        mock_chunk.assert_called_once_with(transactions)
        mock_embed.assert_called_once_with(
            ["2025-03-01 | Uber | $18.25", "2025-03-02 | Netflix | $15.99"],
            "fake-key",
        )
        mock_store.upsert.assert_called_once_with(
            ids=["tx1", "tx2"],
            documents=["2025-03-01 | Uber | $18.25", "2025-03-02 | Netflix | $15.99"],
            metadatas=[{"doc_type": "transaction"}, {"doc_type": "transaction"}],
            embeddings=[[0.1, 0.2], [0.3, 0.4]],
        )

    @patch("backend.rag.ingestion.get_embeddings_batch")
    @patch("backend.rag.ingestion.chunk_transactions")
    def test_ingest_empty_transactions(self, mock_chunk, mock_embed):
        mock_chunk.return_value = []
        mock_store = MagicMock()

        ingest_transactions([], mock_store, "fake-key")

        mock_embed.assert_not_called()
        mock_store.upsert.assert_not_called()


class TestIngestMonthlySummary(unittest.TestCase):

    @patch("backend.rag.ingestion.get_embeddings_batch")
    @patch("backend.rag.ingestion.chunk_monthly_summary")
    def test_ingest_summary(self, mock_chunk, mock_embed):
        mock_chunk.return_value = {
            "id": "sum1",
            "text": "March summary: $500",
            "metadata": {"doc_type": "monthly_summary", "month": "2025-03"},
        }
        mock_embed.return_value = [[0.5, 0.6]]

        mock_store = MagicMock()
        transactions = [
            {"date": "2025-03-01", "name": "Test", "amount": 50.0, "category": ["Food"]},
            {"date": "2025-03-15", "name": "Test2", "amount": 100.0, "category": "Transport"},
        ]

        ingest_monthly_summary("2025-03", transactions, mock_store, "fake-key")

        mock_chunk.assert_called_once()
        mock_store.upsert.assert_called_once()

    @patch("backend.rag.ingestion.get_embeddings_batch")
    def test_ingest_summary_no_matching_transactions(self, mock_embed):
        mock_store = MagicMock()
        transactions = [
            {"date": "2025-04-01", "name": "Test", "amount": 50.0},
        ]

        ingest_monthly_summary("2025-03", transactions, mock_store, "fake-key")

        mock_embed.assert_not_called()
        mock_store.upsert.assert_not_called()


class TestIngestBudgets(unittest.TestCase):

    @patch("backend.rag.ingestion.get_embeddings_batch")
    @patch("backend.rag.ingestion.chunk_budget_goals")
    def test_ingest_budgets(self, mock_chunk, mock_embed):
        mock_chunk.return_value = [
            {"id": "bg1", "text": "Budget: Food $400", "metadata": {"doc_type": "budget_goal"}},
        ]
        mock_embed.return_value = [[0.7, 0.8]]

        mock_store = MagicMock()
        ingest_budgets({"Food": 400.0}, "2025-03", mock_store, "fake-key")

        mock_chunk.assert_called_once_with({"Food": 400.0}, "2025-03")
        mock_store.upsert.assert_called_once()

    @patch("backend.rag.ingestion.get_embeddings_batch")
    @patch("backend.rag.ingestion.chunk_budget_goals")
    def test_ingest_empty_budgets(self, mock_chunk, mock_embed):
        mock_chunk.return_value = []
        mock_store = MagicMock()

        ingest_budgets({}, "2025-03", mock_store, "fake-key")

        mock_embed.assert_not_called()
        mock_store.upsert.assert_not_called()


class TestIngestPolicyDocs(unittest.TestCase):

    @patch("backend.rag.ingestion.get_embeddings_batch")
    @patch("backend.rag.ingestion.chunk_policy_doc")
    @patch("builtins.open", new_callable=mock_open, read_data="# Budgeting Rules\nSome content here.")
    @patch("os.listdir")
    @patch("os.path.isdir")
    def test_ingest_policy_docs(self, mock_isdir, mock_listdir, mock_file, mock_chunk, mock_embed):
        mock_isdir.return_value = True
        mock_listdir.return_value = ["budgeting_rules.md", "credit.md", "readme.txt"]

        mock_chunk.return_value = [
            {"id": "p1", "text": "Budgeting rules chunk", "metadata": {"doc_type": "policy", "source_file": "budgeting_rules.md"}},
        ]
        mock_embed.return_value = [[0.9, 1.0]]

        mock_store = MagicMock()
        ingest_policy_docs(mock_store, "fake-key")

        # Should only process .md files (2 out of 3)
        self.assertEqual(mock_chunk.call_count, 2)
        mock_store.upsert.assert_called_once()

    @patch("os.path.isdir")
    def test_ingest_no_knowledge_base_dir(self, mock_isdir):
        mock_isdir.return_value = False
        mock_store = MagicMock()

        ingest_policy_docs(mock_store, "fake-key")

        mock_store.upsert.assert_not_called()


class TestIngestAll(unittest.TestCase):

    @patch("backend.rag.ingestion.ingest_policy_docs")
    @patch("backend.rag.ingestion.ingest_budgets")
    @patch("backend.rag.ingestion.ingest_monthly_summary")
    @patch("backend.rag.ingestion.ingest_transactions")
    def test_ingest_all_with_budgets(self, mock_tx, mock_summary, mock_budgets, mock_policy):
        mock_store = MagicMock()
        transactions = [
            {"date": "2025-03-01", "name": "Test", "amount": 50.0},
        ]

        ingest_all(
            transactions=transactions,
            vector_store=mock_store,
            api_key="fake-key",
            budget_limits={"Food": 400.0},
            month="2025-03",
        )

        mock_tx.assert_called_once_with(transactions, mock_store, "fake-key")
        mock_summary.assert_called_once_with("2025-03", transactions, mock_store, "fake-key")
        mock_budgets.assert_called_once_with({"Food": 400.0}, "2025-03", mock_store, "fake-key")
        mock_policy.assert_called_once_with(mock_store, "fake-key")

    @patch("backend.rag.ingestion.ingest_policy_docs")
    @patch("backend.rag.ingestion.ingest_budgets")
    @patch("backend.rag.ingestion.ingest_monthly_summary")
    @patch("backend.rag.ingestion.ingest_transactions")
    def test_ingest_all_without_budgets(self, mock_tx, mock_summary, mock_budgets, mock_policy):
        mock_store = MagicMock()
        transactions = [
            {"date": "2025-03-01", "name": "Test", "amount": 50.0},
        ]

        ingest_all(
            transactions=transactions,
            vector_store=mock_store,
            api_key="fake-key",
        )

        mock_tx.assert_called_once()
        mock_summary.assert_called_once()
        mock_budgets.assert_not_called()
        mock_policy.assert_called_once()


if __name__ == "__main__":
    unittest.main()

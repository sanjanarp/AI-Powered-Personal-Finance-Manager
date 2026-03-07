import unittest
from unittest.mock import patch, MagicMock
from backend.rag.retriever import retrieve_context, format_retrieved_context


class TestFormatRetrievedContext(unittest.TestCase):

    def test_empty_documents(self):
        result = format_retrieved_context([], [])
        self.assertEqual(result, "")

    def test_transaction_formatting(self):
        docs = ["2025-03-01 | Uber | $18.25 | Transport"]
        metas = [{"doc_type": "transaction"}]
        result = format_retrieved_context(docs, metas)

        self.assertIn("=== Relevant Transactions ===", result)
        self.assertIn("Uber", result)
        self.assertIn("$18.25", result)

    def test_monthly_summary_formatting(self):
        docs = ["March 2025 summary: Total $500"]
        metas = [{"doc_type": "monthly_summary"}]
        result = format_retrieved_context(docs, metas)

        self.assertIn("=== Monthly Summaries ===", result)
        self.assertIn("March 2025", result)

    def test_budget_goal_formatting(self):
        docs = ["Budget goal for 2025-03: Food — limit $400.00/month"]
        metas = [{"doc_type": "budget_goal"}]
        result = format_retrieved_context(docs, metas)

        self.assertIn("=== Budget Goals ===", result)
        self.assertIn("Food", result)

    def test_policy_formatting(self):
        docs = ["50/30/20 rule: 50% needs, 30% wants, 20% savings"]
        metas = [{"doc_type": "policy", "source_file": "budgeting_rules.md"}]
        result = format_retrieved_context(docs, metas)

        self.assertIn("=== Financial Guidelines ===", result)
        self.assertIn("[budgeting_rules.md]", result)

    def test_mixed_doc_types(self):
        docs = [
            "2025-03-01 | Uber | $18.25",
            "March summary: $500 total",
            "Budget: Food $400",
            "50/30/20 rule",
        ]
        metas = [
            {"doc_type": "transaction"},
            {"doc_type": "monthly_summary"},
            {"doc_type": "budget_goal"},
            {"doc_type": "policy", "source_file": "rules.md"},
        ]
        result = format_retrieved_context(docs, metas)

        self.assertIn("=== Relevant Transactions ===", result)
        self.assertIn("=== Monthly Summaries ===", result)
        self.assertIn("=== Budget Goals ===", result)
        self.assertIn("=== Financial Guidelines ===", result)


class TestRetrieveContext(unittest.TestCase):

    @patch("backend.rag.retriever.get_embedding")
    def test_empty_store_returns_empty(self, mock_embed):
        mock_store = MagicMock()
        mock_store.count.return_value = 0

        context, results = retrieve_context("test query", mock_store, "fake-key")

        self.assertEqual(context, "")
        self.assertEqual(results, {})
        mock_embed.assert_not_called()

    @patch("backend.rag.retriever.get_embedding")
    def test_retrieval_with_results(self, mock_embed):
        mock_embed.return_value = [0.1, 0.2, 0.3]

        mock_store = MagicMock()
        mock_store.count.return_value = 10
        mock_store.query.return_value = {
            "ids": [["id1", "id2"]],
            "documents": [["2025-03-01 | Uber | $18.25", "March summary"]],
            "metadatas": [[{"doc_type": "transaction"}, {"doc_type": "monthly_summary"}]],
            "distances": [[0.1, 0.2]],
        }

        context, results = retrieve_context("spending", mock_store, "fake-key", n_results=5)

        mock_embed.assert_called_once_with("spending", "fake-key")
        mock_store.query.assert_called_once_with(
            query_embeddings=[[0.1, 0.2, 0.3]],
            n_results=5,
            where_filter=None,
        )
        self.assertIn("Uber", context)
        self.assertIn("March summary", context)

    @patch("backend.rag.retriever.get_embedding")
    def test_retrieval_with_filter(self, mock_embed):
        mock_embed.return_value = [0.1]

        mock_store = MagicMock()
        mock_store.count.return_value = 5
        mock_store.query.return_value = {
            "ids": [["id1"]],
            "documents": [["doc1"]],
            "metadatas": [[{"doc_type": "transaction"}]],
            "distances": [[0.05]],
        }

        filters = {"doc_type": "transaction"}
        retrieve_context("test", mock_store, "key", filters=filters)

        mock_store.query.assert_called_once_with(
            query_embeddings=[[0.1]],
            n_results=10,
            where_filter=filters,
        )


if __name__ == "__main__":
    unittest.main()

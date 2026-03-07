import unittest
from backend.rag.chunker import (
    chunk_transactions,
    chunk_monthly_summary,
    chunk_budget_goals,
    chunk_policy_doc,
)


class TestChunkTransactions(unittest.TestCase):

    def test_basic_transaction_chunking(self):
        transactions = [
            {
                "date": "2025-03-02",
                "name": "Uber",
                "amount": 18.25,
                "category": ["Transportation"],
                "account_id": "acc_123",
                "source": "plaid",
            }
        ]
        chunks = chunk_transactions(transactions)
        self.assertEqual(len(chunks), 1)

        chunk = chunks[0]
        self.assertIn("Uber", chunk["text"])
        self.assertIn("$18.25", chunk["text"])
        self.assertIn("Transportation", chunk["text"])
        self.assertEqual(chunk["metadata"]["doc_type"], "transaction")
        self.assertEqual(chunk["metadata"]["month"], "2025-03")
        self.assertEqual(chunk["metadata"]["category"], "Transportation")
        self.assertEqual(chunk["metadata"]["source"], "plaid")
        self.assertEqual(chunk["metadata"]["merchant"], "Uber")
        self.assertEqual(chunk["metadata"]["amount"], 18.25)

    def test_list_category_extraction(self):
        transactions = [
            {"date": "2025-01-15", "name": "Starbucks", "amount": 5.50, "category": ["Food and Drink", "Coffee"]}
        ]
        chunks = chunk_transactions(transactions)
        self.assertEqual(chunks[0]["metadata"]["category"], "Food and Drink")

    def test_string_category(self):
        transactions = [
            {"date": "2025-02-10", "name": "Netflix", "amount": 15.99, "category": "Entertainment"}
        ]
        chunks = chunk_transactions(transactions)
        self.assertEqual(chunks[0]["metadata"]["category"], "Entertainment")

    def test_empty_category_defaults(self):
        transactions = [
            {"date": "2025-03-01", "name": "Unknown Store", "amount": 42.00}
        ]
        chunks = chunk_transactions(transactions)
        self.assertEqual(chunks[0]["metadata"]["category"], "Uncategorized")

    def test_multiple_transactions(self):
        transactions = [
            {"date": "2025-03-01", "name": "Store A", "amount": 10.0},
            {"date": "2025-03-02", "name": "Store B", "amount": 20.0},
            {"date": "2025-04-01", "name": "Store C", "amount": 30.0},
        ]
        chunks = chunk_transactions(transactions)
        self.assertEqual(len(chunks), 3)
        # Each chunk should have a unique ID
        ids = [c["id"] for c in chunks]
        self.assertEqual(len(set(ids)), 3)

    def test_empty_transactions(self):
        chunks = chunk_transactions([])
        self.assertEqual(len(chunks), 0)

    def test_negative_amount_becomes_positive(self):
        transactions = [
            {"date": "2025-03-01", "name": "Refund", "amount": -25.50}
        ]
        chunks = chunk_transactions(transactions)
        self.assertIn("$25.50", chunks[0]["text"])
        self.assertEqual(chunks[0]["metadata"]["amount"], 25.50)


class TestChunkMonthlySummary(unittest.TestCase):

    def test_basic_summary(self):
        category_totals = {"Food": 200.0, "Transport": 100.0, "Entertainment": 50.0}
        chunk = chunk_monthly_summary("2025-03", category_totals, 350.0)

        self.assertIn("2025-03", chunk["text"])
        self.assertIn("$350.00", chunk["text"])
        self.assertIn("Food", chunk["text"])
        self.assertEqual(chunk["metadata"]["doc_type"], "monthly_summary")
        self.assertEqual(chunk["metadata"]["month"], "2025-03")

    def test_top_category_identified(self):
        category_totals = {"Shopping": 500.0, "Bills": 300.0}
        chunk = chunk_monthly_summary("2025-01", category_totals, 800.0)
        self.assertIn("Top spending category: Shopping", chunk["text"])

    def test_zero_total_no_division_error(self):
        chunk = chunk_monthly_summary("2025-06", {"Misc": 0.0}, 0.0)
        self.assertIn("$0.00", chunk["text"])


class TestChunkBudgetGoals(unittest.TestCase):

    def test_basic_budget_chunks(self):
        budgets = {"Food": 400.0, "Transport": 150.0}
        chunks = chunk_budget_goals(budgets, "2025-03")

        self.assertEqual(len(chunks), 2)
        self.assertTrue(any("Food" in c["text"] for c in chunks))
        self.assertTrue(any("$400.00" in c["text"] for c in chunks))

        for c in chunks:
            self.assertEqual(c["metadata"]["doc_type"], "budget_goal")
            self.assertEqual(c["metadata"]["month"], "2025-03")

    def test_empty_budgets(self):
        chunks = chunk_budget_goals({}, "2025-03")
        self.assertEqual(len(chunks), 0)


class TestChunkPolicyDoc(unittest.TestCase):

    def test_short_doc_single_chunk(self):
        content = "This is a short policy document about budgeting."
        chunks = chunk_policy_doc("budgeting.md", content)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["metadata"]["doc_type"], "policy")
        self.assertEqual(chunks[0]["metadata"]["source_file"], "budgeting.md")

    def test_long_doc_multiple_chunks(self):
        # Create content that's larger than chunk_size
        paragraphs = [f"Paragraph {i}: " + "x" * 200 for i in range(10)]
        content = "\n\n".join(paragraphs)
        chunks = chunk_policy_doc("long_doc.md", content, chunk_size=500, overlap=100)

        self.assertGreater(len(chunks), 1)
        # All chunks should have sequential chunk_index
        for i, chunk in enumerate(chunks):
            self.assertEqual(chunk["metadata"]["chunk_index"], i)

    def test_empty_content(self):
        chunks = chunk_policy_doc("empty.md", "")
        self.assertEqual(len(chunks), 0)

    def test_whitespace_only_content(self):
        chunks = chunk_policy_doc("blank.md", "   \n\n  ")
        self.assertEqual(len(chunks), 0)


if __name__ == "__main__":
    unittest.main()

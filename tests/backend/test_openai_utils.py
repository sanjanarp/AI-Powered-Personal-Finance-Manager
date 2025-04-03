import unittest
from unittest.mock import patch
from backend.utils.openai_utils import get_summary_and_advice, extract_expense_json

class TestOpenAIUtils(unittest.TestCase):
    @patch("backend.utils.openai_utils.openai.ChatCompletion.create")
    def test_get_summary_and_advice(self, mock_openai):
        mock_openai.return_value = {
            "choices": [{"message": {"content": "Mocked summary"}}]
        }
        result = get_summary_and_advice("Mocked text", "mocked_api_key")
        self.assertEqual(result, "Mocked summary")

    @patch("backend.utils.openai_utils.openai.ChatCompletion.create")
    def test_extract_expense_json(self, mock_openai):
        mock_openai.return_value = {
            "choices": [{"message": {"content": '{"Food": 100, "Transport": 50}'}}]
        }
        result = extract_expense_json("Mocked text", "mocked_api_key")
        self.assertEqual(result, {"Food": 100, "Transport": 50})

if __name__ == "__main__":
    unittest.main()
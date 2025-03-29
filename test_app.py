import unittest
from unittest.mock import patch, MagicMock
import json
import pandas as pd
from io import BytesIO
from app import extract_text_from_pdfs, get_summary_and_advice, ask_followup_question
import openai

class TestApp(unittest.TestCase):

    @patch("PyPDF2.PdfReader")
    def test_extract_text_from_pdfs(self, mock_pdf_reader):
        mock_pdf_reader.return_value.pages = [MagicMock(extract_text=lambda: "Sample extracted text from PDF.\n")]
        uploaded_files = [BytesIO(b"dummy pdf content")]
        result = extract_text_from_pdfs(uploaded_files).strip()  # Strip trailing newline
        self.assertEqual(result, "Sample extracted text from PDF.")

    @patch("openai.ChatCompletion.create")
    def test_get_summary_and_advice(self, mock_get_summary):
        mock_get_summary.return_value = {
            "choices": [{"message": {"content": "This is a financial summary and advice."}}]
        }
        text = "Sample text from PDF."
        api_key = "test_api_key"  # Mocked, not real
        result = get_summary_and_advice(text, api_key)
        self.assertEqual(result, "This is a financial summary and advice.")

    @patch("openai.ChatCompletion.create")
    def test_ask_followup_question(self, mock_ask_question):
        mock_ask_question.return_value = {
            "choices": [{"message": {"content": "This is a follow-up response."}}]
        }
        question = "What is my total expense?"
        api_key = "test_api_key"  # Mocked, not real
        result = ask_followup_question(question, api_key)
        self.assertEqual(result, "This is a follow-up response.")

    @patch("openai.ChatCompletion.create")
    def test_expense_data_parsing(self, mock_openai_create):
        # Mock OpenAI API response
        mock_openai_create.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"Food": 200, "Transport": 100, "Entertainment": 50}'
                    }
                }
            ]
        }

        # Simulate API call and JSON parsing
        api_key = "test_api_key"
        combined_text = "Sample bank statement text."
        prompt = (
            "Extract categorized expenses from this bank statement."
            " Return only a valid JSON object with category names as keys and total expenses as values."
            " Do NOT include code formatting, markdown, or natural language."
            f"\n\n{combined_text}"
        )

        openai.api_key = api_key
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful financial assistant."},
                {"role": "user", "content": prompt}
            ]
        )

        reply = response["choices"][0]["message"]["content"]
        parsed_data = json.loads(reply)
        self.assertEqual(parsed_data, {"Food": 200, "Transport": 100, "Entertainment": 50})

    def test_expense_data_cleanup(self):
        # Test cleaning up and filtering expense data
        raw_data = {"Food": 200, "Transport": -100, "Entertainment": "50", "Invalid": "abc"}
        cleaned_data = {k: abs(float(v)) for k, v in raw_data.items() if str(v).replace('.', '', 1).isdigit() and float(v) > 0}
        self.assertEqual(cleaned_data, {"Food": 200.0, "Entertainment": 50.0})

    def test_csv_generation(self):
        # Test CSV generation from expense data
        expense_data = {"Food": 200, "Transport": 100, "Entertainment": 50}
        df = pd.DataFrame(list(expense_data.items()), columns=["Category", "Amount"])
        csv_data = df.to_csv(index=False).encode("utf-8")
        self.assertIn(b"Category,Amount", csv_data)
        self.assertIn(b"Food,200", csv_data)
        self.assertIn(b"Transport,100", csv_data)
        self.assertIn(b"Entertainment,50", csv_data)

if __name__ == "__main__":
    unittest.main()
import sys
import os
from io import BytesIO
import unittest
from unittest.mock import patch

# Add the project root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from backend.app import app

class TestApp(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch("backend.routes.advice.get_summary_and_advice")  # Correct path for advice route
    @patch("backend.routes.advice.extract_text_from_pdfs")  # Correct path for advice route
    def test_advice_blueprint_summary(self, mock_extract_text, mock_get_summary):
        """
        Test the /advice/summary endpoint with valid inputs.
        - Mocks the PDF text extraction and OpenAI API response.
        - Does NOT test the actual OpenAI API call or PDF parsing logic.
        """
        mock_extract_text.return_value = "Mocked PDF text"
        mock_get_summary.return_value = "Mocked financial advice summary"

        data = {"api_key": "mocked_api_key"}
        files = {"files": (BytesIO(b"%PDF-1.4\n%Mocked PDF content"), "mocked_file.pdf")}
        response = self.app.post(
            "/advice/summary",
            data={**data, "files": files["files"]},
            content_type="multipart/form-data"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Mocked financial advice summary", response.get_json()["summary"])

    def test_advice_blueprint_missing_files(self):
        """
        Test the /advice/summary endpoint with missing files.
        - Ensures the endpoint returns a 400 error.
        """
        data = {"api_key": "mocked_api_key"}
        response = self.app.post("/advice/summary", data=data)

        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing files or API key", response.get_json()["error"])

    def test_advice_blueprint_missing_api_key(self):
        """
        Test the /advice/summary endpoint with missing API key.
        - Ensures the endpoint returns a 400 error.
        """
        files = {"files": (BytesIO(b"%PDF-1.4\n%Mocked PDF content"), "mocked_file.pdf")}
        response = self.app.post("/advice/summary", data={"files": files["files"]})

        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing files or API key", response.get_json()["error"])

    @patch("backend.routes.analyze.extract_expense_json")  # Correct path for analyze route
    @patch("backend.routes.analyze.extract_text_from_pdfs")  # Correct path for analyze route
    def test_analyze_blueprint(self, mock_extract_text, mock_extract_expense):
        """
        Test the /analyze/ endpoint with valid inputs.
        - Mocks the PDF text extraction and OpenAI API response.
        - Does NOT test the actual OpenAI API call or PDF parsing logic.
        """
        mock_extract_text.return_value = "Mocked PDF text"
        mock_extract_expense.return_value = {"Food": 100, "Transport": 50}

        data = {"api_key": "mocked_api_key"}
        files = {"files": (BytesIO(b"%PDF-1.4\n%Mocked PDF content"), "mocked_file.pdf")}
        response = self.app.post(
            "/analyze/",
            data={**data, "files": files["files"]},
            content_type="multipart/form-data"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"Food": 100, "Transport": 50})

    def test_analyze_blueprint_missing_files(self):
        """
        Test the /analyze/ endpoint with missing files.
        - Ensures the endpoint returns a 400 error.
        """
        data = {"api_key": "mocked_api_key"}
        response = self.app.post("/analyze/", data=data)

        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing files or API key", response.get_json()["error"])

    def test_analyze_blueprint_missing_api_key(self):
        """
        Test the /analyze/ endpoint with missing API key.
        - Ensures the endpoint returns a 400 error.
        """
        files = {"files": (BytesIO(b"%PDF-1.4\n%Mocked PDF content"), "mocked_file.pdf")}
        response = self.app.post("/analyze/", data={"files": files["files"]})

        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing files or API key", response.get_json()["error"])

if __name__ == "__main__":
    unittest.main()
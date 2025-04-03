import unittest
from io import BytesIO
from backend.app import app

class TestAdviceRoutes(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_summary_missing_files(self):
        response = self.app.post("/advice/summary", data={"api_key": "mocked_api_key"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing files or API key", response.get_json()["error"])

    def test_summary_missing_api_key(self):
        files = {"files": (BytesIO(b"%PDF-1.4\n%Mocked PDF content"), "mocked_file.pdf")}
        response = self.app.post("/advice/summary", data={"files": files["files"]})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing files or API key", response.get_json()["error"])

if __name__ == "__main__":
    unittest.main()
import unittest
from unittest.mock import patch, MagicMock

class TestFrontend(unittest.TestCase):
    @patch("requests.post")
    def test_analyze_statements(self, mock_post):
        # Mock the response from requests.post
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {"summary": "Mocked summary"})

        # Simulate the backend call
        mock_post.assert_called()

if __name__ == "__main__":
    unittest.main()
import unittest
from backend.utils.token_utils import count_tokens, trim_to_token_limit

class TestTokenUtils(unittest.TestCase):
    def test_count_tokens(self):
        text = "This is a test."
        token_count = count_tokens(text, model="gpt-4")
        self.assertGreater(token_count, 0)

    def test_trim_to_token_limit(self):
        text = "This is a test." * 1000
        trimmed_text = trim_to_token_limit(text, max_tokens=10, model="gpt-4")
        self.assertLessEqual(len(trimmed_text.split()), 10)

if __name__ == "__main__":
    unittest.main()
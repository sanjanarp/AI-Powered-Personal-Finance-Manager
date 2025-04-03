import unittest

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test modules explicitly
    suite.addTests(loader.loadTestsFromName("tests.backend.test_app"))
    suite.addTests(loader.loadTestsFromName("tests.backend.test_openai_utils"))
    suite.addTests(loader.loadTestsFromName("tests.backend.test_pdf_utils"))
    suite.addTests(loader.loadTestsFromName("tests.backend.test_routes_advice"))
    suite.addTests(loader.loadTestsFromName("tests.backend.test_token_utils"))
    suite.addTests(loader.loadTestsFromName("tests.frontend.test_app"))

    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
import unittest
from io import BytesIO
from backend.utils.pdf_utils import extract_text_from_pdfs
from werkzeug.datastructures import FileStorage

class TestPDFUtils(unittest.TestCase):
    def test_extract_text_from_pdfs(self):
        # Create a mock PDF file
        pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<< /Root 1 0 R >>\nstartxref\n9\n%%EOF"
        mock_file = FileStorage(
            stream=BytesIO(pdf_content),
            filename="mock.pdf",
            content_type="application/pdf"
        )

        # Call the function
        result = extract_text_from_pdfs([mock_file])

        # Assert that the result is empty (since the mock PDF has no text)
        self.assertEqual(result, "")

if __name__ == "__main__":
    unittest.main()
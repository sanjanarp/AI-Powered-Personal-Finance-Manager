import PyPDF2
from typing import List
from werkzeug.datastructures import FileStorage

def extract_text_from_pdfs(files: List[FileStorage]) -> str:
    all_text = ""
    for file in files:
        print(f"\n📄 Reading PDF file: {file.filename}")
        reader = PyPDF2.PdfReader(file)
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            print(f"--- Page {i+1} ---")
            print(text if text else "[No text extracted]")
            if text:
                all_text += text + "\n"
    return all_text

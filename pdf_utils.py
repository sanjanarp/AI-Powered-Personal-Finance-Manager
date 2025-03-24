import PyPDF2
from typing import List
from werkzeug.datastructures import FileStorage

def extract_text_from_pdfs(files: List[FileStorage]) -> str:
    all_text = ""
    for file in files:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                all_text += text + "\n"
    return all_text

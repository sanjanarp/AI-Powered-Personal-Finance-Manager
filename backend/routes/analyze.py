from flask import Blueprint, request, jsonify
from backend.utils.openai_utils import extract_expense_json
from backend.utils.pdf_utils import extract_text_from_pdfs

analyze_bp = Blueprint("analyze", __name__)

@analyze_bp.route("/", methods=["POST"])
def analyze():
    files = request.files.getlist("files")
    api_key = request.form.get("api_key")

    if not files or not api_key:
        return jsonify({"error": "Missing files or API key"}), 400

    try:
        print("📄 Extracting text from PDFs...")
        text = extract_text_from_pdfs(files)
        print(f"Extracted text: {text[:100]}")  # Log the first 100 characters

        result = extract_expense_json(text, api_key)
        print(f"Extracted expenses: {result}")

        return jsonify(result)
    except Exception as e:
        print(f"Error in /analyze: {str(e)}")
        return jsonify({"error": str(e)}), 500

@analyze_bp.route('/', methods=['GET'])
def get_analysis():
    return jsonify({"message": "Analyze endpoint is working!"}), 200

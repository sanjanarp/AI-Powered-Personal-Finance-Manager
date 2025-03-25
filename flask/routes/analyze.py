from flask import Blueprint, request, jsonify
from flask.utils.pdf_utils import extract_text_from_pdfs
from flask.utils.openai_utils import extract_expense_json

analyze_bp = Blueprint("analyze", __name__)

@analyze_bp.route("/", methods=["POST"])
def analyze():
    files = request.files.getlist("files")
    api_key = request.form.get("api_key")

    if not files or not api_key:
        return jsonify({"error": "Missing files or API key"}), 400

    try:
        text = extract_text_from_pdfs(files)
        result = extract_expense_json(text, api_key)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

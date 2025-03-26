from flask import Blueprint, request, jsonify
from utils.pdf_utils import extract_text_from_pdfs
from utils.openai_utils import get_summary_and_advice, ask_followup_question
from utils.token_utils import trim_to_token_limit

advice_bp = Blueprint("advice", __name__)

@advice_bp.route("/summary", methods=["POST"])
def summary():
    api_key = request.form.get("api_key")
    files = request.files.getlist("files")

    if not files or not api_key:
        return jsonify({"error": "Missing files or API key"}), 400

    try:
        full_text = extract_text_from_pdfs(files)
        MAX_TOKENS = 13000  # GPT-4 safety limit
        trimmed_text = trim_to_token_limit(full_text, max_tokens=MAX_TOKENS)
        summary = get_summary_and_advice(trimmed_text, api_key)
        return jsonify({"summary": summary})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@advice_bp.route("/followup", methods=["POST"])
def followup():
    question = request.form.get("question")
    api_key = request.form.get("api_key")
    if not question or not api_key:
        return jsonify({"error": "Missing question or API key"}), 400

    try:
        reply = ask_followup_question(question, api_key)
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

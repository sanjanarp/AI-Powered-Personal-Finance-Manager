from flask import Blueprint, request, jsonify
from flask.utils.openai_utils import get_summary_and_advice, ask_followup_question

advice_bp = Blueprint("advice", __name__)

@advice_bp.route("/summary", methods=["POST"])
def summary():
    text = request.form.get("text")
    api_key = request.form.get("api_key")
    if not text or not api_key:
        return jsonify({"error": "Missing text or API key"}), 400

    try:
        summary = get_summary_and_advice(text, api_key)
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

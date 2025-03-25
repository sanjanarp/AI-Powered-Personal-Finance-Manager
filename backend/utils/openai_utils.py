import openai
import json
import re

def get_summary_and_advice(pdf_text: str, api_key: str) -> str:
    openai.api_key = api_key
    messages = [
        {
            "role": "system",
            "content": (
                "You are a financial advisor. Analyze the following bank statement text and provide a summary "
                "of expenses, deposits, fixed and unfixed costs. Then, offer tailored financial advice and ask "
                "if the user has any follow-up questions."
            )
        },
        {"role": "user", "content": f"Please analyze the following bank statements:\n\n{pdf_text}"}
    ]
    response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
    return response["choices"][0]["message"]["content"]

def ask_followup_question(question: str, api_key: str) -> str:
    openai.api_key = api_key
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful financial advisor."},
            {"role": "user", "content": question}
        ]
    )
    return response["choices"][0]["message"]["content"]

def extract_expense_json(text: str, api_key: str):
    openai.api_key = api_key
    prompt = (
        "Extract categorized expenses from this bank statement. "
        "Return only a valid JSON object with category names as keys and total expenses as values. "
        "Do NOT include markdown, explanations, or code formatting.\n\n" + text
    )

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful financial assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    reply = response["choices"][0]["message"]["content"]

    match = re.search(r"\{.*?\}", reply, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())
            return {k: abs(float(v)) for k, v in parsed.items() if float(v) > 0}
        except:
            raise ValueError("Invalid JSON format or data")
    else:
        raise ValueError("No valid JSON dictionary found in GPT response.")

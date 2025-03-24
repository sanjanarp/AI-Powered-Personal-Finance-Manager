import openai

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
        {
            "role": "user",
            "content": f"Please analyze the following bank statements:\n\n{pdf_text}"
        }
    ]
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
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

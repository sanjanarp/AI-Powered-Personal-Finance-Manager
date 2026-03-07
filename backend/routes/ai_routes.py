# backend/routes/ai_routes.py
from flask import Blueprint
from openai import OpenAI
from backend.rag.retriever import retrieve_context

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")


def transactions_to_text(transactions):
    return "\n".join([
        f"{tx['date']} - {tx['name']} - ${tx['amount']} - {', '.join(tx.get('category', []))}"
        for tx in transactions
    ])


def chat_with_advisor(api_key, transactions, conversation_history, user_input, user_goals=None):
    """Legacy chat function — stuffs all transactions into the system prompt."""
    client = OpenAI(api_key=api_key)

    if not conversation_history:
        # Inject data ONLY into the system prompt
        transaction_text = transactions_to_text(transactions)
        intro = f"User's financial goals: {user_goals}" if user_goals else ""

        conversation_history = [
            {
                "role": "system",
                "content": (
                    f"You are an AI-powered financial advisor.\n\n"
                    f"{intro}\n\n"
                    "Here is the user's transaction data:\n"
                    f"{transaction_text}\n\n"
                    "Use this data to provide personalized financial advice, including:\n"
                    "- Spending insights\n"
                    "- Budget suggestions\n"
                    "- Credit score improvement strategies (e.g., reducing high-interest spending, paying on time, avoiding overdrafts, maintaining low credit utilization)"
                )
            },
            {
                "role": "user",
                "content": "Can you review my spending and give me financial advice?"
            }
        ]

    else:
        # Follow-up questions
        conversation_history.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=conversation_history
    )

    reply = response.choices[0].message.content
    conversation_history.append({"role": "assistant", "content": reply})

    return reply, conversation_history


def chat_with_advisor_rag(
    api_key,
    vector_store,
    conversation_history,
    user_input,
    user_goals=None,
    n_results=15,
):
    """RAG-powered chat function — retrieves relevant context per question.

    Instead of dumping all transactions into the prompt, this function:
    1. Embeds the user's question
    2. Retrieves the most relevant document chunks from the vector store
    3. Injects ONLY those chunks into the system prompt
    4. Asks GPT to cite which data it used

    Args:
        api_key: OpenAI API key.
        vector_store: FinanceVectorStore instance with ingested data.
        conversation_history: List of conversation message dicts.
        user_input: The user's current question.
        user_goals: Optional user financial goals string.
        n_results: Number of context chunks to retrieve.

    Returns:
        Tuple of (reply_text, updated_conversation_history, retrieved_context).
    """
    client = OpenAI(api_key=api_key)

    # Retrieve relevant context for this specific question
    context, raw_results = retrieve_context(
        query=user_input,
        vector_store=vector_store,
        api_key=api_key,
        n_results=n_results,
    )

    # Build the system prompt with retrieved context
    goals_section = f"\nUser's financial goals: {user_goals}\n" if user_goals else ""

    system_prompt = (
        "You are an AI-powered financial advisor using a RAG (Retrieval-Augmented Generation) system.\n\n"
        f"{goals_section}"
        "Below is the relevant financial context retrieved for this question. "
        "Use ONLY this context to provide your answer. "
        "If the context doesn't contain enough information, say so honestly.\n"
        "When giving advice, cite which specific transactions or data points you're referencing.\n\n"
        f"{context}\n\n"
        "Provide personalized financial advice including:\n"
        "- Spending insights based on the retrieved data\n"
        "- Budget suggestions\n"
        "- Credit score improvement strategies where relevant\n"
        "- References to specific transactions or patterns you observed"
    )

    if not conversation_history:
        conversation_history = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]
    else:
        # Update the system prompt with fresh context for follow-up questions
        conversation_history[0] = {"role": "system", "content": system_prompt}
        conversation_history.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=conversation_history,
    )

    reply = response.choices[0].message.content
    conversation_history.append({"role": "assistant", "content": reply})

    return reply, conversation_history, context

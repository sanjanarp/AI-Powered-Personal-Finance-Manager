"""
AI-Powered Personal Finance Manager (Streamlit Application)

This Streamlit application allows users to upload bank statement PDFs, analyze their financial data, 
and receive categorized expense breakdowns, financial summaries, and advice powered by OpenAI's GPT-3.5-turbo. 
"""

# --- Imports ---
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
import re
from io import BytesIO
from pdf_utils import extract_text_from_pdfs
from openai_utils import get_summary_and_advice
import openai  # Ensure openai is imported globally


# --- Helper Functions ---
def parse_expense_data(reply):
    """
    Parses the JSON-like response from OpenAI's API to extract categorized expenses.
    Removes invalid or negative values.
    """
    try:
        # Attempt to parse the response as JSON
        parsed_data = json.loads(reply)
        # Filter out invalid or negative values
        return {k: abs(float(v)) for k, v in parsed_data.items() if isinstance(v, (int, float)) and float(v) > 0}
    except (json.JSONDecodeError, ValueError) as e:
        # Return None if parsing fails
        return None


def display_expense_chart(expense_data):
    """
    Displays a pie chart of categorized expenses and provides a CSV download option.
    """
    df = pd.DataFrame(list(expense_data.items()), columns=["Category", "Amount"])
    total = df["Amount"].sum()
    st.markdown(f"**Total Expenses:** ${total:.2f}")

    # Create pie chart
    fig, ax = plt.subplots()
    wedges, texts = ax.pie(df["Amount"], labels=None, startangle=90)
    ax.axis("equal")

    # Add legend
    legend_labels = [f"{cat}: {amt / total:.1%}" for cat, amt in zip(df["Category"], df["Amount"])]
    ax.legend(wedges, legend_labels, title="Categories", loc="center left", bbox_to_anchor=(1, 0.5))
    st.pyplot(fig)

    # CSV download button
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Expense Data as CSV", csv, "expenses.csv", "text/csv")


# --- Main Function ---
def main():
    # --- Streamlit Page Configuration ---
    st.set_page_config(page_title="AI Finance Manager", layout="centered")
    st.title("📊 AI-Powered Personal Finance Manager")

    # --- Input Fields ---
    api_key = st.text_input("Enter your OpenAI API Key:", type="password")
    uploaded_files = st.file_uploader(
        "Upload your bank statement PDFs:",
        type=["pdf"],
        accept_multiple_files=True
    )

    # --- Global Variables ---
    summary = ""
    expense_data = {}
    conversation_history = []  # To maintain context for follow-up questions

    # --- Analyze Statements ---
    if st.button("Analyze Statements") and uploaded_files and api_key:
        with st.spinner("Analyzing statements..."):
            try:
                # Extract text from uploaded PDFs
                combined_text = extract_text_from_pdfs(uploaded_files)

                # Get financial advice and summary
                summary = get_summary_and_advice(combined_text, api_key)
                st.subheader("📋 Financial Summary and Advice")
                st.text_area("Summary", summary, height=300)

                # Request categorized expenses in JSON format
                prompt = (
                    "Extract categorized expenses from this bank statement."
                    " Return only a valid JSON object with category names as keys and total expenses as values."
                    " Do NOT include code formatting, markdown, or natural language."
                    f"\n\n{combined_text}"
                )

                openai.api_key = api_key
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful financial assistant."},
                        {"role": "user", "content": prompt}
                    ]
                )

                reply = response["choices"][0]["message"]["content"]
                expense_data = parse_expense_data(reply)

                if not expense_data:
                    st.warning("Could not parse expense dictionary. Invalid JSON or data format.")
                    st.text_area("Detected Block", reply, height=150)
                else:
                    st.success("Expense data successfully parsed!")

                # Add context to conversation history
                conversation_history.append(
                    {"role": "system", "content": "You are a helpful financial assistant."}
                )
                conversation_history.append(
                    {"role": "user", "content": f"Here is the bank statement data:\n\n{combined_text}"}
                )
                conversation_history.append(
                    {"role": "assistant", "content": summary}
                )
            except Exception as e:
                st.error(f"Error: {str(e)}")

    # --- Expense Breakdown Chart ---
    st.markdown("---")
    st.subheader("📈 Expense Breakdown Chart")

    if expense_data:
        display_expense_chart(expense_data)
    else:
        st.info("No valid expense data available to plot.")

    # --- Follow-up Questions ---
    st.markdown("---")
    st.subheader("💬 Ask a Follow-up Question")
    followup_q = st.text_input("Your question:")

    if st.button("Ask") and followup_q and api_key:
        with st.spinner("Thinking..."):
            try:
                # Add the user's question to the conversation history
                conversation_history.append({"role": "user", "content": followup_q})

                # Send the conversation history to OpenAI
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=conversation_history
                )

                # Get the assistant's reply
                reply = response["choices"][0]["message"]["content"]
                st.success("Response:")
                st.text_area("AI Reply", reply, height=200)

                # Add the assistant's reply to the conversation history
                conversation_history.append({"role": "assistant", "content": reply})
            except Exception as e:
                st.error(f"Error: {str(e)}")


# --- Run the Application ---
if __name__ == "__main__":
    main()

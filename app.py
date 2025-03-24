# app.py (Streamlit Version with Custom Pie Chart, Total, CSV Download, and Financial Advice Display)
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
import re
from io import BytesIO
from pdf_utils import extract_text_from_pdfs
from openai_utils import ask_followup_question, get_summary_and_advice

st.set_page_config(page_title="AI Finance Manager", layout="centered")
st.title("📊 AI-Powered Personal Finance Manager")

api_key = st.text_input("Enter your OpenAI API Key:", type="password")

uploaded_files = st.file_uploader(
    "Upload your bank statement PDFs:",
    type=["pdf"],
    accept_multiple_files=True
)

summary = ""
expense_data = {}

if st.button("Analyze Statements") and uploaded_files and api_key:
    with st.spinner("Analyzing statements..."):
        try:
            combined_text = extract_text_from_pdfs(uploaded_files)

            # Get financial advice and expense summary
            summary = get_summary_and_advice(combined_text, api_key)
            st.subheader("📋 Financial Summary and Advice")
            st.text_area("Summary", summary, height=300)

            # Use a refined prompt to request clean JSON
            prompt = (
                "Extract categorized expenses from this bank statement."
                " Return only a valid JSON object with category names as keys and total expenses as values."
                " Do NOT include code formatting, markdown, or natural language."
                f"\n\n{combined_text}"
            )

            import openai
            openai.api_key = api_key
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful financial assistant."},
                    {"role": "user", "content": prompt}
                ]
            )

            reply = response["choices"][0]["message"]["content"]

            # Use regex to extract first JSON-like dict
            match = re.search(r"\{.*?\}", reply, re.DOTALL)
            if match:
                try:
                    parsed_data = json.loads(match.group())
                    # Remove negative or invalid values
                    expense_data = {k: abs(float(v)) for k, v in parsed_data.items() if float(v) > 0}
                except (json.JSONDecodeError, ValueError) as e:
                    st.warning("Could not parse expense dictionary. Invalid JSON or data format.")
                    st.text_area("Detected Block", match.group(), height=150)
            else:
                st.warning("No valid dictionary found in GPT output.")
        except Exception as e:
            st.error(f"Error: {str(e)}")

st.markdown("---")
st.subheader("📈 Expense Breakdown Chart")

if expense_data:
    df = pd.DataFrame(list(expense_data.items()), columns=["Category", "Amount"])
    total = df["Amount"].sum()
    st.markdown(f"**Total Expenses:** ${total:.2f}")

    fig, ax = plt.subplots()
    wedges, texts = ax.pie(df["Amount"], labels=None, startangle=90)
    ax.axis("equal")

    legend_labels = [f"{cat}: {amt / total:.1%}" for cat, amt in zip(df["Category"], df["Amount"])]
    ax.legend(wedges, legend_labels, title="Categories", loc="center left", bbox_to_anchor=(1, 0.5))
    st.pyplot(fig)

    # CSV download button
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Expense Data as CSV", csv, "expenses.csv", "text/csv")
else:
    st.info("No valid expense data available to plot.")

st.markdown("---")
st.subheader("💬 Ask a Follow-up Question")
followup_q = st.text_input("Your question:")

if st.button("Ask") and followup_q and api_key:
    with st.spinner("Thinking..."):
        try:
            reply = ask_followup_question(followup_q, api_key)
            st.success("Response:")
            st.text_area("AI Reply", reply, height=200)
        except Exception as e:
            st.error(f"Error: {str(e)}")

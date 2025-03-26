import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
import re
import requests
from io import BytesIO

st.set_page_config(page_title="AI Finance Manager", layout="centered")
st.title("📊 AI-Powered Personal Finance Manager")

# Define your Flask backend base URL
BACKEND_URL = "http://localhost:5050"

api_key = st.text_input("Enter your OpenAI API Key:", type="password")

uploaded_files = st.file_uploader(
    "Upload your bank statement PDFs:",
    type=["pdf"],
    accept_multiple_files=True
)

summary = ""
expense_data = {}

if st.button("Analyze Statements") and uploaded_files and api_key:
    with st.spinner("Analyzing statements via backend..."):
        try:

            # Step 1: Get financial advice summary
            # First, extract text from PDFs for the summary
            # Prepare files and API key (just once)
            files = [("files", (f.name, f, "application/pdf")) for f in uploaded_files]
            data = {"api_key": api_key}

            # 🧠 Call backend for financial advice (PDF gets parsed server-side now)
            summary_res = requests.post(
                f"{BACKEND_URL}/advice/summary",
                files=files,
                data=data
            )

            if summary_res.status_code == 200:
                summary = summary_res.json()["summary"]
                st.subheader("📋 Financial Summary and Advice")
                st.text_area("Summary", summary, height=300, key="summary_text")
            else:
                st.warning("Failed to get financial advice summary.")
                st.text_area("Backend Message", summary_res.text, height=150, key="summary_error_text")


            # Step 2: Get categorized expenses
            response = requests.post(f"{BACKEND_URL}/analyze/", files=files, data=data)

            if response.status_code == 200:
                expense_data = response.json()
            else:
                st.warning("Failed to extract expenses.")
                st.text_area("Backend Message", response.text, height=150, key="response_text")

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
            response = requests.post(
                f"{BACKEND_URL}/advice/followup", data={"question": followup_q, "api_key": api_key}
            )
            if response.status_code == 200:
                st.success("Response:")
                st.text_area("AI Reply", response.json()["reply"], height=200)
            else:
                st.error("Failed to get reply.")
                st.text_area("Backend Message", response.text, height=150)
        except Exception as e:
            st.error(f"Error: {str(e)}")

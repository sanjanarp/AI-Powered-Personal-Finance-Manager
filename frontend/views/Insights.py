import streamlit as st
import pandas as pd
import altair as alt
from openai import OpenAI
import json
from backend.utils.config import Config
from frontend.components.AccountSelector import show_account_selector
from backend.rag.retriever import retrieve_context

def show_insights():
    st.title("📊 Spending Insights – AI Finance Manager")

    selected_accounts = show_account_selector()

    if not selected_accounts:
        st.warning("⚠️ Please select at least one account to view insights.")
        st.stop()

    if 'transactions' not in st.session_state:
        st.warning("No transaction data found. Go to 'Home' and connect your bank first.")
        st.stop()

    # Filter relevant transactions
    transactions = [
        tx for tx in st.session_state['transactions']
        if (tx.get('account_id') in selected_accounts or tx.get('source') == 'manual_upload')
    ]

    if not transactions:
        st.warning("No transactions found for selected accounts.")
        st.stop()

    # 🔁 Map account_id → institution name (bank)
    bank_name_map = {}
    if "linked_banks" in st.session_state:
        for bank in st.session_state["linked_banks"].values():
            institution_name = bank.get("institution_name", "Unknown Bank")
            for account in bank.get("accounts", []):
                bank_name_map[account["account_id"]] = institution_name

    # 📄 Create DataFrame
    df = pd.DataFrame(transactions)

    def parse_date(date_str):
        if isinstance(date_str, str):
            try:
                return pd.to_datetime(date_str)
            except:
                try:
                    return pd.to_datetime(date_str, format="%a, %d %b %Y %H:%M:%S GMT")
                except:
                    return pd.NaT
        return pd.NaT

    df["date"] = df["date"].apply(parse_date)
    df = df.dropna(subset=["date"]).sort_values("date", ascending=False)

    # Add bank name for Plaid transactions
    df["bank_name"] = df["account_id"].apply(lambda x: bank_name_map.get(x, "Unknown Bank"))

    # Normalize category format with smart fallback
    def infer_category_from_name(merchant_name):
        """Infer a spending category from the merchant/transaction name."""
        name = str(merchant_name).lower()

        keyword_map = {
            "Food & Drink": ["starbucks", "mcdonald", "dunkin", "chipotle", "pizza", "burger",
                             "taco", "wendy", "chick-fil", "subway", "panera", "grubhub",
                             "doordash", "uber eats", "postmates", "restaurant", "cafe", "diner",
                             "bakery", "coffee"],
            "Transportation": ["uber", "lyft", "gas", "shell", "chevron", "exxon", "bp ",
                               "parking", "transit", "metro", "amtrak", "fuel"],
            "Travel": ["airline", "united air", "delta air", "american air", "southwest",
                       "jetblue", "hotel", "marriott", "hilton", "airbnb", "booking", "expedia"],
            "Shopping": ["amazon", "walmart", "target", "costco", "best buy", "ebay",
                         "etsy", "ikea", "home depot", "lowe", "sparkfun"],
            "Entertainment": ["netflix", "spotify", "hulu", "disney", "apple music",
                              "youtube", "gaming", "cinema", "movie", "theater"],
            "Bills & Utilities": ["electric", "water", "internet", "comcast", "verizon",
                                  "at&t", "t-mobile", "utility", "power", "gas bill"],
            "Healthcare": ["pharmacy", "cvs", "walgreens", "doctor", "hospital", "dental",
                           "medical", "health"],
            "Groceries": ["grocery", "trader joe", "whole foods", "safeway", "kroger",
                          "publix", "aldi", "sprouts"],
            "Transfer": ["transfer", "zelle", "venmo", "paypal", "wire"],
            "Payment": ["payment", "pymnt", "credit card", "autopay"],
            "Deposit": ["deposit", "direct dep", "ach", "gusto", "payroll"],
            "Interest": ["interest", "intrst"],
            "Recreation": ["climbing", "touchstone", "gym", "fitness", "sport"],
        }

        for category, keywords in keyword_map.items():
            if any(kw in name for kw in keywords):
                return category
        return "Uncategorized"

    def resolve_category(row):
        """Get category from Plaid data or infer from merchant name."""
        # Negative amounts are refunds/credits — never spending
        amt = row.get("amount") if "amount" in row.index else 0
        try:
            if float(amt) < 0:
                return "Refund/Credit"
        except (ValueError, TypeError):
            pass

        merchant = row.get("name", "") if "name" in row.index else ""
        name_lower = str(merchant).lower()

        # Priority: check if name clearly indicates a deposit/transfer
        # (Plaid sandbox often miscategorizes these)
        _deposit_words = ["deposit", "direct dep", "ach", "payroll", "gusto"]
        _transfer_words = ["transfer", "zelle", "venmo", "paypal", "wire"]
        if any(kw in name_lower for kw in _deposit_words):
            return "Deposit"
        if any(kw in name_lower for kw in _transfer_words):
            return "Transfer"

        # Check the standard 'category' field
        cat = row.get("category") if "category" in row.index else None
        if isinstance(cat, list) and len(cat) > 0:
            return cat[0]
        if isinstance(cat, str) and cat and cat not in ("Uncategorized", "None", "null"):
            return cat

        # Check Plaid's newer personal_finance_category field
        if "personal_finance_category" in row.index:
            pfc = row.get("personal_finance_category")
            if isinstance(pfc, dict):
                primary = pfc.get("primary") or pfc.get("detailed", "")
                if primary:
                    return primary.replace("_", " ").title()

        # Fallback: infer from merchant name
        return infer_category_from_name(merchant)

    df["category"] = df.apply(resolve_category, axis=1)


    # Format source label with bank name
    def format_source(row):
        if row.get("source") == "manual_upload":
            return "📷 Receipt"
        elif row.get("source") == "plaid":
            return f"🏦 {row.get('bank_name', 'Bank')}"
        else:
            return "🏦 Bank"

    df["formatted_source"] = df.apply(format_source, axis=1)

    # -------------------- Visualization --------------------

    # Separate expenses from income/deposits
    _non_spending_cats = {"Deposit", "Transfer", "Income/Credit", "Income", "Refund/Credit"}
    spending_df = df[
        (~df["category"].isin(_non_spending_cats)) &
        (df["amount"] > 0)
    ].copy()
    income_df = df[
        (df["category"].isin(_non_spending_cats)) | (df["amount"] < 0)
    ].copy()

    # 1. Category-wise Spending (expenses only)
    st.subheader("🧾 Spending by Category")
    if not spending_df.empty:
        category_totals = spending_df.groupby("category")["amount"].sum().reset_index().sort_values("amount", ascending=False)

        st.altair_chart(
            alt.Chart(category_totals).mark_bar().encode(
                x=alt.X("category", sort="-y", title="Category"),
                y=alt.Y("amount", title="Amount ($)"),
                tooltip=[
                    alt.Tooltip("category", title="Category"),
                    alt.Tooltip("amount", title="Amount", format="$.2f")
                ]
            ).properties(width=700),
            use_container_width=True
        )

        total_spending = spending_df["amount"].sum()
        st.metric("Total Spending", f"${total_spending:,.2f}")
    else:
        st.info("No spending transactions found.")

    # Income/Deposits summary
    if not income_df.empty:
        total_income = abs(income_df["amount"].sum())
        st.caption(f"💰 Total deposits/credits: ${total_income:,.2f} (excluded from spending chart)")

    # 2. Time-based Spending
    st.subheader("📅 Spending Over Time")
    daily_spending = spending_df.groupby("date")["amount"].sum().reset_index() if not spending_df.empty else pd.DataFrame(columns=["date", "amount"])

    st.altair_chart(
        alt.Chart(daily_spending).mark_line(point=True).encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("amount:Q", title="Amount ($)"),
            tooltip=[
                alt.Tooltip("date:T", title="Date", format="%Y-%m-%d"),
                alt.Tooltip("amount:Q", title="Amount", format="$.2f")
            ]
        ).properties(width=700, height=400).interactive(),
        use_container_width=True
    )

    # 3. Spending Transaction Table
    st.subheader("📄 Spending Transactions")
    display_df = spending_df[["date", "name", "amount", "category", "formatted_source"]].copy()
    display_df.rename(columns={"formatted_source": "source"}, inplace=True)
    display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
    display_df["amount"] = display_df["amount"].map("${:,.2f}".format)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "date": "Date",
            "name": "Merchant",
            "amount": "Amount",
            "category": "Category",
            "source": "Source"
        }
    )

    # 4. AI Spending Trend Analysis (RAG-enhanced)
    st.subheader("🧠 Analyze My Spending Trends")
    if st.button("📊 Get AI Insights"):
        with st.spinner("Analyzing your charts..."):
            try:
                api_key = Config.get_openai_api_key()
                client = OpenAI(api_key=api_key)

                # Check if we have a RAG vector store available
                vector_store = st.session_state.get('vector_store')

                if vector_store and vector_store.count() > 0:
                    # RAG path: retrieve relevant context
                    analysis_query = (
                        "Analyze spending trends: which categories have high spending, "
                        "are there spending spikes or unusual patterns, and what are the trends over time?"
                    )
                    rag_context, _ = retrieve_context(
                        query=analysis_query,
                        vector_store=vector_store,
                        api_key=api_key,
                        n_results=20,
                    )

                    prompt = f"""You are a personal finance assistant. Analyze this user's spending patterns using the following retrieved context:

{rag_context}

Tell the user:
- Which categories had unusually high or low spending.
- If any categories increased or decreased significantly.
- Any spikes, dips, or trends over time (e.g., mid-month spending surge).
- Cite specific transactions or data points when possible.
Return natural-language bullet points. Be concise but insightful."""

                    # Show what context was retrieved
                    with st.expander("📚 Retrieved Context (data the AI is analyzing)"):
                        st.code(rag_context, language="text")

                else:
                    # Fallback: use direct data (no RAG)
                    category_data = (
                        spending_df.groupby("category")["amount"].sum().reset_index().to_dict(orient="records")
                    ) if not spending_df.empty else []

                    date_df = (
                        spending_df.groupby("date")["amount"].sum().reset_index().sort_values("date")
                    ) if not spending_df.empty else pd.DataFrame(columns=["date", "amount"])
                    date_df["date"] = date_df["date"].dt.strftime("%Y-%m-%d")
                    date_data = date_df.to_dict(orient="records")

                    prompt = f"""You are a personal finance assistant. Analyze this user's spending patterns from two charts:

1. Category-wise totals:
{json.dumps(category_data, indent=2)}

2. Daily spending trends:
{json.dumps(date_data, indent=2)}

Tell the user:
- Which categories had unusually high or low spending.
- If any categories increased or decreased significantly.
- Any spikes, dips, or trends over time (e.g., mid-month spending surge).
Return natural-language bullet points. Be concise but insightful."""

                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful financial advisor analyzing spending trends."},
                        {"role": "user", "content": prompt}
                    ]
                )
                insights = response.choices[0].message.content
                st.markdown("### 🔍 AI-Generated Insights:")
                st.markdown(insights)
            except Exception as e:
                st.error(f"AI analysis failed: {str(e)}")


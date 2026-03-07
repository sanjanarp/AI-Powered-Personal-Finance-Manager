import streamlit as st
import io
from backend.routes.ai_routes import chat_with_advisor_rag
from backend.utils.config import Config
from backend.rag.vector_store import FinanceVectorStore
from backend.rag.ingestion import ingest_all
from openai import OpenAI


def show_chatbot():
    st.title("💬 AI Financial Advisor")
    st.caption("Powered by RAG — retrieves only the most relevant data for each question")

    # Session state setup
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []

    if 'chat_started' not in st.session_state:
        st.session_state.chat_started = False

    if 'retrieved_contexts' not in st.session_state:
        st.session_state.retrieved_contexts = []

    # Goals input (only at the start)
    if not st.session_state.chat_started:
        user_goals = ""

    # Check if transactions are available
    if 'transactions' not in st.session_state:
        st.warning("⚠️ Please fetch transactions from the Home page first.")
    else:
        transactions = st.session_state['transactions']

        try:
            api_key = Config.get_openai_api_key()

            # Start chat on button press
            if not st.session_state.chat_started and st.button("🚀 Start Financial Advice Chat"):
                with st.spinner("🔄 Building knowledge base & analyzing your transactions..."):
                    # Initialize vector store and ingest data
                    vector_store = FinanceVectorStore(
                        persist_dir="./chroma_db",
                        collection_name="finance_docs"
                    )
                    vector_store.reset()  # Fresh start for this session

                    # Gather budget info if available
                    budget_limits = {}
                    current_month = None
                    if 'budget_limits' in st.session_state:
                        for month, limits in st.session_state['budget_limits'].items():
                            budget_limits = limits
                            current_month = month
                            break  # Use the most recent month

                    # -----------------------------------------------------------
                    # PRE-ENRICH: Fix categories, dates, and exclude deposits.
                    # This MUST run here (in the view) to avoid stale-module issues.
                    # -----------------------------------------------------------
                    from dateutil import parser as _date_parser

                    _kw_map = {
                        "Food & Drink": ["starbucks", "mcdonald", "dunkin", "chipotle", "pizza",
                                         "burger", "taco", "wendy", "chick-fil", "subway",
                                         "panera", "grubhub", "doordash", "uber eats",
                                         "postmates", "restaurant", "cafe", "diner",
                                         "bakery", "coffee"],
                        "Transportation": ["uber", "lyft", "gas", "shell", "chevron", "exxon",
                                           "bp ", "parking", "transit", "metro", "amtrak", "fuel"],
                        "Travel": ["airline", "united air", "delta air", "american air",
                                   "southwest", "jetblue", "hotel", "marriott", "hilton",
                                   "airbnb", "booking", "expedia"],
                        "Shopping": ["amazon", "walmart", "target", "costco", "best buy",
                                     "ebay", "etsy", "ikea", "home depot", "lowe", "sparkfun"],
                        "Entertainment": ["netflix", "spotify", "hulu", "disney", "apple music",
                                          "youtube", "gaming", "cinema", "movie", "theater"],
                        "Bills & Utilities": ["electric", "water", "internet", "comcast",
                                              "verizon", "at&t", "t-mobile", "utility", "power"],
                        "Healthcare": ["pharmacy", "cvs", "walgreens", "doctor", "hospital",
                                       "dental", "medical", "health"],
                        "Groceries": ["grocery", "trader joe", "whole foods", "safeway",
                                      "kroger", "publix", "aldi", "sprouts"],
                        "Transfer": ["transfer", "zelle", "venmo", "paypal", "wire"],
                        "Payment": ["payment", "pymnt", "credit card", "autopay"],
                        "Deposit": ["deposit", "direct dep", "ach", "gusto", "payroll"],
                        "Interest": ["interest", "intrst"],
                        "Recreation": ["climbing", "touchstone", "gym", "fitness", "sport"],
                    }

                    # Non-spending categories to exclude from spending summaries
                    _non_spending = {"Deposit", "Transfer", "Refund/Credit", "Income/Credit"}
                    _dep_kw = ["deposit", "direct dep", "ach", "payroll", "gusto"]
                    _xfr_kw = ["transfer", "zelle", "venmo", "paypal", "wire"]

                    for tx in transactions:
                        # 1) Normalize date to ISO format ("2026-02-10")
                        raw_date = tx.get("date", "")
                        if isinstance(raw_date, str) and raw_date and not (len(raw_date) >= 10 and raw_date[4] == "-"):
                            try:
                                parsed_dt = _date_parser.parse(raw_date)
                                tx["date"] = parsed_dt.strftime("%Y-%m-%d")
                            except Exception:
                                pass

                        # 2) Resolve category (same priority as Insights page)
                        amount = float(tx.get("amount", 0))
                        name_lower = str(tx.get("name", "")).lower()

                        if amount < 0:
                            tx["category"] = "Refund/Credit"
                        elif any(kw in name_lower for kw in _dep_kw):
                            tx["category"] = "Deposit"
                        elif any(kw in name_lower for kw in _xfr_kw):
                            tx["category"] = "Transfer"
                        else:
                            cat = tx.get("category")
                            if isinstance(cat, list) and cat and cat[0]:
                                tx["category"] = cat[0]
                            elif isinstance(cat, str) and cat and cat not in ("None", "Uncategorized", "null"):
                                pass  # Already good
                            else:
                                matched = "Uncategorized"
                                for cat_name, keywords in _kw_map.items():
                                    if any(kw in name_lower for kw in keywords):
                                        matched = cat_name
                                        break
                                tx["category"] = matched

                    # Filter: only pass actual expenses to ingestion (exclude deposits & credits)
                    spending_txs = [
                        tx for tx in transactions
                        if tx.get("category") not in _non_spending
                        and float(tx.get("amount", 0)) > 0
                    ]

                    # Ingest spending transactions (for summaries)
                    ingest_all(
                        transactions=spending_txs,
                        vector_store=vector_store,
                        api_key=api_key,
                        budget_limits=budget_limits,
                        month=current_month,
                    )

                    # Store vector store in session
                    st.session_state['vector_store'] = vector_store
                    doc_count = vector_store.count()
                    st.session_state['rag_doc_count'] = doc_count

                    default_goals = (
                        "Improve my credit score by reducing unnecessary expenses, ensuring timely payments, "
                        "and optimizing credit utilization across categories like shopping, dining, bills, and subscriptions."
                    )

                    initial_query = "Provide financial advice based on my transactions. Include suggestions for improving my credit score."

                    reply, history, context = chat_with_advisor_rag(
                        api_key=api_key,
                        vector_store=vector_store,
                        conversation_history=[],
                        user_input=initial_query,
                        user_goals=user_goals if 'user_goals' in dir() and user_goals else default_goals,
                    )
                    st.session_state.conversation_history = history
                    st.session_state.retrieved_contexts = [context]
                    st.session_state.chat_started = True
                    st.rerun()

            # Show chat
            if st.session_state.chat_started:
                # Show RAG status
                doc_count = st.session_state.get('rag_doc_count', 0)
                st.markdown(f"📚 **Knowledge base**: {doc_count} documents indexed")

                st.markdown("### 📌 Conversation")

                msg_index = 0
                for msg in st.session_state.conversation_history:
                    if msg["role"] == "system":
                        continue  # Don't show system prompt
                    if msg["role"] == "user":
                        with st.chat_message("user"):
                            st.markdown(msg["content"])
                    elif msg["role"] == "assistant":
                        with st.chat_message("assistant"):
                            st.markdown(msg["content"])

                        # Show retrieved context for this response
                        ctx_idx = msg_index
                        if ctx_idx < len(st.session_state.retrieved_contexts):
                            ctx = st.session_state.retrieved_contexts[ctx_idx]
                            if ctx:
                                with st.expander("📚 Retrieved Context (what the AI used)"):
                                    st.code(ctx, language="text")
                        msg_index += 1

                # Input box for user follow-up
                followup = st.chat_input("Ask a question about your spending, savings, or financial goals...")

                if followup:
                    with st.spinner("🔍 Retrieving relevant data & generating response..."):
                        vector_store = st.session_state.get('vector_store')
                        if vector_store is None:
                            st.error("Vector store not initialized. Please restart the chat.")
                        else:
                            reply, updated_history, context = chat_with_advisor_rag(
                                api_key=api_key,
                                vector_store=vector_store,
                                conversation_history=st.session_state.conversation_history,
                                user_input=followup,
                            )
                            st.session_state.conversation_history = updated_history
                            st.session_state.retrieved_contexts.append(context)
                            st.rerun()

                # 💾 Export chat log
                if st.session_state.conversation_history:
                    export_format = st.radio("💾 Export Format", ["Markdown (.md)", "Text (.txt)"], horizontal=True)

                    if st.button("📥 Save Chat Log"):
                        buffer = io.StringIO()

                        for msg in st.session_state.conversation_history:
                            if msg['role'] == 'system':
                                continue
                            role = "User" if msg['role'] == 'user' else "Advisor"
                            content = msg['content']
                            if export_format.startswith("Markdown"):
                                buffer.write(f"### **{role}:**\n{content}\n\n")
                            else:
                                buffer.write(f"{role}:\n{content}\n\n")

                        file_ext = "md" if export_format.startswith("Markdown") else "txt"
                        filename = f"financial_chat_log.{file_ext}"

                        st.download_button(
                            label="⬇️ Download Chat Log",
                            data=buffer.getvalue(),
                            file_name=filename,
                            mime="text/plain" if file_ext == "txt" else "text/markdown"
                        )
        except ValueError as e:
            st.error("⚠️ OpenAI API key not configured. Please add it to your .env file.")

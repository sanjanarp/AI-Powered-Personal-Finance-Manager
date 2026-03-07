# backend/rag/ingestion.py
"""Ingestion pipeline for the RAG system.

Handles converting raw app data (transactions, budgets, policy docs)
into embedded document chunks stored in the vector database.
"""

import os
from collections import defaultdict

from backend.rag.chunker import (
    chunk_transactions,
    chunk_monthly_summary,
    chunk_budget_goals,
    chunk_policy_doc,
)
from backend.rag.embeddings import get_embeddings_batch


def infer_category(merchant_name: str) -> str:
    """Infer spending category from merchant/transaction name."""
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


# Path to the knowledge base directory
KNOWLEDGE_BASE_DIR = os.path.join(os.path.dirname(__file__), "knowledge_base")


def _enrich_categories(transactions: list) -> list:
    """Pre-process transactions to ensure every one has a proper category string.
    
    This modifies transactions in-place so that downstream functions
    (even if stale-cached) see category as a non-empty string.
    """
    for tx in transactions:
        raw_cat = tx.get("category")
        # Already has a good category?
        if isinstance(raw_cat, list) and raw_cat and raw_cat[0]:
            tx["category"] = raw_cat[0]  # Convert list to string
            continue
        if isinstance(raw_cat, str) and raw_cat and raw_cat not in ("None", "Uncategorized"):
            continue
        
        # Try personal_finance_category
        pfc = tx.get("personal_finance_category")
        if isinstance(pfc, dict):
            primary = pfc.get("primary") or pfc.get("detailed", "")
            if primary:
                tx["category"] = primary.replace("_", " ").title()
                continue
        
        # Infer from merchant name
        tx["category"] = infer_category(tx.get("name", ""))
    return transactions


def ingest_transactions(transactions: list, vector_store, api_key: str):
    """Chunk and ingest transaction data into the vector store.

    Args:
        transactions: List of transaction dicts.
        vector_store: FinanceVectorStore instance.
        api_key: OpenAI API key for embeddings.
    """
    chunks = chunk_transactions(transactions)
    if not chunks:
        return

    ids = [c["id"] for c in chunks]
    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    # Batch embed
    embeddings = get_embeddings_batch(texts, api_key)

    vector_store.upsert(
        ids=ids,
        documents=texts,
        metadatas=metadatas,
        embeddings=embeddings,
    )


def ingest_monthly_summary(month: str, transactions: list, vector_store, api_key: str):
    """Generate and ingest a monthly spending summary.

    Args:
        month: Year-month string, e.g., "2025-03".
        transactions: All transactions (will be filtered to the given month).
        vector_store: FinanceVectorStore instance.
        api_key: OpenAI API key for embeddings.
    """
    # Filter transactions for the target month
    month_txs = []
    for tx in transactions:
        date = tx.get("date", "")
        if isinstance(date, str) and date[:7] == month:
            month_txs.append(tx)
        else:
            # Try parsing other date formats
            try:
                from dateutil import parser as date_parser
                parsed = date_parser.parse(str(date))
                if parsed.strftime("%Y-%m") == month:
                    month_txs.append(tx)
            except Exception:
                continue

    if not month_txs:
        return

    # Calculate category totals
    category_totals = defaultdict(float)
    total_spent = 0.0
    for tx in month_txs:
        amount = abs(float(tx.get("amount", 0)))
        total_spent += amount

        raw_cat = tx.get("category")
        if isinstance(raw_cat, list) and raw_cat:
            cat = raw_cat[0]
        elif isinstance(raw_cat, str) and raw_cat:
            cat = raw_cat
        else:
            # Try personal_finance_category, then infer from name
            pfc = tx.get("personal_finance_category")
            if isinstance(pfc, dict):
                primary = pfc.get("primary") or pfc.get("detailed", "")
                cat = primary.replace("_", " ").title() if primary else infer_category(tx.get("name", ""))
            else:
                cat = infer_category(tx.get("name", ""))
        category_totals[cat] += amount

    chunk = chunk_monthly_summary(month, dict(category_totals), total_spent)

    embeddings = get_embeddings_batch([chunk["text"]], api_key)

    vector_store.upsert(
        ids=[chunk["id"]],
        documents=[chunk["text"]],
        metadatas=[chunk["metadata"]],
        embeddings=embeddings,
    )


def ingest_budgets(budget_limits: dict, month: str, vector_store, api_key: str):
    """Ingest budget goal data into the vector store.

    Args:
        budget_limits: Dict mapping category -> limit amount.
        month: Year-month string, e.g., "2025-03".
        vector_store: FinanceVectorStore instance.
        api_key: OpenAI API key for embeddings.
    """
    chunks = chunk_budget_goals(budget_limits, month)
    if not chunks:
        return

    ids = [c["id"] for c in chunks]
    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    embeddings = get_embeddings_batch(texts, api_key)

    vector_store.upsert(
        ids=ids,
        documents=texts,
        metadatas=metadatas,
        embeddings=embeddings,
    )


def ingest_policy_docs(vector_store, api_key: str):
    """Read and ingest all policy/guide documents from the knowledge base.

    Args:
        vector_store: FinanceVectorStore instance.
        api_key: OpenAI API key for embeddings.
    """
    if not os.path.isdir(KNOWLEDGE_BASE_DIR):
        return

    all_chunks = []
    for filename in os.listdir(KNOWLEDGE_BASE_DIR):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(KNOWLEDGE_BASE_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        chunks = chunk_policy_doc(filename, content)
        all_chunks.extend(chunks)

    if not all_chunks:
        return

    ids = [c["id"] for c in all_chunks]
    texts = [c["text"] for c in all_chunks]
    metadatas = [c["metadata"] for c in all_chunks]

    embeddings = get_embeddings_batch(texts, api_key)

    vector_store.upsert(
        ids=ids,
        documents=texts,
        metadatas=metadatas,
        embeddings=embeddings,
    )


def ingest_all(
    transactions: list,
    vector_store,
    api_key: str,
    budget_limits: dict = None,
    month: str = None,
):
    """Orchestrator: ingest all data sources into the vector store.

    Args:
        transactions: List of transaction dicts.
        vector_store: FinanceVectorStore instance.
        api_key: OpenAI API key for embeddings.
        budget_limits: Optional dict of category -> limit.
        month: Optional year-month string for summary/budgets.
    """
    # Pre-enrich categories so ALL downstream functions see proper categories
    # This is the single source of truth - handles Plaid's null categories
    transactions = _enrich_categories(transactions)

    # 1. Ingest transactions
    ingest_transactions(transactions, vector_store, api_key)

    # 2. Ingest monthly summaries (auto-detect months from transactions)
    months_seen = set()
    for tx in transactions:
        date = tx.get("date", "")
        if isinstance(date, str) and len(date) >= 7 and date[4:5] == "-":
            months_seen.add(date[:7])
        else:
            try:
                from dateutil import parser as date_parser
                parsed = date_parser.parse(str(date))
                months_seen.add(parsed.strftime("%Y-%m"))
            except Exception:
                continue

    for m in months_seen:
        ingest_monthly_summary(m, transactions, vector_store, api_key)

    # 3. Ingest budgets if provided
    if budget_limits and month:
        ingest_budgets(budget_limits, month, vector_store, api_key)

    # 4. Ingest policy docs
    ingest_policy_docs(vector_store, api_key)

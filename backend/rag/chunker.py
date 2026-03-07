# backend/rag/chunker.py
"""Document chunking logic for the RAG pipeline.

Converts raw financial data into text documents with metadata,
ready to be embedded and stored in the vector database.
"""

import hashlib
from collections import defaultdict


def _make_id(*parts) -> str:
    """Generate a deterministic ID from parts."""
    raw = "|".join(str(p) for p in parts)
    return hashlib.md5(raw.encode()).hexdigest()


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


def chunk_transactions(transactions: list) -> list:
    """Convert transaction records into embeddable text chunks.

    Each transaction becomes a single chunk with this format:
        "2025-03-02 | Uber | $18.25 | Transportation | account: Chase Freedom"

    Args:
        transactions: List of transaction dicts with keys: date, name, amount, category, account_id.

    Returns:
        List of dicts with keys: id, text, metadata.
    """
    chunks = []
    for i, tx in enumerate(transactions):
        date = tx.get("date", "Unknown date")
        name = tx.get("name", "Unknown")
        amount = abs(float(tx.get("amount", 0)))

        # Normalize category — try Plaid data first, then infer from merchant name
        raw_cat = tx.get("category")
        if isinstance(raw_cat, list) and raw_cat:
            category = raw_cat[0]
        elif isinstance(raw_cat, str) and raw_cat:
            category = raw_cat
        else:
            # Try personal_finance_category (newer Plaid field)
            pfc = tx.get("personal_finance_category")
            if isinstance(pfc, dict):
                primary = pfc.get("primary") or pfc.get("detailed", "")
                category = primary.replace("_", " ").title() if primary else infer_category(name)
            else:
                category = infer_category(name)

        account_id = tx.get("account_id", "unknown")
        source = tx.get("source", "plaid")

        text = f"{date} | {name} | ${amount:.2f} | {category} | account: {account_id}"

        # Extract month from date (handle multiple formats)
        month = "unknown"
        if isinstance(date, str):
            # Try ISO format: "2025-03-02"
            if len(date) >= 7 and date[4] == "-":
                month = date[:7]
            # Try other formats by extracting year-month
            else:
                try:
                    from dateutil import parser as date_parser
                    parsed = date_parser.parse(date)
                    month = parsed.strftime("%Y-%m")
                except Exception:
                    month = "unknown"

        chunk_id = _make_id("tx", date, name, amount, i)
        chunks.append({
            "id": chunk_id,
            "text": text,
            "metadata": {
                "doc_type": "transaction",
                "month": month,
                "category": category,
                "source": source,
                "merchant": name,
                "amount": amount,
            },
        })
    return chunks


def chunk_monthly_summary(month: str, category_totals: dict, total_spent: float) -> dict:
    """Create a summary chunk for a given month.

    Args:
        month: Year-month string, e.g., "2025-03".
        category_totals: Dict mapping category -> total amount.
        total_spent: Total spending for the month.

    Returns:
        Dict with keys: id, text, metadata.
    """
    lines = [f"Monthly spending summary for {month}:"]
    lines.append(f"Total spent: ${total_spent:.2f}")
    lines.append("")

    # Sort categories by spending (highest first)
    sorted_cats = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    for cat, amount in sorted_cats:
        pct = (amount / total_spent * 100) if total_spent > 0 else 0
        lines.append(f"  {cat}: ${amount:.2f} ({pct:.1f}%)")

    if sorted_cats:
        top_cat = sorted_cats[0][0]
        lines.append(f"\nTop spending category: {top_cat}")

    text = "\n".join(lines)
    return {
        "id": _make_id("summary", month),
        "text": text,
        "metadata": {
            "doc_type": "monthly_summary",
            "month": month,
        },
    }


def chunk_budget_goals(budgets: dict, month: str) -> list:
    """Create chunks for budget limits/goals.

    Args:
        budgets: Dict mapping category -> budget limit amount.
        month: Year-month string, e.g., "2025-03".

    Returns:
        List of dicts with keys: id, text, metadata.
    """
    chunks = []
    for category, limit in budgets.items():
        text = f"Budget goal for {month}: {category} — limit ${limit:.2f}/month"
        chunks.append({
            "id": _make_id("budget", month, category),
            "text": text,
            "metadata": {
                "doc_type": "budget_goal",
                "month": month,
                "category": category,
                "budget_limit": limit,
            },
        })
    return chunks


def chunk_policy_doc(filename: str, content: str, chunk_size: int = 500, overlap: int = 100) -> list:
    """Split a policy/guide document into overlapping text chunks.

    Args:
        filename: Name of the source file (for metadata).
        content: Full text content of the document.
        chunk_size: Target size of each chunk in characters.
        overlap: Number of characters to overlap between chunks.

    Returns:
        List of dicts with keys: id, text, metadata.
    """
    chunks = []
    if not content or not content.strip():
        return chunks

    # Split by paragraphs first, then combine into chunks
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

    current_chunk = ""
    chunk_index = 0

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 > chunk_size and current_chunk:
            # Save current chunk
            chunks.append({
                "id": _make_id("policy", filename, chunk_index),
                "text": current_chunk.strip(),
                "metadata": {
                    "doc_type": "policy",
                    "source_file": filename,
                    "chunk_index": chunk_index,
                },
            })
            chunk_index += 1
            # Start new chunk with overlap from end of previous
            if overlap > 0 and len(current_chunk) > overlap:
                current_chunk = current_chunk[-overlap:] + "\n\n" + para
            else:
                current_chunk = para
        else:
            current_chunk = (current_chunk + "\n\n" + para) if current_chunk else para

    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append({
            "id": _make_id("policy", filename, chunk_index),
            "text": current_chunk.strip(),
            "metadata": {
                "doc_type": "policy",
                "source_file": filename,
                "chunk_index": chunk_index,
            },
        })

    return chunks

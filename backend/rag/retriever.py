# backend/rag/retriever.py
"""Retrieval logic for the RAG pipeline.

Embeds the user's query, retrieves the most relevant document chunks
from the vector store, and formats them into context for the LLM.
"""

from backend.rag.embeddings import get_embedding


def retrieve_context(
    query: str,
    vector_store,
    api_key: str,
    n_results: int = 10,
    filters: dict = None,
) -> tuple:
    """Retrieve relevant context for a user query.

    Args:
        query: The user's question or prompt.
        vector_store: FinanceVectorStore instance.
        api_key: OpenAI API key for generating query embedding.
        n_results: Number of results to retrieve.
        filters: Optional metadata filters (e.g., {"doc_type": "transaction"}).

    Returns:
        Tuple of (formatted_context_string, raw_results_dict).
    """
    if vector_store.count() == 0:
        return "", {}

    # Embed the query
    query_embedding = get_embedding(query, api_key)

    # Retrieve from vector store
    results = vector_store.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where_filter=filters,
    )

    # Format the retrieved documents into context
    context = format_retrieved_context(
        documents=results.get("documents", [[]])[0],
        metadatas=results.get("metadatas", [[]])[0],
    )

    return context, results


def format_retrieved_context(documents: list, metadatas: list) -> str:
    """Format retrieved documents into a context string for the LLM.

    Groups documents by type and formats them with source citations.

    Args:
        documents: List of document text strings.
        metadatas: List of metadata dicts corresponding to each document.

    Returns:
        Formatted context string.
    """
    if not documents:
        return ""

    # Group by doc_type for cleaner formatting
    grouped = {}
    for doc, meta in zip(documents, metadatas):
        doc_type = meta.get("doc_type", "other")
        if doc_type not in grouped:
            grouped[doc_type] = []
        grouped[doc_type].append((doc, meta))

    sections = []

    # Transactions
    if "transaction" in grouped:
        lines = ["=== Relevant Transactions ==="]
        for doc, meta in grouped["transaction"]:
            lines.append(f"  • {doc}")
        sections.append("\n".join(lines))

    # Monthly summaries
    if "monthly_summary" in grouped:
        lines = ["=== Monthly Summaries ==="]
        for doc, meta in grouped["monthly_summary"]:
            lines.append(doc)
        sections.append("\n".join(lines))

    # Budget goals
    if "budget_goal" in grouped:
        lines = ["=== Budget Goals ==="]
        for doc, meta in grouped["budget_goal"]:
            lines.append(f"  • {doc}")
        sections.append("\n".join(lines))

    # Policy / knowledge base
    if "policy" in grouped:
        lines = ["=== Financial Guidelines ==="]
        for doc, meta in grouped["policy"]:
            source = meta.get("source_file", "unknown")
            lines.append(f"[{source}] {doc}")
        sections.append("\n".join(lines))

    # Catch-all for any other types
    for doc_type, items in grouped.items():
        if doc_type not in ("transaction", "monthly_summary", "budget_goal", "policy"):
            lines = [f"=== {doc_type.replace('_', ' ').title()} ==="]
            for doc, meta in items:
                lines.append(f"  • {doc}")
            sections.append("\n".join(lines))

    return "\n\n".join(sections)

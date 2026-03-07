# backend/rag/embeddings.py
"""OpenAI embedding helpers for the RAG pipeline."""

from openai import OpenAI

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


def get_embedding(text: str, api_key: str) -> list:
    """Get embedding vector for a single text string.

    Args:
        text: The text to embed.
        api_key: OpenAI API key.

    Returns:
        List of floats representing the embedding vector.
    """
    client = OpenAI(api_key=api_key)
    text = text.replace("\n", " ").strip()
    if not text:
        return [0.0] * EMBEDDING_DIMENSIONS

    response = client.embeddings.create(
        input=[text],
        model=EMBEDDING_MODEL,
    )
    return response.data[0].embedding


def get_embeddings_batch(texts: list, api_key: str) -> list:
    """Get embedding vectors for a batch of texts.

    Args:
        texts: List of text strings to embed.
        api_key: OpenAI API key.

    Returns:
        List of embedding vectors (each a list of floats).
    """
    if not texts:
        return []

    client = OpenAI(api_key=api_key)
    cleaned = [t.replace("\n", " ").strip() for t in texts]

    response = client.embeddings.create(
        input=cleaned,
        model=EMBEDDING_MODEL,
    )
    return [item.embedding for item in response.data]

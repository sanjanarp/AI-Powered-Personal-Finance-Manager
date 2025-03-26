import tiktoken

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count tokens in the given text using the tokenizer for the specified model."""
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

def trim_to_token_limit(text: str, max_tokens: int, model: str = "gpt-4") -> str:
    """
    Trims the input text so its token count is <= max_tokens.
    Returns the truncated text.
    """
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)

    if len(tokens) <= max_tokens:
        return text  # No trimming needed

    trimmed_tokens = tokens[:max_tokens]
    trimmed_text = encoding.decode(trimmed_tokens)
    return trimmed_text

def split_into_chunks(text: str, max_words: int) -> list[str]:
    if max_words < 1:
        raise ValueError("max_words must be at least 1")

    words = text.split()
    chunks: list[str] = []

    for start in range(0, len(words), max_words):
        chunk_words = words[start : start + max_words]
        chunk_text = " ".join(chunk_words)
        chunks.append(chunk_text)

    return chunks

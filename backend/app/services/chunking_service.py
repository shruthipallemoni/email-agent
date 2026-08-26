"""
Splits a long document into smaller pieces ("chunks") before embedding.

Why chunk at all? Two reasons:
1. Embedding models capture meaning better on a focused paragraph or two
   than on a 10-page document where the "meaning" gets averaged out.
2. When we retrieve results later, we want to hand the AI "the 3 relevant
   paragraphs", not the entire document - shorter, more relevant context
   produces better replies and costs less.

This chunker tries to break on paragraph boundaries first (keeping related
sentences together), and only falls back to a hard character cut if a
single paragraph is longer than one chunk by itself.
"""

DEFAULT_CHUNK_SIZE = 800  # characters, not tokens - a simple, dependency-free approximation
DEFAULT_OVERLAP = 100  # characters of overlap between consecutive chunks


def chunk_text(
    text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_OVERLAP
) -> list[str]:
    """
    Splits `text` into chunks of roughly `chunk_size` characters, each
    overlapping the previous one by `overlap` characters (so a sentence
    that happens to fall right on a chunk boundary doesn't lose context).
    """
    text = text.strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text]

    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}" if current else paragraph

        if len(candidate) <= chunk_size:
            current = candidate
            continue

        # Adding this paragraph would overflow the current chunk - close
        # the current chunk out first.
        if current:
            chunks.append(current)
            # Start the next chunk with a bit of overlap from the end of
            # the previous one, so context isn't lost at the seam.
            current = current[-overlap:] if overlap else ""
            candidate = f"{current}\n\n{paragraph}" if current else paragraph

        if len(paragraph) <= chunk_size:
            current = candidate
        else:
            # A single paragraph is bigger than a whole chunk - hard-split
            # it by characters, since we can't preserve paragraph structure.
            for start in range(0, len(paragraph), chunk_size - overlap):
                piece = paragraph[start : start + chunk_size]
                if piece:
                    chunks.append(piece)
            current = ""

    if current:
        chunks.append(current)

    return chunks
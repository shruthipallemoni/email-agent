"""
Turns text into an "embedding" - a list of numbers that represents what
the text MEANS, so we can later find text with similar meaning (not just
matching keywords) by comparing these numbers.

This uses Google's Gemini embedding model specifically (regardless of
which LLM_PROVIDER is chosen for chat/analysis), because it has a genuinely
free tier - see README for setup. This means RAG features need a
GEMINI_API_KEY in .env even if you're using Claude or GPT for everything
else in the app.
"""

from google import genai

from app.core.config import get_settings
from app.models.document import EMBEDDING_DIMENSIONS

settings = get_settings()

EMBEDDING_MODEL = "gemini-embedding-001"

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


async def embed_text(text: str) -> list[float]:
    """Converts one piece of text into an embedding vector."""
    client = _get_client()
    response = await client.aio.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=[text],
        config={"output_dimensionality": EMBEDDING_DIMENSIONS},
    )
    return response.embeddings[0].values


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Converts several pieces of text into embeddings in one API call -
    faster than calling embed_text() once per chunk when adding a document
    with many chunks.
    """
    if not texts:
        return []
    client = _get_client()
    response = await client.aio.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts,
        config={"output_dimensionality": EMBEDDING_DIMENSIONS},
    )
    return [embedding.values for embedding in response.embeddings]
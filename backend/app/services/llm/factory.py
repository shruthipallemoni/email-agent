"""
Picks which AI provider to actually use, based on the LLM_PROVIDER setting
in .env. This is the ONLY place in the app that needs to know all three
providers exist - everywhere else just calls get_llm_provider().
"""

from functools import lru_cache

from app.core.config import get_settings
from app.services.llm.anthropic_provider import AnthropicProvider
from app.services.llm.base import LLMProvider
from app.services.llm.gemini_provider import GeminiProvider
from app.services.llm.openai_provider import OpenAIProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    provider = settings.LLM_PROVIDER.lower()

    if provider == "anthropic":
        return AnthropicProvider(api_key=settings.ANTHROPIC_API_KEY, model=settings.LLM_MODEL)
    elif provider == "openai":
        return OpenAIProvider(api_key=settings.OPENAI_API_KEY, model=settings.LLM_MODEL)
    elif provider == "gemini":
        return GeminiProvider(api_key=settings.GEMINI_API_KEY, model=settings.LLM_MODEL)
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{settings.LLM_PROVIDER}'. Use 'anthropic', 'openai', or 'gemini'."
        )
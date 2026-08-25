"""
Wraps our LLM calls with Langfuse tracing, so every prompt sent to the AI
and every response it gives back is recorded somewhere you can browse,
search, and measure (how long each step took, what the AI actually saw,
which step is slow or expensive). This turns the agent from a black box
into something you can actually inspect and debug.

Langfuse (https://langfuse.com) has a free tier that's plenty for a
project like this - see the README for the 2-minute setup.

IMPORTANT: if Langfuse isn't configured (no keys in your .env), every
function below quietly does nothing. Tracing is purely optional
observability, never a requirement - the agent works exactly the same
either way. This matters because it means you can build and test this
whole project without ever signing up for anything, and turn tracing on
later with zero code changes.

Design note: we trace each real LLM call (analyze / generate reply /
validate reply) as its OWN observation, rather than nesting all three
under one shared "run" trace. That's a deliberate simplification - true
parent/child grouping across LangGraph's node execution would need extra
machinery we didn't want to bolt on here. Each call still shows up with
its full prompt, response, model, and timing - which is the part that
actually helps you debug and understand what the agent is doing.
"""

from contextlib import contextmanager
from typing import Iterator, Optional

from app.core.config import get_settings

settings = get_settings()

_ENABLED = bool(settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY)


def is_enabled() -> bool:
    return _ENABLED


def init_observability() -> None:
    """
    Call once when the app starts up (see the `lifespan` function in
    app/main.py) to register the Langfuse client with our credentials.
    Every other function in this file reuses that same client afterward.
    """
    if not _ENABLED:
        return

    from langfuse import Langfuse

    Langfuse(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        host=settings.LANGFUSE_BASE_URL,
    )


@contextmanager
def trace_llm_call(
    name: str, model: str, system_prompt: str, user_prompt: str
) -> Iterator[Optional[object]]:
    """
    Wraps one call to an LLM provider so it shows up in Langfuse as a
    "generation" - the exact prompt sent, the exact response received, and
    how long it took.

    Usage:
        with trace_llm_call("analyze_email", llm.model_name, SYSTEM_PROMPT, user_prompt) as generation:
            response = await llm.complete(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)
            if generation:
                generation.update(output=response)

    Yields None (and does nothing) when Langfuse isn't configured - always
    check `if generation:` before calling anything on it.
    """
    if not _ENABLED:
        yield None
        return

    from langfuse import get_client

    client = get_client()
    with client.start_as_current_observation(
        as_type="generation",
        name=name,
        model=model,
        input={"system": system_prompt, "user": user_prompt},
    ) as generation:
        yield generation
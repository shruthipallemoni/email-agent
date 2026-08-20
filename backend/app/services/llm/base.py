"""
Defines the common interface every AI provider (Claude, GPT, Gemini) must
follow.

Why this matters: the rest of the app (email analysis, reply generation
later) should never need to know or care which AI company we're using. It
just asks for "an LLM provider" and calls .complete(...) on it. This means
switching providers is a one-line settings change, not a rewrite.

This pattern is called "provider abstraction" - it's used any time you want
to support multiple interchangeable backends for the same job.
"""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        """
        Sends a request to the AI model and returns its raw text response.

        - system_prompt: instructions about HOW the AI should behave/respond
          (e.g. "You are an email classifier, always reply in JSON").
        - user_prompt: the actual content/question for this specific request
          (e.g. the email text to analyze).
        """
        raise NotImplementedError
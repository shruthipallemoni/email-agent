"""
Connects to Google's Gemini models.
"""

from google import genai
from google.genai import types

from app.services.llm.base import LLMProvider


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self._client = genai.Client(api_key=api_key)
        self.model_name = model

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        response = await self._client.aio.models.generate_content(
            model=self.model_name,
            contents=user_prompt,
            config=types.GenerateContentConfig(system_instruction=system_prompt),
        )
        return response.text or ""
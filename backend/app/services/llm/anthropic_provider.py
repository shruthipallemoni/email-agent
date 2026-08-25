"""
Connects to Anthropic's Claude models.
"""

from anthropic import AsyncAnthropic

from app.services.llm.base import LLMProvider


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self._client = AsyncAnthropic(api_key=api_key)
        self.model_name = model

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        response = await self._client.messages.create(
            model=self.model_name,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        # Claude's response can contain multiple content blocks - we join
        # any text blocks together to get the full reply.
        return "".join(block.text for block in response.content if block.type == "text")
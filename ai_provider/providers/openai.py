"""ai_provider/providers/openai.py — OpenAI GPT-4o провайдер."""

from __future__ import annotations
import os
import openai
from ai_provider.base import BaseAIProvider


class OpenAIProvider(BaseAIProvider):
    name = "openai"

    def __init__(self):
        self._key = os.getenv("OPENAI_API_KEY")
        self._client = openai.AsyncOpenAI(api_key=self._key) if self._key else None

    def is_available(self) -> bool:
        return bool(self._key)

    async def chat(self, messages, system=None, max_tokens=1000, temperature=0.7) -> str:
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        response = await self._client.chat.completions.create(
            model="gpt-4o",
            messages=full_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()

"""ai_provider/providers/yi.py — Yi (01.AI) провайдер (OpenAI-совместимый)."""

from __future__ import annotations
import os
import openai
from ai_provider.base import BaseAIProvider


class YiProvider(BaseAIProvider):
    name = "yi"

    def __init__(self):
        self._key = os.getenv("YI_API_KEY")
        self._client = openai.AsyncOpenAI(
            api_key=self._key,
            base_url="https://api.01.ai/v1",
        ) if self._key else None

    def is_available(self) -> bool:
        return bool(self._key)

    async def chat(self, messages, system=None, max_tokens=1000, temperature=0.7) -> str:
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        response = await self._client.chat.completions.create(
            model="yi-large",
            messages=full_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()

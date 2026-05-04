"""ai_provider/providers/cohere.py — Cohere провайдер."""

from __future__ import annotations
import os
from services.ai_provider.base import BaseAIProvider


class CohereProvider(BaseAIProvider):
    name = "cohere"

    def __init__(self):
        self._key = os.getenv("COHERE_API_KEY")

    def is_available(self) -> bool:
        return bool(self._key)

    async def chat(self, messages, system=None, max_tokens=1000, temperature=0.7) -> str:
        import cohere
        client = cohere.AsyncClientV2(api_key=self._key)

        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        response = await client.chat(
            model="command-r-plus-08-2024",
            messages=full_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.message.content[0].text.strip()

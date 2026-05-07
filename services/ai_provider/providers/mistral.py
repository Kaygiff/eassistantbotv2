"""ai_provider/providers/mistral.py — Mistral провайдер."""

from __future__ import annotations
import os
from services.ai_provider.base import BaseAIProvider


class MistralProvider(BaseAIProvider):
    name = "mistral"

    def __init__(self):
        self._key = os.getenv("MISTRAL_API_KEY")

    def is_available(self) -> bool:
        return bool(self._key)

    async def chat(self, messages, system=None, max_tokens=1000, temperature=0.7) -> str:
        from mistralai import Mistral
        client = Mistral(api_key=self._key)
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        response = await client.chat.complete_async(
            model="mistral-large-latest",
            messages=full_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()

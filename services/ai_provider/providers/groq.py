"""ai_provider/providers/groq.py — Groq (Llama) провайдер."""

from __future__ import annotations
import os
from services.ai_provider.base import BaseAIProvider


class GroqProvider(BaseAIProvider):
    name = "groq"

    def __init__(self):
        self._key = os.getenv("GROQ_API_KEY")

    def is_available(self) -> bool:
        return bool(self._key)

    async def chat(self, messages, system=None, max_tokens=1000, temperature=0.7) -> str:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=self._key)
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=full_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()

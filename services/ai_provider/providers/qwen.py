"""ai_provider/providers/qwen.py — Qwen (Alibaba) провайдер (OpenAI-совместимый)."""

from __future__ import annotations
import os
import openai
from services.ai_provider.base import BaseAIProvider


class QwenProvider(BaseAIProvider):
    name = "qwen"

    def __init__(self):
        self._key = os.getenv("QWEN_API_KEY")
        self._client = openai.AsyncOpenAI(
            api_key=self._key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        ) if self._key else None

    def is_available(self) -> bool:
        return bool(self._key)

    async def chat(self, messages, system=None, max_tokens=1000, temperature=0.7) -> str:
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        response = await self._client.chat.completions.create(
            model="qwen-max",
            messages=full_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()

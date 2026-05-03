"""
services/image/generator.py — Генерация изображений.
Провайдеры: DALL-E 3 (основной) → Stable Diffusion (fallback).
"""

from __future__ import annotations
import os
import logging

logger = logging.getLogger(__name__)

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
STABILITY_KEY = os.getenv("STABILITY_API_KEY")


async def generate_via_dalle(prompt: str) -> str | None:
    """Генерирует изображение через DALL-E 3."""
    if not OPENAI_KEY:
        return None
    try:
        import openai
        client = openai.AsyncOpenAI(api_key=OPENAI_KEY)
        response = await client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        return response.data[0].url
    except Exception as e:
        logger.warning(f"[ImageGen] DALL-E error: {e}")
        return None


async def generate_via_stability(prompt: str) -> str | None:
    """Генерирует изображение через Stability AI."""
    if not STABILITY_KEY:
        return None
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                headers={"Authorization": f"Bearer {STABILITY_KEY}", "Accept": "application/json"},
                json={
                    "text_prompts": [{"text": prompt, "weight": 1}],
                    "cfg_scale": 7,
                    "height": 1024,
                    "width": 1024,
                    "samples": 1,
                    "steps": 30,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            # Возвращаем base64 изображение как data URL
            img_b64 = data["artifacts"][0]["base64"]
            return f"data:image/png;base64,{img_b64}"
    except Exception as e:
        logger.warning(f"[ImageGen] Stability error: {e}")
        return None


async def generate_image(prompt: str) -> str | None:
    """
    Генерирует изображение по промпту.
    Возвращает URL или None при ошибке.
    """
    url = await generate_via_dalle(prompt)
    if url:
        return url
    return await generate_via_stability(prompt)

"""
services/image/generator.py — Генерация изображений.
Провайдеры: DALL-E 3 (основной) → Stable Diffusion (fallback).
"""

from __future__ import annotations
import os
import base64
import logging

logger = logging.getLogger(__name__)

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
STABILITY_KEY = os.getenv("STABILITY_API_KEY")


async def generate_via_dalle(prompt: str) -> bytes | None:
    """Генерирует изображение через DALL-E 3, возвращает байты."""
    if not OPENAI_KEY:
        return None
    try:
        import httpx
        import openai
        client = openai.AsyncOpenAI(api_key=OPENAI_KEY)
        response = await client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        url = response.data[0].url
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            return resp.content
    except Exception as e:
        logger.warning(f"[ImageGen] DALL-E error: {e}")
        return None


async def generate_via_stability(prompt: str) -> bytes | None:
    """Генерирует изображение через Stability AI, возвращает байты."""
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
                    "height": 512,
                    "width": 512,
                    "samples": 1,
                    "steps": 30,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            img_b64 = data["artifacts"][0]["base64"]
            return base64.b64decode(img_b64)
    except Exception as e:
        logger.warning(f"[ImageGen] Stability error: {e}")
        return None


async def generate_image(prompt: str) -> bytes | None:
    """
    Генерирует изображение по промпту.
    Возвращает байты изображения или None при ошибке.
    """
    img = await generate_via_dalle(prompt)
    if img:
        return img
    return await generate_via_stability(prompt)

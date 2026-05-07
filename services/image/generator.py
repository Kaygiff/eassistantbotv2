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
    """Генерирует изображение через Stability AI v2beta, возвращает байты."""
    if not STABILITY_KEY:
        return None
    try:
        import httpx
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.stability.ai/v2beta/stable-image/generate/core",
                headers={
                    "Authorization": f"Bearer {STABILITY_KEY}",
                    "Accept": "image/*",
                },
                files={"none": (None, "")},
                data={"prompt": prompt, "output_format": "jpeg"},
            )
            if resp.status_code != 200:
                logger.warning(f"[ImageGen] Stability raw error: {resp.text}")
                resp.raise_for_status()
            return resp.content
    except Exception as e:
        logger.warning(f"[ImageGen] Stability error: {e}")
        return None


async def _translate_to_english(prompt: str) -> str:
    """Переводит промпт на английский через AI hub (Mistral)."""
    try:
        from services.ai_provider.hub import get_hub
        hub = get_hub()
        result, _ = await hub.chat(
            messages=[{"role": "user", "content": prompt}],
            system="Translate the user text to English for an image generation prompt. Return ONLY the translated text, nothing else.",
            max_tokens=200,
            temperature=0.3,
        )
        return result.strip()
    except Exception as e:
        logger.warning(f"[ImageGen] Translation error: {e}")
        return prompt


async def generate_via_pollinations(prompt: str) -> bytes | None:
    """
    Генерирует изображение через Pollinations.ai — бесплатно, без ключей.
    Fallback когда DALL-E и Stability исчерпали баланс.
    """
    try:
        import httpx
        from urllib.parse import quote
        url = f"https://image.pollinations.ai/prompt/{quote(prompt)}?width=1024&height=1024&nologo=true&enhance=true"
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
                return resp.content
            logger.warning(f"[ImageGen] Pollinations error: {resp.status_code}")
            return None
    except Exception as e:
        logger.warning(f"[ImageGen] Pollinations error: {e}")
        return None


async def generate_image(prompt: str) -> bytes | None:
    """
    Генерирует изображение по промпту.
    Переводит на английский, затем пробует провайдеров по очереди:
    DALL-E 3 → Stability AI → Pollinations.ai (бесплатный fallback).
    Возвращает байты изображения или None при ошибке.
    """
    english_prompt = await _translate_to_english(prompt)
    logger.info(f"[ImageGen] Translated prompt: {english_prompt}")

    img = await generate_via_dalle(english_prompt)
    if img:
        return img

    img = await generate_via_stability(english_prompt)
    if img:
        return img

    logger.info("[ImageGen] Falling back to Pollinations.ai")
    return await generate_via_pollinations(english_prompt)

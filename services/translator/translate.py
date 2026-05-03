"""
services/translator/translate.py — Перевод текста.
Провайдеры: DeepL (основной) → Google Translate (fallback).
Определяет исходный язык автоматически.
"""

from __future__ import annotations
import os
import re
import logging

import httpx

logger = logging.getLogger(__name__)

DEEPL_KEY = os.getenv("DEEPL_API_KEY")
GOOGLE_KEY = os.getenv("GOOGLE_TRANSLATE_KEY")

TARGET_LANG_MAP = {
    "ru": "RU", "kz": "RU", "by": "RU", "uz": "RU",
    "tj": "RU", "tm": "RU", "kg": "RU", "en": "EN-GB",
}


def _extract_text_to_translate(raw: str) -> tuple[str, str | None]:
    """
    Извлекает текст и целевой язык из запроса.
    'переведи hello world на русский' → ('hello world', 'RU')
    'translate this text to english' → ('this text', 'EN-GB')
    """
    lang_patterns = [
        (r"на русск\w+", "RU"), (r"на английск\w+", "EN-GB"),
        (r"to russian", "RU"), (r"to english", "EN-GB"),
        (r"на казахск\w+", "KK"), (r"на узбекск\w+", "UZ"),
    ]
    target_lang = None
    text = raw

    for pattern, lang in lang_patterns:
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            target_lang = lang
            text = re.sub(pattern, "", raw, flags=re.IGNORECASE)
            break

    # Убираем триггерные слова
    text = re.sub(r"^(переведи|перевод|translate|перевести)\s*", "", text, flags=re.IGNORECASE).strip()
    return text, target_lang


async def translate_via_deepl(text: str, target_lang: str) -> str | None:
    """Переводит через DeepL API."""
    if not DEEPL_KEY:
        return None
    try:
        base_url = "https://api-free.deepl.com" if "free" in DEEPL_KEY.lower() else "https://api.deepl.com"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{base_url}/v2/translate",
                data={"auth_key": DEEPL_KEY, "text": text, "target_lang": target_lang},
            )
            resp.raise_for_status()
            return resp.json()["translations"][0]["text"]
    except Exception as e:
        logger.warning(f"[Translate] DeepL error: {e}")
        return None


async def translate_text(raw_query: str, language: str = "ru") -> str:
    """
    Главная функция перевода.
    Определяет текст и целевой язык, выбирает провайдера.
    """
    text, target_lang = _extract_text_to_translate(raw_query)

    if not text:
        return "✏️ Укажи текст для перевода.\n\nПример: *переведи hello world на русский*"

    if target_lang is None:
        target_lang = TARGET_LANG_MAP.get(language, "EN-GB")

    # Пробуем DeepL
    result = await translate_via_deepl(text, target_lang)

    if not result:
        return "❌ Сервис перевода временно недоступен."

    return f"🌐 *Перевод:*\n\n{result}"

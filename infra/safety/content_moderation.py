"""
safety/content_moderation.py — Модерация контента.
Проверяет только AI-чат и генерируемый AI-контент.
Действия между пользователями (actions) НЕ модерируются автоматически.
Провайдеры: OpenAI Moderation API и/или Azure Content Moderation.
"""

from __future__ import annotations
import os
import logging
from typing import Optional

import openai

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Список стоп-слов управляется через админпанель (хранится в Supabase)
_stopwords_cache: list[str] = []


async def load_stopwords() -> None:
    """Загружает стоп-слова из Supabase в память (кэш)."""
    from infra.db.supabase import supabase_admin
    try:
        res = supabase_admin.table("stopwords").select("word").execute()
        global _stopwords_cache
        _stopwords_cache = [row["word"].lower() for row in (res.data or [])]
    except Exception as e:
        logger.warning(f"Failed to load stopwords: {e}")


async def check_openai_moderation(text: str) -> tuple[bool, Optional[str]]:
    """
    Проверяет текст через OpenAI Moderation API.
    Возвращает (is_safe, category) где category — причина блокировки или None.
    """
    if not OPENAI_API_KEY:
        return True, None
    try:
        client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
        response = await client.moderations.create(input=text)
        result = response.results[0]
        if result.flagged:
            # Находим категорию с наибольшим score
            cats = result.categories.model_dump()
            flagged_cats = [k for k, v in cats.items() if v]
            return False, flagged_cats[0] if flagged_cats else "unknown"
        return True, None
    except Exception as e:
        logger.warning(f"OpenAI moderation failed: {e}")
        return True, None  # При ошибке пропускаем — не блокируем


def check_stopwords(text: str) -> tuple[bool, Optional[str]]:
    """Проверяет текст на стоп-слова из списка."""
    text_lower = text.lower()
    for word in _stopwords_cache:
        if word in text_lower:
            return False, word
    return True, None


async def moderate_text(text: str) -> tuple[bool, Optional[str]]:
    """
    Полная проверка текста.
    Используется ТОЛЬКО для AI-чата и генерируемого AI-контента.

    Возвращает:
        (True, None)         — текст безопасен
        (False, reason)      — текст заблокирован, reason — причина
    """
    # 1. Стоп-слова (быстрая локальная проверка)
    is_safe, reason = check_stopwords(text)
    if not is_safe:
        return False, f"stopword:{reason}"

    # 2. OpenAI Moderation API
    is_safe, category = await check_openai_moderation(text)
    if not is_safe:
        return False, f"openai:{category}"

    return True, None

"""
safety/content_moderation.py — Модерация контента через стоп-слова.
"""

from __future__ import annotations
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_stopwords_cache: list[str] = []


async def load_stopwords() -> None:
    from infra.db.supabase import get_supabase_admin
    try:
        res = get_supabase_admin().table("stopwords").select("word").execute()
        global _stopwords_cache
        _stopwords_cache = [row["word"].lower() for row in (res.data or [])]
    except Exception as e:
        logger.warning(f"Failed to load stopwords: {e}")


def check_stopwords(text: str) -> tuple[bool, Optional[str]]:
    text_lower = text.lower()
    for word in _stopwords_cache:
        if word in text_lower:
            return False, word
    return True, None


async def moderate_text(text: str) -> tuple[bool, Optional[str]]:
    is_safe, reason = check_stopwords(text)
    if not is_safe:
        return False, f"stopword:{reason}"
    return True, None

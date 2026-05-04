"""
services/translator/translate.py — Перевод текста через AI (Mistral/hub).
"""

from __future__ import annotations
import re
import logging

logger = logging.getLogger(__name__)

LANG_NAMES = {
    "ru": "русский", "kz": "казахский", "uz": "узбекский",
    "tj": "таджикский", "tm": "туркменский", "kg": "кыргызский",
    "by": "белорусский", "en": "English",
}

LANG_PATTERNS = [
    (r"на русск\w+", "русский"),
    (r"на английск\w+", "английский"),
    (r"на казахск\w+", "казахский"),
    (r"на узбекск\w+", "узбекский"),
    (r"на таджикск\w+", "таджикский"),
    (r"на туркменск\w+", "туркменский"),
    (r"на кыргызск\w+", "кыргызский"),
    (r"на белорусск\w+", "белорусский"),
    (r"to russian", "русский"),
    (r"to english", "английский"),
    (r"to kazakh", "казахский"),
]


def _extract(raw: str) -> tuple[str, str | None]:
    """Извлекает текст и целевой язык из запроса."""
    target_lang = None
    text = raw

    for pattern, lang in LANG_PATTERNS:
        if re.search(pattern, raw, re.IGNORECASE):
            target_lang = lang
            text = re.sub(pattern, "", raw, flags=re.IGNORECASE)
            break

    text = re.sub(
        r"^(переведи|перевод|переводи|translate|перевести)\s*",
        "", text, flags=re.IGNORECASE
    ).strip()

    return text, target_lang


async def translate_text(raw_query: str, language: str = "ru") -> str:
    """Переводит текст через AI hub."""
    from services.ai_provider.hub import get_hub

    text, target_lang = _extract(raw_query)

    if not text:
        return "✏️ Укажи текст для перевода.\n\nПример: *переведи hello world на русский*"

    if target_lang is None:
        target_lang = LANG_NAMES.get(language, "английский")

    system = (
        f"You are a professional translator. "
        f"Translate the user's text to {target_lang}. "
        f"Return ONLY the translated text, nothing else."
    )

    hub = get_hub()
    try:
        result, _ = await hub.chat(
            messages=[{"role": "user", "content": text}],
            system=system,
            max_tokens=500,
            temperature=0.3,
        )
        return f"🌐 *Перевод на {target_lang}:*\n\n{result.strip()}"
    except Exception as e:
        logger.error(f"[Translate] AI error: {e}")
        return "❌ Сервис перевода временно недоступен."

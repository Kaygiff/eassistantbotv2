"""
i18n — загрузчик локализаций.
Поддерживаемые языки: ru, kz, uz, tj, tm, kg, by, en.
Fallback: ru.
"""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

SUPPORTED_LANGS = {"ru", "kz", "uz", "tj", "tm", "kg", "by", "en"}
FALLBACK_LANG = "ru"
LOCALES_DIR = Path(__file__).parent / "locales"


@lru_cache()
def _load_locale(lang: str) -> dict[str, Any]:
    path = LOCALES_DIR / f"{lang}.json"
    if not path.exists():
        path = LOCALES_DIR / f"{FALLBACK_LANG}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@lru_cache()
def _load_fallback() -> dict[str, Any]:
    return _load_locale(FALLBACK_LANG)


def _get_nested(data: dict, key_path: str) -> str | None:
    """Получает значение по пути 'section.key'."""
    parts = key_path.split(".", 1)
    if len(parts) == 1:
        return data.get(key_path)
    section, rest = parts
    section_data = data.get(section, {})
    if not isinstance(section_data, dict):
        return None
    return _get_nested(section_data, rest)


def t(lang: str, key: str, **kwargs: Any) -> str:
    """
    Возвращает локализованную строку.

    Использование:
        t("ru", "economy.balance", balance=500)
        t("en", "common.error")
    """
    if lang not in SUPPORTED_LANGS:
        lang = FALLBACK_LANG

    locale = _load_locale(lang)
    text = _get_nested(locale, key)

    if not text:
        # Fallback на русский
        fallback = _load_fallback()
        text = _get_nested(fallback, key)

    if not text:
        return f"[{key}]"  # Ключ не найден — явно показываем

    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass

    return text


def get_language_keyboard() -> list[dict]:
    """Возвращает список кнопок для выбора языка."""
    return [
        {"text": "🇷🇺 Русский", "callback_data": "lang:ru"},
        {"text": "🇰🇿 Қазақша", "callback_data": "lang:kz"},
        {"text": "🇺🇿 O'zbekcha", "callback_data": "lang:uz"},
        {"text": "🇹🇯 Тоҷикӣ", "callback_data": "lang:tj"},
        {"text": "🇹🇲 Türkmençe", "callback_data": "lang:tm"},
        {"text": "🇰🇬 Кыргызча", "callback_data": "lang:kg"},
        {"text": "🇧🇾 Беларуская", "callback_data": "lang:by"},
        {"text": "🇬🇧 English", "callback_data": "lang:en"},
    ]

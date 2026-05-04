"""
services/library/books.py — Поиск книг через Google Books API.
"""

from __future__ import annotations
import os
import logging
import httpx

logger = logging.getLogger(__name__)
GOOGLE_BOOKS_KEY = os.getenv("GOOGLE_BOOKS_KEY")


async def search_books(query: str, language: str = "ru") -> str:
    """Ищет книги через Google Books и возвращает форматированный список."""
    try:
        params = {
            "q": query,
            "maxResults": 5,
            "langRestrict": "ru" if language in ("ru", "kz", "by") else "en",
            "printType": "books",
        }
        if GOOGLE_BOOKS_KEY:
            params["key"] = GOOGLE_BOOKS_KEY

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("https://www.googleapis.com/books/v1/volumes", params=params)
            resp.raise_for_status()
            data = resp.json()

        items = data.get("items", [])
        if not items:
            return f"🔍 Книги по запросу *{query}* не найдены."

        lines = [f"📚 *Книги по запросу «{query}»:*\n"]
        for item in items[:5]:
            info = item.get("volumeInfo", {})
            title = info.get("title", "Без названия")
            authors = ", ".join(info.get("authors", ["Неизвестен"]))
            year = info.get("publishedDate", "")[:4]
            rating = info.get("averageRating")
            preview = info.get("previewLink", "")

            line = f"📖 *{title}*\n👤 {authors}"
            if year:
                line += f" · {year}"
            if rating:
                line += f" · ⭐ {rating}"
            if preview:
                # \u200b — нулевой пробел, убирает превью Telegram но ссылка кликабельна
                line += f"\n\u200b[Читать]({preview})"
            lines.append(line)

        return "\n\n".join(lines)

    except Exception as e:
        logger.error(f"[Books] Error for '{query}': {e}")
        return "❌ Не удалось найти книги."

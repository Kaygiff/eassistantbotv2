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
    """Ищет самую популярную книгу по запросу."""
    try:
        params = {
            "q": query,
            "maxResults": 5,
            "orderBy": "relevance",
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

        # Берём первую (самую релевантную)
        info = items[0].get("volumeInfo", {})
        title = info.get("title", "Без названия")
        authors = ", ".join(info.get("authors", ["Неизвестен"]))
        year = info.get("publishedDate", "")[:4]
        rating = info.get("averageRating")
        description = info.get("description", "")
        if len(description) > 300:
            description = description[:300].rsplit(" ", 1)[0] + "..."

        text = f"📖 *{title}*\n👤 {authors}"
        if year:
            text += f" · {year}"
        if rating:
            text += f" · ⭐ {rating}"
        if description:
            text += f"\n\n{description}"

        return text

    except Exception as e:
        logger.error(f"[Books] Error for '{query}': {e}")
        return "❌ Не удалось найти книги."

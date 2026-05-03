"""
services/library/anime.py — Поиск аниме через Jikan API (MyAnimeList).
"""

from __future__ import annotations
import logging
import httpx

logger = logging.getLogger(__name__)


async def search_anime(query: str, language: str = "ru") -> str:
    """Ищет аниме через Jikan API и возвращает форматированный список."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.jikan.moe/v4/anime",
                params={"q": query, "limit": 5, "sfw": True},
            )
            resp.raise_for_status()
            data = resp.json()

        items = data.get("data", [])
        if not items:
            return f"🔍 Аниме по запросу *{query}* не найдено."

        lines = [f"🎌 *Аниме по запросу «{query}»:*\n"]
        for anime in items[:5]:
            title = anime.get("title", "Без названия")
            title_ru = anime.get("title_russian") or title
            episodes = anime.get("episodes", "?")
            score = anime.get("score", "?")
            status = anime.get("status", "")
            url = anime.get("url", "")
            anime_type = anime.get("type", "")

            line = f"🎬 *{title_ru}*"
            if title_ru != title:
                line += f" ({title})"
            line += f"\n📺 {anime_type} · {episodes} эп. · ⭐ {score}"
            if status:
                line += f" · {status}"
            if url:
                line += f"\n🔗 [MyAnimeList]({url})"
            lines.append(line)

        return "\n\n".join(lines)

    except Exception as e:
        logger.error(f"[Anime] Error for '{query}': {e}")
        return "❌ Не удалось найти аниме."

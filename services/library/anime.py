"""
services/library/anime.py — Поиск аниме через AniList GraphQL API.
"""

from __future__ import annotations
import logging
import httpx

logger = logging.getLogger(__name__)

ANILIST_URL = "https://graphql.anilist.co"

QUERY = """
query ($search: String) {
  Page(perPage: 5) {
    media(search: $search, type: ANIME, sort: POPULARITY_DESC) {
      title { romaji english native }
      episodes
      averageScore
      status
      siteUrl
    }
  }
}
"""


async def search_anime(query: str, language: str = "ru") -> str:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                ANILIST_URL,
                json={"query": QUERY, "variables": {"search": query}},
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()

        items = data.get("data", {}).get("Page", {}).get("media", [])
        if not items:
            return f"🔍 Аниме по запросу *{query}* не найдено."

        anime = items[0]
        title_en = anime["title"].get("english") or anime["title"].get("romaji", "Без названия")
        title_jp = anime["title"].get("native", "")
        episodes = anime.get("episodes") or "?"
        score = anime.get("averageScore")
        status_map = {
            "FINISHED": "Завершён",
            "RELEASING": "Выходит",
            "NOT_YET_RELEASED": "Анонс",
            "CANCELLED": "Отменён",
        }
        status = status_map.get(anime.get("status", ""), "")
        url = anime.get("siteUrl", "")

        text = f"🎌 *{title_en}*"
        if title_jp:
            text += f"\n_{title_jp}_"
        text += f"\n📺 {episodes} эп."
        if score:
            text += f" · ⭐ {score}/100"
        if status:
            text += f" · {status}"
        if url:
            text += f"\n\n[AniList]({url})"

        return text

    except Exception as e:
        logger.error(f"[Anime] Error for '{query}': {e}")
        return "❌ Не удалось найти аниме."

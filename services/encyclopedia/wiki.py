"""
services/encyclopedia/wiki.py — Wikipedia и энциклопедические запросы.
Кэш в Redis на 1 час.
"""

from __future__ import annotations
import logging

import httpx

from infra.db.redis import get_redis, encyclopedia_cache_key

logger = logging.getLogger(__name__)
CACHE_TTL = 3600

WIKI_LANG_MAP = {
    "ru": "ru", "kz": "ru", "by": "ru", "uz": "uz",
    "tj": "ru", "tm": "ru", "kg": "ru", "en": "en",
}

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "EAssistantBot/2.0 (Telegram bot; https://t.me/eassistantbot)",
}


async def get_article(query: str, language: str = "ru") -> str:
    """Возвращает краткую справку из Wikipedia."""
    redis = get_redis()
    cache_key = encyclopedia_cache_key(query, language)

    cached = await redis.get(cache_key)
    if cached:
        return cached

    wiki_lang = WIKI_LANG_MAP.get(language, "ru")

    try:
        async with httpx.AsyncClient(timeout=10.0, headers=HEADERS) as client:
            resp = await client.get(
                f"https://{wiki_lang}.wikipedia.org/api/rest_v1/page/summary/{query}",
            )
            if resp.status_code == 404:
                search_resp = await client.get(
                    f"https://{wiki_lang}.wikipedia.org/w/api.php",
                    params={"action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": 1},
                )
                search_data = search_resp.json()
                results = search_data.get("query", {}).get("search", [])
                if not results:
                    return f"🔍 По запросу *{query}* ничего не найдено."

                title = results[0]["title"]
                resp = await client.get(
                    f"https://{wiki_lang}.wikipedia.org/api/rest_v1/page/summary/{title}",
                )

            resp.raise_for_status()
            data = resp.json()

        title = data.get("title", query)
        extract = data.get("extract", "")

        if not extract:
            return f"🔍 По запросу *{query}* ничего не найдено."

        if len(extract) > 500:
            extract = extract[:500].rsplit(".", 1)[0] + "."

        text = f"📚 *{title}*\n\n{extract}"

        await redis.setex(cache_key, CACHE_TTL, text)
        return text

    except Exception as e:
        logger.error(f"[Encyclopedia] Error for '{query}': {e}")
        return "❌ Не удалось получить информацию."

"""
services/music/downloader.py — Поиск и отправка музыки через SoundCloud.
Кэш: сначала проверяем Supabase → если есть, отдаём CDN URL.
Если нет — скачиваем, загружаем в Storage, кэшируем.
"""

from __future__ import annotations
import asyncio
import logging
import os
import tempfile
import httpx
from pathlib import Path

logger = logging.getLogger(__name__)

SOUNDCLOUD_CLIENT_ID = os.getenv("SOUNDCLOUD_CLIENT_ID", "")


async def search_and_send(chat_id: int, query: str, language: str, bot) -> None:
    """Ищет трек по запросу и отправляет аудио в чат."""
    from core.i18n.loader import t
    from infra.db.storage import upload_file

    # 1. Ищем в кэше
    cached = await _find_cached(query)
    if cached:
        await bot.send_audio(
            chat_id,
            audio=cached["storage_url"],
            title=cached.get("title", query),
            performer=cached.get("artist", ""),
        )
        return

    # 2. Получаем список кандидатов с SoundCloud (до 10 штук)
    candidates = await _search_tracks(query)
    if not candidates:
        await bot.send_message(chat_id, t(language, "common.not_found"))
        return

    # 3. Перебираем кандидатов пока не скачается хоть один
    track = None
    file_path = None
    for candidate in candidates:
        try:
            fp, _ = await _download_track(candidate)
            if fp:
                track = candidate
                file_path = fp
                break
            logger.debug(f"[Music] Skipping track {candidate['id']} — stream unavailable")
        except Exception as e:
            logger.debug(f"[Music] Skipping track {candidate['id']}: {e}")
            continue

    if not file_path or not track:
        await bot.send_message(chat_id, t(language, "common.not_found"))
        return

    # 4. Загружаем в Supabase Storage и отправляем
    try:
        audio_data = Path(file_path).read_bytes()
        track_id = str(track["id"])
        title = track.get("title", query)
        artist = track.get("artist", "")

        storage_path = f"music/{track_id}.mp3"
        cdn_url = await upload_file(audio_data, storage_path, "audio/mpeg")

        # Кэшируем
        from infra.db.supabase import get_supabase_admin
        supabase_admin = get_supabase_admin()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: supabase_admin.table("music_cache").upsert({
                "youtube_id": track_id,
                "title": title,
                "artist": artist,
                "storage_url": cdn_url,
            }).execute()
        )

        from aiogram.types import BufferedInputFile
        audio_bytes = BufferedInputFile(audio_data, filename=f"{artist} - {title}.mp3")
        await bot.send_audio(
            chat_id,
            audio=audio_bytes,
            title=title,
            performer=artist,
        )

        os.unlink(file_path)

    except Exception as e:
        logger.error(f"[Music] Upload/send failed: {e}")
        await bot.send_message(chat_id, t(language, "common.error"))


async def _search_tracks(query: str) -> list[dict]:
    """
    Ищет треки на SoundCloud. Возвращает список кандидатов —
    сначала оригиналы (без ремиксов), потом всё остальное.
    """
    url = "https://api-v2.soundcloud.com/search/tracks"
    params = {
        "q": query,
        "client_id": SOUNDCLOUD_CLIENT_ID,
        "limit": 10,
        "offset": 0,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            logger.warning(f"[Music] SoundCloud search failed: {resp.status_code}")
            return []

        tracks = resp.json().get("collection", [])

    if not tracks:
        return []

    skip_words = ["remix", "cover", "remake", "mashup", "bootleg", "edit", "flip",
                  "ремикс", "кавер", "переделка"]

    def _to_dict(t: dict) -> dict:
        return {
            "id": t["id"],
            "title": t.get("title", query),
            "artist": t.get("user", {}).get("username", ""),
            "stream_url": t.get("media", {}).get("transcodings", []),
        }

    # Сначала оригиналы, потом ремиксы — так перебор найдёт рабочий быстрее
    originals = [_to_dict(t) for t in tracks
                 if not any(w in t.get("title", "").lower() for w in skip_words)]
    rest = [_to_dict(t) for t in tracks
            if any(w in t.get("title", "").lower() for w in skip_words)]

    return originals + rest


async def _get_stream_url(transcodings: list) -> str | None:
    """Получает прямую ссылку на аудио поток."""
    progressive = None
    for t in transcodings:
        fmt = t.get("format", {})
        if fmt.get("protocol") == "progressive":
            progressive = t
            break

    if not progressive:
        progressive = transcodings[0] if transcodings else None

    if not progressive:
        return None

    url = progressive["url"]
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params={"client_id": SOUNDCLOUD_CLIENT_ID})
        if resp.status_code != 200:
            return None
        return resp.json().get("url")


async def _download_track(track: dict) -> tuple[str | None, str | None]:
    """Скачивает трек и сохраняет во временный файл."""
    transcodings = track.get("stream_url", [])
    if not transcodings:
        return None, None

    stream_url = await _get_stream_url(transcodings)
    if not stream_url:
        return None, None

    tmp_dir = tempfile.mkdtemp()
    file_path = os.path.join(tmp_dir, f"{track['id']}.mp3")

    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        resp = await client.get(stream_url)
        if resp.status_code != 200:
            return None, None
        with open(file_path, "wb") as f:
            f.write(resp.content)

    return file_path, tmp_dir


async def _find_cached(query: str) -> dict | None:
    """Ищет трек в кэше по названию."""
    from infra.db.supabase import get_supabase_admin
    supabase_admin = get_supabase_admin()
    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(
        None,
        lambda: supabase_admin.table("music_cache")
        .select("*")
        .ilike("title", f"%{query}%")
        .limit(1)
        .execute()
    )
    if res.data:
        return res.data[0]
    return None

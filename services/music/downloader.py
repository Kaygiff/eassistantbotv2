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

<<<<<<< HEAD
YOUTUBE_COOKIES = os.getenv("YOUTUBE_COOKIES", "")


def _write_cookies_file(tmp_dir: str) -> str | None:
    """Записывает cookies из переменной окружения во временный файл."""
    if not YOUTUBE_COOKIES:
        return None
    cookies_path = os.path.join(tmp_dir, "cookies.txt")
    with open(cookies_path, "w") as f:
        f.write(YOUTUBE_COOKIES)
    return cookies_path
=======
SOUNDCLOUD_CLIENT_ID = os.getenv("SOUNDCLOUD_CLIENT_ID", "")
>>>>>>> b7573452c1d5966f86a65e5a4911c727b080cd1b


async def search_and_send(chat_id: int, query: str, language: str, bot) -> None:
    """Ищет трек по запросу и отправляет аудио в чат."""
    from core.i18n.loader import t
    from infra.db.supabase import get_supabase_admin
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

    # 2. Ищем трек на SoundCloud
    track = await _search_track(query)
    if not track:
        await bot.send_message(chat_id, t(language, "common.not_found"))
        return

    # 3. Скачиваем трек
    try:
        file_path, tmp_dir = await _download_track(track)
    except Exception as e:
        logger.warning(f"[Music] Download failed for '{query}': {e}")
        await bot.send_message(chat_id, t(language, "common.not_found"))
        return

    if not file_path:
        await bot.send_message(chat_id, t(language, "common.not_found"))
        return

    # 4. Загружаем в Supabase Storage
    try:
        audio_data = Path(file_path).read_bytes()
        track_id = str(track["id"])
        title = track.get("title", query)
        artist = track.get("artist", "")

        storage_path = f"music/{track_id}.mp3"

        cdn_url = await upload_file(audio_data, storage_path, "audio/mpeg")

<<<<<<< HEAD
        # 4. Кэшируем в Supabase
        get_supabase_admin().table("music_cache").upsert({
            "youtube_id": track_info["youtube_id"],
            "title": track_info.get("title"),
            "artist": track_info.get("artist"),
            "storage_url": cdn_url,
        }).execute()

        # 5. Отправляем пользователю
        await bot.send_audio(
            chat_id,
            audio=cdn_url,
            title=track_info.get("title", query),
            performer=track_info.get("artist", ""),
        )

        os.unlink(track_info["file_path"])
=======
        # 5. Кэшируем
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

        # 6. Отправляем пользователю — байтами чтобы Telegram принял title/performer
        from aiogram.types import BufferedInputFile
        audio_bytes = BufferedInputFile(audio_data, filename=f"{artist} - {title}.mp3")
        await bot.send_audio(
            chat_id,
            audio=audio_bytes,
            title=title,
            performer=artist,
        )

        os.unlink(file_path)
>>>>>>> b7573452c1d5966f86a65e5a4911c727b080cd1b

    except Exception as e:
        logger.error(f"[Music] Upload/send failed: {e}")
        await bot.send_message(chat_id, t(language, "common.error"))


async def _search_track(query: str) -> dict | None:
    """Ищет оригинальный трек на SoundCloud (без ремиксов и каверов)."""
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
            return None

        data = resp.json()
        tracks = data.get("collection", [])

    if not tracks:
        return None

    # Фильтруем ремиксы и каверы
    skip_words = ["remix", "cover", "remake", "mashup", "bootleg", "edit", "flip",
                  "ремикс", "кавер", "переделка"]

    for track in tracks:
        title = track.get("title", "").lower()
        if not any(w in title for w in skip_words):
            return {
                "id": track["id"],
                "title": track.get("title", query),
                "artist": track.get("user", {}).get("username", ""),
                "stream_url": track.get("media", {}).get("transcodings", []),
            }

    # Если все треки с нежелательными словами — берём первый
    t = tracks[0]
    return {
        "id": t["id"],
        "title": t.get("title", query),
        "artist": t.get("user", {}).get("username", ""),
        "stream_url": t.get("media", {}).get("transcodings", []),
    }


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
<<<<<<< HEAD
    res = (
        get_supabase_admin().table("music_cache")
=======
    supabase_admin = get_supabase_admin()
    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(
        None,
        lambda: supabase_admin.table("music_cache")
>>>>>>> b7573452c1d5966f86a65e5a4911c727b080cd1b
        .select("*")
        .ilike("title", f"%{query}%")
        .limit(1)
        .execute()
    )
    if res.data:
        return res.data[0]
    return None
<<<<<<< HEAD


async def _download_track(query: str) -> dict | None:
    """
    Скачивает трек через yt-dlp в временный файл.
    Возвращает dict с file_path, youtube_id, title, artist.
    """
    import yt_dlp

    tmp_dir = tempfile.mkdtemp()
    cookies_path = _write_cookies_file(tmp_dir)

    ydl_opts = {
        "format": "140/bestaudio/best",
        "outtmpl": f"{tmp_dir}/%(id)s.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "default_search": "ytsearch1",
        "max_filesize": 50 * 1024 * 1024,
    }

    if cookies_path:
        ydl_opts["cookiefile"] = cookies_path

    loop = asyncio.get_event_loop()

    def _extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            if "entries" in info:
                info = info["entries"][0]
            return info

    try:
        info = await loop.run_in_executor(None, _extract)
        youtube_id = info.get("id", "unknown")
        ext = info.get("ext", "m4a")
        file_path = f"{tmp_dir}/{youtube_id}.{ext}"

        return {
            "youtube_id": youtube_id,
            "title": info.get("title", query),
            "artist": info.get("uploader", ""),
            "file_path": file_path,
        }
    except Exception as e:
        logger.warning(f"[Music] yt-dlp error: {e}")
        return None
=======
>>>>>>> b7573452c1d5966f86a65e5a4911c727b080cd1b

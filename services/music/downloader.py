"""
services/music/downloader.py — Поиск и отправка музыки через yt-dlp.
Кэш: сначала проверяем Supabase → если есть, отдаём CDN URL.
Если нет — скачиваем, загружаем в Storage, кэшируем.
"""

from __future__ import annotations
import asyncio
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

YOUTUBE_COOKIES = os.getenv("YOUTUBE_COOKIES", "")


def _write_cookies_file(tmp_dir: str) -> str | None:
    """Записывает cookies из переменной окружения во временный файл."""
    if not YOUTUBE_COOKIES:
        return None
    cookies_path = os.path.join(tmp_dir, "cookies.txt")
    with open(cookies_path, "w") as f:
        f.write(YOUTUBE_COOKIES)
    return cookies_path


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

    # 2. Скачиваем через yt-dlp
    try:
        track_info = await _download_track(query)
    except Exception as e:
        logger.warning(f"[Music] Download failed for '{query}': {e}")
        await bot.send_message(chat_id, t(language, "common.not_found"))
        return

    if not track_info:
        await bot.send_message(chat_id, t(language, "common.not_found"))
        return

    # 3. Загружаем в Supabase Storage
    try:
        audio_data = Path(track_info["file_path"]).read_bytes()
        storage_path = f"music/{track_info['youtube_id']}.mp3"
        cdn_url = await upload_file(audio_data, storage_path, "audio/mpeg")

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

    except Exception as e:
        logger.error(f"[Music] Upload/send failed: {e}")
        await bot.send_message(chat_id, t(language, "common.error"))


async def _find_cached(query: str) -> dict | None:
    """Ищет трек в кэше по названию."""
    from infra.db.supabase import get_supabase_admin
    res = (
        get_supabase_admin().table("music_cache")
        .select("*")
        .ilike("title", f"%{query}%")
        .limit(1)
        .execute()
    )
    if res.data:
        return res.data[0]
    return None


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

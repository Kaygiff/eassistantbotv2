"""
Supabase Storage + CDN.
Используется для: кэша музыки (mp3), аватаров, медиафайлов пользователей.
"""

import os
import mimetypes
from pathlib import Path
from infra.db.supabase import get_supabase_admin

BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "eassistant-media")
CDN_BASE = os.getenv("CDN_BASE_URL", "")

supabase_admin = get_supabase_admin()


def _public_url(path: str) -> str:
    """Возвращает публичный CDN-URL для файла."""
    if CDN_BASE:
        return f"{CDN_BASE}/{path}"
    # Fallback — прямой Supabase Storage URL
    res = supabase_admin.storage.from_(BUCKET).get_public_url(path)
    return res


async def upload_file(
    data: bytes,
    storage_path: str,
    content_type: str | None = None,
) -> str:
    """
    Загружает файл в Supabase Storage.
    Возвращает публичный URL.
    """
    if not content_type:
        content_type, _ = mimetypes.guess_type(storage_path)
        content_type = content_type or "application/octet-stream"

    supabase_admin.storage.from_(BUCKET).upload(
        path=storage_path,
        file=data,
        file_options={"content-type": content_type, "upsert": "true"},
    )
    return _public_url(storage_path)


async def file_exists(storage_path: str) -> bool:
    """Проверяет существование файла в Storage (используется для кэша музыки)."""
    try:
        files = supabase_admin.storage.from_(BUCKET).list(
            path=str(Path(storage_path).parent)
        )
        names = [f["name"] for f in files]
        return Path(storage_path).name in names
    except Exception:
        return False


async def get_public_url(storage_path: str) -> str:
    return _public_url(storage_path)


async def delete_file(storage_path: str) -> None:
    supabase_admin.storage.from_(BUCKET).remove([storage_path])

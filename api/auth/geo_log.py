"""
auth/geo_log.py — Логирование IP и геолокации при входе.
Только для аналитики. Блокировка по IP/GEO не применяется.
"""

from __future__ import annotations
import httpx
from typing import Optional

from api.audit.logger import log_action


async def get_geo_by_ip(ip: str) -> Optional[str]:
    """
    Определяет страну/регион по IP через ip-api.com (бесплатно, без ключа).
    Возвращает строку вида 'Russia, Moscow' или None при ошибке.
    """
    if not ip or ip in ("127.0.0.1", "::1", ""):
        return None
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.get(f"http://ip-api.com/json/{ip}?fields=country,regionName")
            data = res.json()
            if data.get("status") == "success":
                return f"{data.get('country', '')}, {data.get('regionName', '')}".strip(", ")
    except Exception:
        pass
    return None


async def log_user_entry(
    user_id: str,
    telegram_id: int,
    ip: Optional[str] = None,
) -> None:
    """
    Логирует вход пользователя с IP и геолокацией в Audit Log.
    Вызывается при каждом /start или первом сообщении сессии.
    """
    geo = await get_geo_by_ip(ip) if ip else None

    await log_action(
        user_id=user_id,
        action="user_entry",
        details={"telegram_id": telegram_id},
        ip_address=ip,
        geo=geo,
    )

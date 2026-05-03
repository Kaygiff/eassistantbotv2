"""
audit/logger.py — Журнал критических действий.
Логирует: авторизации, транзакции Ecoins, действия админов,
изменения профилей, блокировки, IP при входе.
Хранение: 90 дней, затем автоудаление.
"""

from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from db.supabase import supabase_admin


async def log_action(
    action: str,
    user_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    geo: Optional[str] = None,
) -> None:
    """
    Записывает событие в audit_log.

    Параметры:
        action     — тип события (напр. 'user_entry', 'ecoin_transfer', 'admin_ban')
        user_id    — UUID пользователя (nullable)
        details    — произвольный JSONB с деталями
        ip_address — IP-адрес (только для входов)
        geo        — страна/регион (только для входов)
    """
    try:
        record: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "action": action,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if user_id:
            record["user_id"] = user_id
        if details:
            record["details"] = details
        if ip_address:
            record["ip_address"] = ip_address
        if geo:
            record["geo"] = geo

        supabase_admin.table("audit_log").insert(record).execute()
    except Exception as e:
        # Audit log не должен ломать основной флоу
        import logging
        logging.getLogger("audit").error(f"Failed to write audit log: {e}")


async def log_ecoin_transaction(
    user_id: str,
    transaction_type: str,
    amount: int,
    reason: str,
    balance_after: int,
) -> None:
    """Удобная обёртка для логирования транзакций Ecoins."""
    await log_action(
        action="ecoin_transaction",
        user_id=user_id,
        details={
            "type": transaction_type,
            "amount": amount,
            "reason": reason,
            "balance_after": balance_after,
        },
    )


async def log_admin_action(
    admin_id: str,
    action: str,
    target_user_id: Optional[str] = None,
    details: Optional[dict] = None,
) -> None:
    """Удобная обёртка для логирования действий администраторов."""
    await log_action(
        action=f"admin_{action}",
        user_id=admin_id,
        details={
            "target_user_id": target_user_id,
            **(details or {}),
        },
    )


async def log_ban(
    user_id: str,
    banned_by: Optional[str],
    reason: Optional[str],
    ban_until: Optional[str] = None,
) -> None:
    """Логирование блокировки пользователя."""
    await log_action(
        action="user_banned",
        user_id=user_id,
        details={
            "banned_by": banned_by,
            "reason": reason,
            "ban_until": ban_until,
        },
    )


async def log_profile_change(user_id: str, changed_fields: list[str]) -> None:
    """Логирование изменений профиля."""
    await log_action(
        action="profile_updated",
        user_id=user_id,
        details={"fields": changed_fields},
    )

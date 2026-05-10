"""
virtual_world/blacklist/service.py — Чёрный список пользователей.

Логика:
- Блокировка/разблокировка через реплай на сообщение
- Заблокированный не может выполнять действия на блокирующего
- Односторонняя блокировка
- Просмотр своего списка с кнопками разблокировки
"""

from __future__ import annotations
import uuid
import logging

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from infra.db.supabase import get_supabase_admin

logger = logging.getLogger(__name__)


def _safe_execute(query):
    """Выполняет запрос и возвращает данные или []."""
    try:
        res = query.execute()
        return res.data or []
    except Exception as e:
        logger.warning(f"[Blacklist] DB error: {e}")
        return []


def _safe_single(query):
    """Выполняет запрос .limit(1) и возвращает первую запись или None."""
    try:
        res = query.limit(1).execute()
        return res.data[0] if res and res.data else None
    except Exception as e:
        logger.warning(f"[Blacklist] DB error: {e}")
        return None


async def add_to_blacklist(blocker_id: str, blocked_telegram_id: int, language: str) -> str:
    """Добавляет пользователя в ЧС по telegram_id (через реплай)."""
    row = _safe_single(
        get_supabase_admin()
        .table("users")
        .select("id, first_name, username")
        .eq("telegram_id", blocked_telegram_id)
    )
    if not row:
        return "🔍 Пользователь не найден — он должен быть зарегистрирован в боте."

    blocked_id = row["id"]
    if blocked_id == blocker_id:
        return "🤔 Нельзя заблокировать самого себя."

    # Проверяем — может уже в ЧС
    existing = _safe_single(
        get_supabase_admin()
        .table("blacklist")
        .select("id")
        .eq("blocker_id", blocker_id)
        .eq("blocked_id", blocked_id)
    )
    if existing:
        name = row.get("first_name") or f"@{row.get('username', '?')}"
        return f"ℹ️ *{name}* уже в твоём чёрном списке."

    get_supabase_admin().table("blacklist").insert({
        "id": str(uuid.uuid4()),
        "blocker_id": blocker_id,
        "blocked_id": blocked_id,
    }).execute()

    name = row.get("first_name") or f"@{row.get('username', '?')}"
    return f"🚫 *{name}* добавлен(а) в чёрный список. Он(а) больше не сможет выполнять действия на тебя."


async def remove_from_blacklist_by_telegram_id(blocker_id: str, blocked_telegram_id: int, language: str) -> str:
    """Убирает пользователя из ЧС по telegram_id (через реплай)."""
    row = _safe_single(
        get_supabase_admin()
        .table("users")
        .select("id, first_name, username")
        .eq("telegram_id", blocked_telegram_id)
    )
    if not row:
        return "🔍 Пользователь не найден."

    blocked_id = row["id"]
    get_supabase_admin().table("blacklist").delete() \
        .eq("blocker_id", blocker_id).eq("blocked_id", blocked_id).execute()

    name = row.get("first_name") or f"@{row.get('username', '?')}"
    return f"✅ *{name}* удалён(а) из чёрного списка."


async def remove_from_blacklist_by_uuid(blocker_id: str, blocked_uuid: str) -> str:
    """Убирает пользователя из ЧС по UUID (через кнопку)."""
    row = _safe_single(
        get_supabase_admin()
        .table("users")
        .select("first_name, username")
        .eq("id", blocked_uuid)
    )
    get_supabase_admin().table("blacklist").delete() \
        .eq("blocker_id", blocker_id).eq("blocked_id", blocked_uuid).execute()

    name = (row.get("first_name") or f"@{row.get('username', '?')}") if row else "Пользователь"
    return f"✅ *{name}* удалён(а) из чёрного списка."


async def get_blacklist(blocker_id: str) -> tuple[str, InlineKeyboardMarkup | None]:
    """
    Возвращает (текст, клавиатура) со списком заблокированных.
    Каждый пользователь — кнопка «Разблокировать».
    """
    rows = _safe_execute(
        get_supabase_admin()
        .table("blacklist")
        .select("blocked_id")
        .eq("blocker_id", blocker_id)
        .order("created_at", desc=True)
        .limit(50)
    )

    if not rows:
        return "✅ Твой чёрный список пуст.", None

    # Получаем данные заблокированных пользователей
    blocked_ids = [r["blocked_id"] for r in rows]
    users_res = _safe_execute(
        get_supabase_admin()
        .table("users")
        .select("id, first_name, username")
        .in_("id", blocked_ids)
    )

    # Строим словарь id → данные
    users_map = {u["id"]: u for u in users_res}

    text_lines = ["🚫 *Твой чёрный список:*\n"]
    buttons = []

    for i, row in enumerate(rows, 1):
        uid = row["blocked_id"]
        user = users_map.get(uid)
        if user:
            name = user.get("first_name") or f"@{user.get('username', '?')}"
            username_part = f" (@{user['username']})" if user.get("username") else ""
        else:
            name = "Неизвестный"
            username_part = ""

        text_lines.append(f"{i}. {name}{username_part}")
        buttons.append(
            InlineKeyboardButton(
                text=f"❌ {name}",
                callback_data=f"blacklist:unblock:{uid}",
            )
        )

    text = "\n".join(text_lines)

    # Кнопки по одной в строке
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[btn] for btn in buttons]
    )

    return text, keyboard


async def is_blocked(blocker_id: str, blocked_id: str) -> bool:
    """Проверяет, заблокировал ли blocker_id пользователя blocked_id."""
    row = _safe_single(
        get_supabase_admin()
        .table("blacklist")
        .select("id")
        .eq("blocker_id", blocker_id)
        .eq("blocked_id", blocked_id)
    )
    return row is not None

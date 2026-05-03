"""
virtual_world/actions/service.py — Действия между пользователями.
Обнять, поцеловать, подарить, ударить, и т.д.
"""

from __future__ import annotations
import uuid
import logging
from datetime import datetime, timezone, timedelta

from db.supabase import supabase_admin
from db.redis import get_redis, cooldown_key
from brain.context import BrainContext
from notifications.sender import notify_user

logger = logging.getLogger(__name__)

COOLDOWN_SECONDS = 300  # 5 минут между одинаковыми действиями на одну пару

ACTIONS = {
    "обнять": {"category": "friendly", "emoji": "🤗", "text": "{initiator} обнял(а) {target}!"},
    "обними": {"category": "friendly", "emoji": "🤗", "text": "{initiator} обнял(а) {target}!"},
    "поцеловать": {"category": "emotional", "emoji": "💋", "text": "{initiator} поцеловал(а) {target}!"},
    "поцелуй": {"category": "emotional", "emoji": "💋", "text": "{initiator} поцеловал(а) {target}!"},
    "погладить": {"category": "friendly", "emoji": "🤚", "text": "{initiator} погладил(а) {target}!"},
    "погладь": {"category": "friendly", "emoji": "🤚", "text": "{initiator} погладил(а) {target}!"},
    "ударить": {"category": "aggressive", "emoji": "👊", "text": "{initiator} ударил(а) {target}!"},
    "ударь": {"category": "aggressive", "emoji": "👊", "text": "{initiator} ударил(а) {target}!"},
    "укусить": {"category": "aggressive", "emoji": "😤", "text": "{initiator} укусил(а) {target}!"},
    "подарить": {"category": "gift", "emoji": "🎁", "text": "{initiator} подарил(а) {target} подарок!"},
}


def _detect_action(text: str) -> tuple[str, dict] | None:
    text_lower = text.lower()
    for keyword, data in ACTIONS.items():
        if keyword in text_lower:
            return keyword, data
    return None


async def _check_cooldown(initiator_id: str, target_id: str, action_type: str) -> bool:
    """True если кулдаун активен (действие недоступно)."""
    redis = get_redis()
    key = cooldown_key(initiator_id, target_id, action_type)
    return bool(await redis.get(key))


async def _set_cooldown(initiator_id: str, target_id: str, action_type: str) -> None:
    redis = get_redis()
    key = cooldown_key(initiator_id, target_id, action_type)
    await redis.setex(key, COOLDOWN_SECONDS, "1")


async def perform_action(ctx: BrainContext, bot) -> str | None:
    """Выполняет действие между пользователями."""
    initiator = ctx.user
    initiator_id = str(initiator.id)

    # Определяем действие
    action_data = _detect_action(ctx.text)
    if not action_data:
        return None
    action_type, action_info = action_data

    # Определяем цель
    target = None
    if ctx.reply_to_user_telegram_id:
        from auth.identity import get_user_by_telegram_id
        target = await get_user_by_telegram_id(ctx.reply_to_user_telegram_id)

    if not target:
        import re
        match = re.search(r"@(\w+)", ctx.text)
        if match:
            res = supabase_admin.table("users").select("*").eq("username", match.group(1)).maybe_single().execute()
            if res.data:
                from models.user import User
                target = User(**res.data)

    if not target:
        return "👥 Укажи пользователя через @username или ответь на его сообщение."

    target_id = str(target.id)

    if target_id == initiator_id:
        return "🤔 Нельзя выполнить действие на себя."

    # Проверяем чёрный список
    bl = supabase_admin.table("blacklist").select("id").eq("blocker_id", target_id).eq("blocked_id", initiator_id).maybe_single().execute()
    if bl.data:
        return "🚫 Этот пользователь заблокировал тебя."

    # Проверяем кулдаун
    if await _check_cooldown(initiator_id, target_id, action_type):
        return f"⏳ Подожди немного перед следующим *{action_type}*!"

    # Логируем действие
    supabase_admin.table("actions_log").insert({
        "id": str(uuid.uuid4()),
        "initiator_id": initiator_id,
        "target_id": target_id,
        "action_type": action_type,
        "category": action_info["category"],
    }).execute()

    # Устанавливаем кулдаун
    await _set_cooldown(initiator_id, target_id, action_type)

    # Формируем сообщение
    initiator_name = initiator.first_name or f"@{initiator.username}" or "Пользователь"
    target_name = target.first_name or f"@{target.username}" or "Пользователь"

    msg_template = action_info["text"]
    emoji = action_info["emoji"]
    msg = f"{emoji} {msg_template.format(initiator=initiator_name, target=target_name)}"

    # Уведомляем цель
    await notify_user(target_id, f"{emoji} *{initiator_name}* {action_type.replace('ть', 'л(а)')} тебя!")

    return msg

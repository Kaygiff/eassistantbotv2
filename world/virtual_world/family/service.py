"""
virtual_world/family/service.py — Семейные роли между пользователями.
"""

from __future__ import annotations
import uuid
import logging

from infra.db.supabase import supabase_admin
from bot.brain.context import BrainContext
from infra.notifications.sender import notify_user

logger = logging.getLogger(__name__)

ROLE_PAIRS = {
    "родитель": "ребёнок", "ребёнок": "родитель",
    "брат": "брат/сестра", "сестра": "брат/сестра",
    "дедушка": "внук/внучка", "бабушка": "внук/внучка",
    "внук": "дедушка/бабушка", "внучка": "дедушка/бабушка",
    "дядя": "племянник/племянница", "тётя": "племянник/племянница",
}


def _detect_role(text: str) -> str | None:
    text_lower = text.lower()
    for role in ROLE_PAIRS:
        if role in text_lower:
            return role
    return None


async def add_family_member(ctx: BrainContext, bot) -> str:
    """Отправляет запрос на добавление в семью."""
    initiator_id = str(ctx.user.id)

    # Определяем роль
    role = _detect_role(ctx.text)
    if not role:
        return "👨‍👩‍👧 Укажи роль. Например: *стать братом @username*"

    # Определяем цель
    import re
    match = re.search(r"@(\w+)", ctx.text)
    if not match:
        return "👥 Укажи пользователя через @username"

    res = supabase_admin.table("users").select("id, first_name, username").eq("username", match.group(1)).maybe_single().execute()
    if not res.data:
        return "🔍 Пользователь не найден."

    target = res.data
    target_id = target["id"]

    if target_id == initiator_id:
        return "🤔 Нельзя добавить самого себя."

    # Проверяем не существует ли уже связь
    existing = (
        supabase_admin.table("family_relations")
        .select("id")
        .or_(f"and(initiator_id.eq.{initiator_id},target_id.eq.{target_id}),and(initiator_id.eq.{target_id},target_id.eq.{initiator_id})")
        .maybe_single()
        .execute()
    )
    if existing.data:
        return "👨‍👩‍👧 Вы уже состоите в семейных отношениях."

    mirror_role = ROLE_PAIRS.get(role, "родственник")

    # Создаём запись со статусом pending
    supabase_admin.table("family_relations").insert({
        "id": str(uuid.uuid4()),
        "initiator_id": initiator_id,
        "target_id": target_id,
        "initiator_role": role,
        "target_role": mirror_role,
        "status": "pending",
    }).execute()

    initiator_name = ctx.user.first_name or f"@{ctx.user.username}"
    target_name = target.get("first_name") or f"@{target.get('username')}"

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    await notify_user(target_id,
        f"👨‍👩‍👧 *{initiator_name}* хочет стать твоим *{role}*!\n\nПринять приглашение?\n"
        f"_(Твоя роль: {mirror_role})_"
    )

    return f"✅ Запрос отправлен *{target_name}*.\nТвоя роль: *{role}*, их роль: *{mirror_role}*"


async def get_family_tree(user_id: str, language: str) -> str:
    """Возвращает список семейных связей пользователя."""
    res = (
        supabase_admin.table("family_relations")
        .select("*, users!initiator_id(first_name, username), users!target_id(first_name, username)")
        .or_(f"initiator_id.eq.{user_id},target_id.eq.{user_id}")
        .eq("status", "active")
        .execute()
    )
    relations = res.data or []

    if not relations:
        return "👨‍👩‍👧 У тебя пока нет семейных связей."

    lines = ["👨‍👩‍👧 *Моя семья:*\n"]
    for rel in relations:
        if rel["initiator_id"] == user_id:
            role = rel["initiator_role"]
            other = rel.get("users!target_id") or {}
        else:
            role = rel["target_role"]
            other = rel.get("users!initiator_id") or {}

        name = other.get("first_name") or f"@{other.get('username', '?')}"
        lines.append(f"• {role.capitalize()}: *{name}*")

    return "\n".join(lines)


async def handle_family_fsm(ctx: BrainContext, bot, state: str) -> bool:
    return False

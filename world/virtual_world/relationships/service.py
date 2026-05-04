"""
virtual_world/relationships/service.py — Отношения, браки, разводы.
"""

from __future__ import annotations
import uuid
import logging
from typing import Optional

from infra.db.supabase import get_supabase_admin
from core.models.user import User
from bot.brain.context import BrainContext
from api.auth.session import get_fsm_state, set_fsm_state, set_fsm_data, get_fsm_data, clear_fsm_state, clear_fsm_data
from core.i18n import t
from infra.notifications.sender import notify_user

logger = logging.getLogger(__name__)


def _ordered_pair(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a < b else (b, a)


async def get_current_relationship(user_id: str) -> Optional[dict]:
    res = (
        get_supabase_admin().table("relationships")
        .select("*")
        .or_(f"user_a_id.eq.{user_id},user_b_id.eq.{user_id}")
        .maybe_single()
        .execute()
    )
    return res.data


async def propose_dating(initiator: User, target: User, language: str, bot) -> str:
    """Предлагает начать отношения."""
    init_id = str(initiator.id)
    target_id = str(target.id)

    # Проверяем не в отношениях ли уже
    if await get_current_relationship(init_id):
        return t(language, "relationships.already_in_relation")

    # Проверяем чёрный список
    bl = get_supabase_admin().table("blacklist").select("id").eq("blocker_id", target_id).eq("blocked_id", init_id).maybe_single().execute()
    if bl.data:
        return t(language, "common.access_denied")

    target_name = target.first_name or f"@{target.username}" or "пользователь"
    init_name = initiator.first_name or f"@{initiator.username}" or "пользователь"

    # Уведомляем цель с кнопками
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❤️ Принять", callback_data=f"relationship:accept_dating:{init_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"relationship:decline_dating:{init_id}"),
    ]])

    await notify_user(
        target_id,
        f"💌 *{init_name}* предлагает тебе начать встречаться!\n\nПринять предложение?",
    )

    return t(language, "relationships.propose_dating", username=target_name)


async def get_relationship_status(user_id: str, language: str) -> str:
    """Возвращает текущий статус отношений."""
    rel = await get_current_relationship(user_id)
    if not rel:
        return "💔 Ты сейчас свободен(а)."

    partner_id = rel["user_b_id"] if rel["user_a_id"] == user_id else rel["user_a_id"]
    partner = get_supabase_admin().table("users").select("first_name, username").eq("id", partner_id).maybe_single().execute()
    partner_name = partner.data.get("first_name") or f"@{partner.data.get('username')}" if partner.data else "Неизвестно"

    status = rel["status"]
    since = rel["started_at"][:10]

    if status == "dating":
        return f"❤️ Вы встречаетесь с *{partner_name}* с {since}"
    elif status == "married":
        married_at = rel.get("married_at", since)[:10]
        return f"💍 Вы женаты с *{partner_name}* с {married_at}"

    return "💔 Статус отношений неизвестен."


async def breakup(user_id: str, language: str) -> str:
    """Разрывает текущие отношения."""
    rel = await get_current_relationship(user_id)
    if not rel:
        return "💔 У тебя нет активных отношений."

    get_supabase_admin().table("relationships").delete().eq("id", rel["id"]).execute()

    partner_id = rel["user_b_id"] if rel["user_a_id"] == user_id else rel["user_a_id"]
    await notify_user(partner_id, "💔 Ваши отношения завершены.")

    return t(language, "relationships.breakup")


async def propose_marriage(initiator: User, target: User, language: str, bot) -> str:
    """Предлагает пожениться (нужно быть в отношениях)."""
    init_id = str(initiator.id)
    target_id = str(target.id)

    rel = await get_current_relationship(init_id)
    if not rel:
        return "💔 Для брака нужно сначала встречаться."

    partner_id = rel["user_b_id"] if rel["user_a_id"] == init_id else rel["user_a_id"]
    if partner_id != target_id:
        return "💔 Предложение можно сделать только своему партнёру."

    if rel["status"] == "married":
        return "💍 Вы уже женаты!"

    init_name = initiator.first_name or f"@{initiator.username}"
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💍 Да!", callback_data=f"relationship:accept_marriage:{init_id}"),
        InlineKeyboardButton(text="❌ Нет", callback_data=f"relationship:decline_marriage:{init_id}"),
    ]])
    await notify_user(target_id, f"💍 *{init_name}* делает тебе предложение!\n\nСогласен(а)?")

    target_name = target.first_name or f"@{target.username}"
    return t(language, "relationships.propose_marriage", username=target_name)


async def divorce(user_id: str, language: str) -> str:
    """Оформляет развод."""
    rel = await get_current_relationship(user_id)
    if not rel or rel["status"] != "married":
        return "📝 Вы не состоите в браке."

    get_supabase_admin().table("relationships").delete().eq("id", rel["id"]).execute()

    partner_id = rel["user_b_id"] if rel["user_a_id"] == user_id else rel["user_a_id"]
    await notify_user(partner_id, "📝 Ваш брак расторгнут.")

    return t(language, "relationships.divorce")


async def handle_relationship_callback(ctx: BrainContext, action: str, param: str | None) -> str | None:
    """Обрабатывает callback кнопок отношений (принять/отклонить)."""
    user_id = str(ctx.user.id)

    if action == "accept_dating" and param:
        user_a_id, user_b_id = _ordered_pair(param, user_id)
        get_supabase_admin().table("relationships").insert({
            "id": str(uuid.uuid4()),
            "user_a_id": user_a_id,
            "user_b_id": user_b_id,
            "status": "dating",
        }).execute()
        await notify_user(param, f"❤️ {ctx.user.first_name or 'Пользователь'} принял(а) твоё предложение!")
        return t(ctx.language, "relationships.dating_accepted", username=ctx.user.first_name or "")

    elif action == "decline_dating" and param:
        await notify_user(param, "💔 Твоё предложение отклонено.")
        return "❌ Предложение отклонено."

    elif action == "accept_marriage" and param:
        rel = await get_current_relationship(user_id)
        if rel:
            from datetime import datetime, timezone
            get_supabase_admin().table("relationships").update({
                "status": "married",
                "married_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", rel["id"]).execute()
            await notify_user(param, "💒 Поздравляем! Вы теперь женаты!")
            return t(ctx.language, "relationships.married")

    elif action == "decline_marriage" and param:
        await notify_user(param, "💔 Предложение о браке отклонено.")
        return "❌ Предложение отклонено."

    return None


async def handle_relationship_fsm(ctx: BrainContext, bot, state: str) -> bool:
    return False

"""
bot/handlers/group.py — Обработка сообщений в групповых чатах.
"""

from __future__ import annotations
import logging

from aiogram import Router, F
from aiogram.types import Message, ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, JOIN_TRANSITION, LEAVE_TRANSITION

from bot.brain.context import BrainContext

logger = logging.getLogger(__name__)

group_router = Router()
group_router.message.filter(F.chat.type.in_({"group", "supergroup"}))


@group_router.message()
async def handle_group_message(message: Message) -> None:
    from api.auth.identity import get_or_create_user
    from bot.brain.group_router import process_group_message

    user, _ = await get_or_create_user(
        telegram_id=message.from_user.id,
        first_name=message.from_user.first_name or "",
        username=message.from_user.username,
    )

    ctx = BrainContext(
        telegram_id=message.from_user.id,
        chat_id=message.chat.id,
        message_id=message.message_id,
        text=message.text or "",
        is_group=True,
    )
    ctx.user = user
    ctx.language = user.language if user else "ru"
    ctx.extra["chat_title"] = message.chat.title or ""

    if message.reply_to_message and message.reply_to_message.from_user:
        reply_user = message.reply_to_message.from_user
        ctx.reply_to_user_telegram_id = reply_user.id
        ctx.extra["reply_to_user_name"] = (
            reply_user.first_name
            or (f"@{reply_user.username}" if reply_user.username else None)
            or f"id:{reply_user.id}"
        )

    await process_group_message(ctx, message.bot)


@group_router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def handle_member_join(event: ChatMemberUpdated) -> None:
    """Отправляет приветствие и правила при вступлении участника."""
    from world.groups.settings import get_group_by_chat_id

    group = await get_group_by_chat_id(event.chat.id)
    if not group:
        return

    user = event.new_chat_member.user
    name = user.first_name or user.username or "Участник"

    # Приветствие
    welcome = group.get("welcome_message")
    if welcome:
        try:
            text = welcome.replace("{name}", name)
            await event.bot.send_message(event.chat.id, text, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"[Group] Failed to send welcome: {e}")

    # Правила — отдельным сообщением после приветствия
    rules = group.get("rules_text")
    if rules:
        try:
            await event.bot.send_message(
                event.chat.id,
                f"📋 *Правила группы:*\n\n{rules}",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"[Group] Failed to send rules on join: {e}")


@group_router.chat_member(ChatMemberUpdatedFilter(LEAVE_TRANSITION))
async def handle_member_leave(event: ChatMemberUpdated) -> None:
    """Отправляет прощальное сообщение при выходе участника."""
    from world.groups.settings import get_group_by_chat_id

    group = await get_group_by_chat_id(event.chat.id)
    if not group:
        return

    farewell = group.get("farewell_message")
    if not farewell:
        return

    user = event.old_chat_member.user
    name = user.first_name or user.username or "Участник"

    try:
        text = farewell.replace("{name}", name)
        await event.bot.send_message(event.chat.id, text, parse_mode="Markdown")
    except Exception as e:
        logger.warning(f"[Group] Failed to send farewell: {e}")

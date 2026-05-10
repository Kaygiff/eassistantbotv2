"""
bot/handlers/group.py — Обработка сообщений в групповых чатах.
"""

from __future__ import annotations
import logging

import os

from aiogram import Router, F
from aiogram.types import Message, ChatMemberUpdated, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import ChatMemberUpdatedFilter, JOIN_TRANSITION, LEAVE_TRANSITION, Command

from bot.brain.context import BrainContext

logger = logging.getLogger(__name__)

group_router = Router()
group_router.message.filter(F.chat.type.in_({"group", "supergroup"}))

_RAILWAY_URL = os.getenv("RAILWAY_PUBLIC_DOMAIN", "eassistantbotv2-production.up.railway.app")
_GUIDE_URL = f"https://{_RAILWAY_URL}/guide"

HELP_TEXT = (
    "🎉 Вот лишь малая часть того, на что я способен:\n\n"
    "🤖 AI-чат на любые темы\n"
    "🎮 Казино и мини-игры на Ecoins\n"
    "🎵 Музыка по запросу\n"
    "🌤 Погода в любом городе\n"
    "👨‍👩‍👧 Виртуальная семья и питомцы\n"
    "💰 Экономика, бонусы, топ игроков\n\n"
    "Но это только начало — в руководстве спрятано всё остальное: "
    "скрытые команды, лайфхаки, как быстро заработать Ecoins и не только.\n\n"
    "📖 Загляни — там интереснее, чем кажется."
)


@group_router.message(Command("help", "справка", "руководство", "помощь"))
async def handle_group_help(message: Message) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📖 Открыть руководство", web_app={"url": _GUIDE_URL})]
        ]
    )
    await message.answer(HELP_TEXT, parse_mode="Markdown", reply_markup=keyboard)


@group_router.message()
async def handle_group_message(message: Message) -> None:
    from api.auth.identity import get_or_create_user
    from bot.brain.group_router import process_group_message

    ctx = BrainContext(
        telegram_id=message.from_user.id,
        chat_id=message.chat.id,
        message_id=message.message_id,
        text=message.text or "",
        is_group=True,
        tg_username=message.from_user.username,
        tg_first_name=message.from_user.first_name,
        tg_last_name=message.from_user.last_name,
        tg_is_premium=bool(getattr(message.from_user, "is_premium", False)),
        tg_locale=message.from_user.language_code,
    )
    ctx.extra["chat_title"] = message.chat.title or ""

    if message.reply_to_message and message.reply_to_message.from_user:
        reply_user = message.reply_to_message.from_user
        ctx.reply_to_user_telegram_id = reply_user.id
        ctx.reply_to_message_id = message.reply_to_message.message_id
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

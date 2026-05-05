"""
bot/handlers/group.py — Обработка сообщений в групповых чатах.
"""

from __future__ import annotations
import logging

from aiogram import Router, F
from aiogram.types import Message

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

    # Заполняем reply_to_user_telegram_id + имя если это ответ на сообщение
    if message.reply_to_message and message.reply_to_message.from_user:
        reply_user = message.reply_to_message.from_user
        ctx.reply_to_user_telegram_id = reply_user.id
        ctx.extra["reply_to_user_name"] = (
            reply_user.first_name
            or (f"@{reply_user.username}" if reply_user.username else None)
            or f"id:{reply_user.id}"
        )

    await process_group_message(ctx, message.bot)

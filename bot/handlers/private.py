"""
bot/handlers/private.py — Обработка личных сообщений (DM).
Создаёт BrainContext и передаёт в brain.router.process().

Slash-команды: только /start.
Все остальные функции — словесные (brain классифицирует текст).
"""

from __future__ import annotations
import logging

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from bot.brain.context import BrainContext
from bot.brain.intent import Intent
from bot.brain.router import process

logger = logging.getLogger(__name__)

private_router = Router()
private_router.message.filter(F.chat.type == "private")


@private_router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    ctx = _build_context(message)

    # Если онбординг уже запущен — возобновляем с текущего шага
    from bot.onboarding.flow import is_in_onboarding, resume_onboarding
    if await is_in_onboarding(str(message.from_user.id)):
        resumed = await resume_onboarding(ctx, message.bot)
        if resumed:
            return

    ctx.set_intent(Intent.START, confidence="keyword")
    await process(ctx, message.bot)


@private_router.message(F.voice)
async def handle_voice(message: Message) -> None:
    """Голосовые сообщения — передаём в Brain со специальным флагом."""
    ctx = _build_context(message)
    ctx.is_voice = True
    ctx.voice_file_id = message.voice.file_id
    ctx.text = ""
    await process(ctx, message.bot)


@private_router.message(F.text)
async def handle_text(message: Message) -> None:
    """Все текстовые сообщения — Brain сам классифицирует."""
    ctx = _build_context(message)
    await process(ctx, message.bot)


def _build_context(message: Message) -> BrainContext:
    """Создаёт BrainContext из aiogram Message."""
    reply_tg_id = None
    if message.reply_to_message and message.reply_to_message.from_user:
        reply_tg_id = message.reply_to_message.from_user.id

    return BrainContext(
        telegram_id=message.from_user.id,
        chat_id=message.chat.id,
        message_id=message.message_id,
        text=message.text or "",
        is_group=False,
        is_command=bool(message.text and message.text.startswith("/")),
        reply_to_user_telegram_id=reply_tg_id,
        tg_username=message.from_user.username,
        tg_first_name=message.from_user.first_name,
        tg_last_name=message.from_user.last_name,
        tg_is_premium=bool(getattr(message.from_user, "is_premium", False)),
        tg_locale=message.from_user.language_code,
    )

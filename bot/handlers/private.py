"""
bot/handlers/private.py — Обработка личных сообщений (DM).
Создаёт BrainContext и передаёт в brain.router.process().
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
# Только личные чаты
private_router.message.filter(F.chat.type == "private")


@private_router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    ctx = _build_context(message)
    ctx.set_intent(Intent.START, confidence="keyword")
    await process(ctx, message.bot)


@private_router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    ctx = _build_context(message)
    ctx.set_intent(Intent.HELP, confidence="keyword")
    await process(ctx, message.bot)


# Русскоязычные алиасы для справки
@private_router.message(Command("справка", "руководство", "помощь"))
async def cmd_help_ru(message: Message) -> None:
    import os
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    RAILWAY_URL = os.getenv("RAILWAY_PUBLIC_DOMAIN", "eassistantbotv2-production.up.railway.app")
    guide_url = f"https://{RAILWAY_URL}/guide"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="📖 Открыть руководство",
                web_app={"url": guide_url},
            )]
        ]
    )
    ctx = _build_context(message)
    ctx.set_intent(Intent.HELP, confidence="keyword")
    await process(ctx, message.bot)
    # Дополнительно шлём кнопку руководства
    await message.answer(
        "📚 Полное руководство доступно по кнопке ниже:",
        reply_markup=keyboard,
    )


@private_router.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    ctx = _build_context(message)
    ctx.set_intent(Intent.PROFILE_VIEW, confidence="keyword")
    await process(ctx, message.bot)


@private_router.message(Command("balance"))
async def cmd_balance(message: Message) -> None:
    ctx = _build_context(message)
    ctx.set_intent(Intent.BALANCE, confidence="keyword")
    await process(ctx, message.bot)


@private_router.message(Command("daily"))
async def cmd_daily(message: Message) -> None:
    ctx = _build_context(message)
    ctx.set_intent(Intent.DAILY_BONUS, confidence="keyword")
    await process(ctx, message.bot)


@private_router.message(Command("pet"))
async def cmd_pet(message: Message) -> None:
    ctx = _build_context(message)
    ctx.set_intent(Intent.PET_STATUS, confidence="keyword")
    await process(ctx, message.bot)


@private_router.message(Command("casino"))
async def cmd_casino(message: Message) -> None:
    ctx = _build_context(message)
    ctx.set_intent(Intent.CASINO_OPEN, confidence="keyword")
    await process(ctx, message.bot)


@private_router.message(Command("tasks"))
async def cmd_tasks(message: Message) -> None:
    ctx = _build_context(message)
    ctx.set_intent(Intent.TASK_LIST, confidence="keyword")
    await process(ctx, message.bot)


@private_router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    ctx = _build_context(message)
    ctx.set_intent(Intent.SETTINGS, confidence="keyword")
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
    """Все остальные текстовые сообщения."""
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


@private_router.message(Command("top"))
async def cmd_top(message: Message) -> None:
    from world.economy.leaderboard import get_leaderboard_text
    from api.auth.identity import get_user_by_telegram_id
    user = await get_user_by_telegram_id(message.from_user.id)
    lang = user.language if user else "ru"
    text = await get_leaderboard_text(limit=10, language=lang)
    await message.answer(text, parse_mode="Markdown")

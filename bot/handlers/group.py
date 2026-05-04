"""
bot/handlers/group.py — Обработка сообщений в группах и супергруппах.
Использует brain.group_router вместо brain.router.
"""

from __future__ import annotations
import logging

from aiogram import Router, F
from aiogram.types import Message, ChatMemberUpdated
from aiogram.filters import Command

from bot.brain.context import BrainContext
from bot.brain.intent import Intent
from bot.brain.group_router import process_group_message, handle_new_chat_member, handle_member_left

logger = logging.getLogger(__name__)

group_router = Router()
# Только групповые чаты
group_router.message.filter(F.chat.type.in_({"group", "supergroup"}))


@group_router.message(Command("warn"))
async def cmd_warn(message: Message) -> None:
    ctx = _build_context(message)
    ctx.set_intent(Intent.GROUP_WARN, confidence="keyword")
    await process_group_message(ctx, message.bot)


@group_router.message(Command("ban"))
async def cmd_ban(message: Message) -> None:
    ctx = _build_context(message)
    ctx.set_intent(Intent.GROUP_BAN, confidence="keyword")
    await process_group_message(ctx, message.bot)


@group_router.message(Command("mute"))
async def cmd_mute(message: Message) -> None:
    ctx = _build_context(message)
    ctx.set_intent(Intent.GROUP_MUTE, confidence="keyword")
    await process_group_message(ctx, message.bot)


@group_router.message(Command("kick"))
async def cmd_kick(message: Message) -> None:
    ctx = _build_context(message)
    ctx.set_intent(Intent.GROUP_KICK, confidence="keyword")
    await process_group_message(ctx, message.bot)


@group_router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    ctx = _build_context(message)
    ctx.set_intent(Intent.GROUP_STATS, confidence="keyword")
    await process_group_message(ctx, message.bot)


@group_router.message(Command("setwelcome"))
async def cmd_set_welcome(message: Message) -> None:
    ctx = _build_context(message)
    ctx.set_intent(Intent.GROUP_WELCOME, confidence="keyword")
    await process_group_message(ctx, message.bot)


@group_router.message(F.voice)
async def handle_voice(message: Message) -> None:
    ctx = _build_context(message)
    ctx.is_voice = True
    ctx.voice_file_id = message.voice.file_id
    ctx.text = ""
    await process_group_message(ctx, message.bot)


@group_router.message(F.text)
async def handle_text(message: Message) -> None:
    ctx = _build_context(message)
    await process_group_message(ctx, message.bot)


@group_router.chat_member()
async def handle_chat_member(update: ChatMemberUpdated) -> None:
    """Обрабатывает вступление/выход участников группы."""
    new_status = update.new_chat_member.status
    old_status = update.old_chat_member.status

    ctx = BrainContext(
        telegram_id=update.from_user.id,
        chat_id=update.chat.id,
        message_id=0,
        text="",
        is_group=True,
        extra={"chat_title": update.chat.title or ""},
    )

    if new_status in ("member", "administrator") and old_status in ("left", "kicked"):
        # Новый участник
        await handle_new_chat_member(ctx, update.bot, update.new_chat_member.user.id)
    elif new_status in ("left", "kicked") and old_status == "member":
        # Участник вышел
        await handle_member_left(ctx, update.bot)


def _build_context(message: Message) -> BrainContext:
    """Создаёт BrainContext из aiogram Message для группового чата."""
    reply_tg_id = None
    if message.reply_to_message and message.reply_to_message.from_user:
        reply_tg_id = message.reply_to_message.from_user.id

    return BrainContext(
        telegram_id=message.from_user.id,
        chat_id=message.chat.id,
        message_id=message.message_id,
        text=message.text or "",
        is_group=True,
        is_command=bool(message.text and message.text.startswith("/")),
        reply_to_user_telegram_id=reply_tg_id,
        extra={"chat_title": message.chat.title or ""},
    )

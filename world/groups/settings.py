"""
groups/settings.py — Настройки и приветствие групп.
"""

from __future__ import annotations
from infra.db.supabase import supabase_admin
from bot.brain.context import BrainContext
from api.auth.session import set_fsm_state, clear_fsm_state


async def get_group_settings_menu(group_id: str, language: str) -> tuple[str, object]:
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    res = supabase_admin.table("groups").select("*").eq("id", group_id).maybe_single().execute()
    group = res.data or {}

    text = (
        f"⚙️ *Настройки группы*\n\n"
        f"🌐 Язык: *{group.get('language', 'ru').upper()}*\n"
        f"⚠️ Порог варнов: *{group.get('warn_threshold', 3)}*\n"
        f"👋 Приветствие: {'✅' if group.get('welcome_message') else '❌'}"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👋 Установить приветствие", callback_data="groupset:welcome")],
        [InlineKeyboardButton(text="⚠️ Порог варнов", callback_data="groupset:warn_threshold")],
        [InlineKeyboardButton(text="🌐 Язык группы", callback_data="groupset:language")],
    ])
    return text, keyboard


async def set_welcome_message(ctx: BrainContext, bot) -> str:
    user_id = str(ctx.user.id)
    await set_fsm_state(user_id, "group:awaiting_welcome")
    return "👋 Введи текст приветственного сообщения.\n\nИспользуй {name} для имени пользователя."


async def save_welcome_message(group_id: str, text: str) -> None:
    supabase_admin.table("groups").update({"welcome_message": text}).eq("id", group_id).execute()

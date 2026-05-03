"""
brain/handlers/system.py — Системные команды: /start, /help, /settings.
"""

from brain.router import register
from brain.intent import Intent
from brain.context import BrainContext
from i18n import t


@register(Intent.START)
async def handle_start(ctx: BrainContext, bot) -> None:
    await bot.send_message(
        ctx.chat_id,
        t(ctx.language, "onboarding.intro"),
        parse_mode="Markdown",
    )


@register(Intent.HELP)
async def handle_help(ctx: BrainContext, bot) -> None:
    lang = ctx.language
    text = (
        f"*{ctx.assistant_name}* — список команд:\n\n"
        f"🤖 /ai — AI-чат\n"
        f"💰 /balance — баланс Ecoins\n"
        f"🎁 /daily — ежедневный бонус\n"
        f"🐾 /pet — мой питомец\n"
        f"🎰 /casino — казино\n"
        f"🎵 /music — найти музыку\n"
        f"🌤 /weather — погода\n"
        f"📚 /book — найти книгу\n"
        f"📝 /tasks — мои задачи\n"
        f"👤 /profile — мой профиль\n"
        f"⚙️ /settings — настройки\n"
    )
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.SETTINGS)
async def handle_settings(ctx: BrainContext, bot) -> None:
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Язык / Language", callback_data="settings:language")],
        [InlineKeyboardButton(text="✏️ Имя ассистента", callback_data="settings:assistant_name")],
        [InlineKeyboardButton(text="👤 Редактировать профиль", callback_data="settings:profile")],
    ])
    await bot.send_message(
        ctx.chat_id,
        "⚙️ *Настройки*\n\nЧто хочешь изменить?",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

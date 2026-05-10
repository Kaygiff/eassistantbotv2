"""
brain/handlers/system.py — Системные команды: /start, /help, /settings.
"""
import os

from bot.brain.router import register
from bot.brain.intent import Intent
from bot.brain.context import BrainContext
from core.i18n import t

_RAILWAY_URL = os.getenv("RAILWAY_PUBLIC_DOMAIN", "eassistantbotv2-production.up.railway.app")
_GUIDE_URL = f"https://{_RAILWAY_URL}/guide"


def _guide_keyboard():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="📖 Открыть руководство",
                web_app={"url": _GUIDE_URL},
            )]
        ]
    )


@register(Intent.START)
async def handle_start(ctx: BrainContext, bot) -> None:
    await bot.send_message(
        ctx.chat_id,
        t(ctx.language, "onboarding.intro"),
        parse_mode="Markdown",
    )


@register(Intent.HELP)
async def handle_help(ctx: BrainContext, bot) -> None:
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
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown", reply_markup=_guide_keyboard())


@register(Intent.WHO_MADE_YOU)
async def handle_who_made_you(ctx: BrainContext, bot) -> None:
    await bot.send_message(
        ctx.chat_id,
        f"🛠 Меня создал *Кай Гиффенс*\\nTelegram: @kxygxf",
        parse_mode="Markdown",
    )


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

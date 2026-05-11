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


def _guide_keyboard(is_group: bool = False):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    if is_group:
        # web_app не поддерживается в группах — используем обычную ссылку
        button = InlineKeyboardButton(text="📖 Открыть руководство", url=f"https://{_RAILWAY_URL}/guide")
    else:
        button = InlineKeyboardButton(text="📖 Открыть руководство", web_app={"url": _GUIDE_URL})
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


@register(Intent.START)
async def handle_start(ctx: BrainContext, bot) -> None:
    await bot.send_message(
        ctx.chat_id,
        t(ctx.language, "onboarding.intro"),
        parse_mode="Markdown",
    )


@register(Intent.HELP)
async def handle_help(ctx: BrainContext, bot) -> None:
    await bot.send_message(
        ctx.chat_id,
        HELP_TEXT,
        parse_mode="Markdown",
        reply_markup=_guide_keyboard(is_group=ctx.is_group),
    )


@register(Intent.WHO_MADE_YOU)
async def handle_who_made_you(ctx: BrainContext, bot) -> None:
    await bot.send_message(
        ctx.chat_id,
        f"🛠 Меня создал *Кай Гиффенс*\nTelegram: @kxygxf",
        parse_mode="Markdown",
    )


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

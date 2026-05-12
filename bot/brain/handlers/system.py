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




def _guide_keyboard(lang: str = "ru", is_group: bool = False):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    label = t(lang, "help.open_guide")
    if is_group:
        button = InlineKeyboardButton(text=label, url=f"https://{_RAILWAY_URL}/guide")
    else:
        button = InlineKeyboardButton(text=label, web_app={"url": _GUIDE_URL})
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
        t(ctx.language, "help.text"),
        parse_mode="Markdown",
        reply_markup=_guide_keyboard(lang=ctx.language, is_group=ctx.is_group),
    )


@register(Intent.WHO_MADE_YOU)
async def handle_who_made_you(ctx: BrainContext, bot) -> None:
    await bot.send_message(
        ctx.chat_id,
        t(ctx.language, "who_made_you.text"),
        parse_mode="Markdown",
    )


@register(Intent.SETTINGS)
async def handle_settings(ctx: BrainContext, bot) -> None:
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    lang = ctx.language
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "settings.language"), callback_data="settings:language")],
        [InlineKeyboardButton(text=t(lang, "settings.assistant_name"), callback_data="settings:assistant_name")],
        [InlineKeyboardButton(text=t(lang, "settings.edit_profile"), callback_data="settings:profile")],
    ])
    await bot.send_message(
        ctx.chat_id,
        t(lang, "settings.title"),
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

"""
brain/handlers/profile.py — Просмотр и редактирование профиля.
"""

from brain.router import register
from brain.intent import Intent
from brain.context import BrainContext


@register(Intent.PROFILE_VIEW)
async def handle_profile_view(ctx: BrainContext, bot) -> None:
    user = ctx.user
    lines = [
        f"👤 *Профиль*\n",
        f"🏷 Имя ассистента: *{user.assistant_name}*",
    ]
    if user.nickname:
        lines.append(f"✏️ Никнейм: *{user.nickname}*")
    if user.bio:
        lines.append(f"📝 О себе: {user.bio}")
    if user.birthday:
        lines.append(f"🎂 День рождения: {user.birthday.strftime('%d.%m.%Y')}")
    lines.append(f"🌐 Язык: {user.language.upper()}")

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data="profile:edit")],
    ])
    await bot.send_message(
        ctx.chat_id,
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


@register(Intent.PROFILE_EDIT)
async def handle_profile_edit(ctx: BrainContext, bot) -> None:
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Никнейм", callback_data="profile:edit:nickname")],
        [InlineKeyboardButton(text="📝 О себе", callback_data="profile:edit:bio")],
        [InlineKeyboardButton(text="🎂 День рождения", callback_data="profile:edit:birthday")],
        [InlineKeyboardButton(text="🌐 Язык", callback_data="profile:edit:language")],
        [InlineKeyboardButton(text="🤖 Имя ассистента", callback_data="profile:edit:assistant_name")],
    ])
    await bot.send_message(
        ctx.chat_id,
        "✏️ *Редактирование профиля*\n\nЧто хочешь изменить?",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

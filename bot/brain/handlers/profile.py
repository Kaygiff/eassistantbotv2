"""
brain/handlers/profile.py — Просмотр и редактирование профиля.
"""

from bot.brain.router import register
from bot.brain.intent import Intent
from bot.brain.context import BrainContext


@register(Intent.PROFILE_VIEW)
async def handle_profile_view(ctx: BrainContext, bot) -> None:
    from world.economy.wallet import get_balance
    from world.virtual_world.pets.service import get_pet_profile_line
    from world.virtual_world.relationships.service import get_relationship_profile_line
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    user = ctx.user
    balance = await get_balance(ctx.user_id)
    pet_line = await get_pet_profile_line(ctx.user_id)
    rel_line = await get_relationship_profile_line(ctx.user_id)

    lines = ["👤 *Профиль*\n"]
    if user.nickname:
        lines.append(f"✏️ *{user.nickname}*")
    lines.append(f"🏷 Ассистент: *{user.assistant_name}*")
    if user.bio:
        lines.append(f"📝 {user.bio}")
    if user.birthday:
        lines.append(f"🎂 {user.birthday.strftime('%d.%m.%Y')}")
    lines.append(f"🌐 {user.language.upper()}")
    lines.append(f"💰 *{balance} Ecoins*")
    lines.append(f"\n{rel_line}" if rel_line else "\n💔 Свободен(а)")
    if pet_line:
        lines.append(f"🐾 {pet_line}")

    pet_btn = (
        InlineKeyboardButton(text="🥚 Создать питомца", callback_data="pet:new")
        if not pet_line else
        InlineKeyboardButton(text="🐾 Питомец", callback_data="pet:menu")
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Редактировать", callback_data="profile:edit"),
            InlineKeyboardButton(text="💰 Ecoins", callback_data="ecoins:menu"),
        ],
        [pet_btn, InlineKeyboardButton(text="🎰 Казино", callback_data="profile:casino")],
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

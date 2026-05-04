"""
brain/handlers/pet.py — Питомец-тамагочи.
"""

from bot.brain.router import register
from bot.brain.intent import Intent
from bot.brain.context import BrainContext
from core.i18n import t


@register(Intent.PET_STATUS)
async def handle_pet_status(ctx: BrainContext, bot) -> None:
    from world.virtual_world.pets.service import get_pet_status
    text = await get_pet_status(ctx.user_id, ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.PET_FEED)
async def handle_pet_feed(ctx: BrainContext, bot) -> None:
    from world.virtual_world.pets.service import feed_pet
    text = await feed_pet(ctx.user_id, ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.PET_PLAY)
async def handle_pet_play(ctx: BrainContext, bot) -> None:
    from world.virtual_world.pets.service import play_with_pet
    text = await play_with_pet(ctx.user_id, ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.PET_HEAL)
async def handle_pet_heal(ctx: BrainContext, bot) -> None:
    from world.virtual_world.pets.service import heal_pet
    text = await heal_pet(ctx.user_id, ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.PET_NEW)
async def handle_pet_new(ctx: BrainContext, bot) -> None:
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🐱 Кот", callback_data="pet:new:cat"),
            InlineKeyboardButton(text="🐶 Пёс", callback_data="pet:new:dog"),
        ],
        [
            InlineKeyboardButton(text="🐰 Кролик", callback_data="pet:new:rabbit"),
            InlineKeyboardButton(text="🐹 Хомяк", callback_data="pet:new:hamster"),
        ],
        [
            InlineKeyboardButton(text="🦊 Лиса", callback_data="pet:new:fox"),
            InlineKeyboardButton(text="🐉 Дракон", callback_data="pet:new:dragon"),
        ],
    ])
    await bot.send_message(
        ctx.chat_id,
        t(ctx.language, "pets.new_pet"),
        reply_markup=keyboard,
    )

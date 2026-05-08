"""
brain/handlers/pets.py — Хэндлеры питомцев.

Команды:
  питомец               → главное меню
  создать питомца       → выбор вида (inline)
  покормить питомца     → еда + XP
  поиграть с питомцем   → энергия + XP
  лечить питомца        → лечение (50 Ecoins) + XP
  сменить имя питомцу   → FSM переименования
"""

from bot.brain.router import register
from bot.brain.intent import Intent
from bot.brain.context import BrainContext


@register(Intent.PET_MENU)
async def handle_pet_menu(ctx: BrainContext, bot) -> None:
    from world.virtual_world.pets.service import open_pet_menu
    await open_pet_menu(str(ctx.user.id), ctx.language, bot, ctx.chat_id)


@register(Intent.PET_STATUS)
async def handle_pet_status(ctx: BrainContext, bot) -> None:
    from world.virtual_world.pets.service import get_pet_status
    text = await get_pet_status(str(ctx.user.id), ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.PET_NEW)
async def handle_pet_new(ctx: BrainContext, bot) -> None:
    from world.virtual_world.pets.service import open_pet_creation
    await open_pet_creation(str(ctx.user.id), bot, ctx.chat_id)


@register(Intent.PET_FEED)
async def handle_pet_feed(ctx: BrainContext, bot) -> None:
    from world.virtual_world.pets.service import feed_pet
    text = await feed_pet(str(ctx.user.id), ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.PET_PLAY)
async def handle_pet_play(ctx: BrainContext, bot) -> None:
    from world.virtual_world.pets.service import play_with_pet
    text = await play_with_pet(str(ctx.user.id), ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.PET_HEAL)
async def handle_pet_heal(ctx: BrainContext, bot) -> None:
    from world.virtual_world.pets.service import heal_pet
    text = await heal_pet(str(ctx.user.id), ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.PET_RENAME)
async def handle_pet_rename(ctx: BrainContext, bot) -> None:
    from world.virtual_world.pets.service import start_pet_rename
    await start_pet_rename(str(ctx.user.id), bot, ctx.chat_id)

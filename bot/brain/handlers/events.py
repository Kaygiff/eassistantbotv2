"""
brain/handlers/events.py — События.
"""

from bot.brain.router import register
from bot.brain.intent import Intent
from bot.brain.context import BrainContext


@register(Intent.EVENT_CREATE)
async def handle_event_create(ctx: BrainContext, bot) -> None:
    from world.virtual_world.events.service import start_event_creation
    await start_event_creation(ctx, bot)


@register(Intent.EVENT_LIST)
async def handle_event_list(ctx: BrainContext, bot) -> None:
    from world.virtual_world.events.service import get_events_list
    text = await get_events_list(ctx.chat_id, ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.EVENT_JOIN)
async def handle_event_join(ctx: BrainContext, bot) -> None:
    from world.virtual_world.events.service import join_event
    text = await join_event(ctx, bot)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")

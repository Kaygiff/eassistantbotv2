"""
brain/handlers/family.py — Семейные роли.
"""

from bot.brain.router import register
from bot.brain.intent import Intent
from bot.brain.context import BrainContext


@register(Intent.FAMILY_ADD)
async def handle_family_add(ctx: BrainContext, bot) -> None:
    from world.virtual_world.family.service import add_family_member
    text = await add_family_member(ctx, bot)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.FAMILY_VIEW)
async def handle_family_view(ctx: BrainContext, bot) -> None:
    from world.virtual_world.family.service import get_family_tree
    text = await get_family_tree(ctx.user_id, ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")

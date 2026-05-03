"""
brain/handlers/actions.py — Действия между пользователями.
"""

import re
from brain.router import register
from brain.intent import Intent
from brain.context import BrainContext


@register(Intent.ACTION_DO)
async def handle_action(ctx: BrainContext, bot) -> None:
    from virtual_world.actions.service import perform_action
    text = await perform_action(ctx, bot)
    if text:
        await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.BLACKLIST_ADD)
async def handle_blacklist_add(ctx: BrainContext, bot) -> None:
    match = re.search(r"@(\w+)", ctx.text)
    if not match:
        await bot.send_message(ctx.chat_id, "🚫 Укажи пользователя: *заблокировать @username*", parse_mode="Markdown")
        return
    from virtual_world.blacklist.service import add_to_blacklist
    text = await add_to_blacklist(str(ctx.user.id), match.group(1), ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.BLACKLIST_REMOVE)
async def handle_blacklist_remove(ctx: BrainContext, bot) -> None:
    match = re.search(r"@(\w+)", ctx.text)
    if not match:
        await bot.send_message(ctx.chat_id, "✅ Укажи пользователя: *разблокировать @username*", parse_mode="Markdown")
        return
    from virtual_world.blacklist.service import remove_from_blacklist
    text = await remove_from_blacklist(str(ctx.user.id), match.group(1), ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")

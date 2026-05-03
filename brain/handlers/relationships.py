"""
brain/handlers/relationships.py — Отношения и браки.
"""

from brain.router import register
from brain.intent import Intent
from brain.context import BrainContext
from i18n import t


async def _get_target_user(ctx: BrainContext, bot):
    """Извлекает целевого пользователя из reply или @username."""
    import re
    from auth.identity import get_user_by_telegram_id
    from db.supabase import supabase_admin

    # Из @username в тексте
    match = re.search(r"@(\w+)", ctx.text)
    if match:
        username = match.group(1)
        res = supabase_admin.table("users").select("*").eq("username", username).maybe_single().execute()
        if res.data:
            from models.user import User
            return User(**res.data)

    # Из reply_to
    if ctx.reply_to_user_telegram_id:
        return await get_user_by_telegram_id(ctx.reply_to_user_telegram_id)

    return None


@register(Intent.RELATIONSHIP_PROPOSE)
async def handle_propose_dating(ctx: BrainContext, bot) -> None:
    target = await _get_target_user(ctx, bot)
    if not target:
        await bot.send_message(ctx.chat_id, "👥 Укажи пользователя через @username или ответь на его сообщение.")
        return
    from virtual_world.relationships.service import propose_dating
    text = await propose_dating(ctx.user, target, ctx.language, bot)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.RELATIONSHIP_STATUS)
async def handle_relationship_status(ctx: BrainContext, bot) -> None:
    from virtual_world.relationships.service import get_relationship_status
    text = await get_relationship_status(ctx.user_id, ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.RELATIONSHIP_BREAKUP)
async def handle_breakup(ctx: BrainContext, bot) -> None:
    from virtual_world.relationships.service import breakup
    text = await breakup(ctx.user_id, ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.MARRIAGE_PROPOSE)
async def handle_propose_marriage(ctx: BrainContext, bot) -> None:
    target = await _get_target_user(ctx, bot)
    if not target:
        await bot.send_message(ctx.chat_id, "💍 Укажи пользователя через @username или ответь на его сообщение.")
        return
    from virtual_world.relationships.service import propose_marriage
    text = await propose_marriage(ctx.user, target, ctx.language, bot)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.MARRIAGE_DIVORCE)
async def handle_divorce(ctx: BrainContext, bot) -> None:
    from virtual_world.relationships.service import divorce
    text = await divorce(ctx.user_id, ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")

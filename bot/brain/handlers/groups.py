"""
brain/handlers/groups.py — Модерация и управление группами.
"""

from bot.brain.router import register
from bot.brain.intent import Intent
from bot.brain.context import BrainContext
from core.i18n import t


async def _require_moderator(ctx: BrainContext, bot) -> bool:
    """Проверяет права модератора. Возвращает False и отправляет ошибку если нет прав."""
    if not ctx.group_id:
        return False
    from infra.safety.group_moderation import can_moderate
    if not await can_moderate(ctx.group_id, ctx.user_id):
        await bot.send_message(ctx.chat_id, t(ctx.language, "common.access_denied"))
        return False
    return True


@register(Intent.GROUP_WARN)
async def handle_warn(ctx: BrainContext, bot) -> None:
    if not await _require_moderator(ctx, bot):
        return
    from world.groups.moderation import warn_user_in_group
    text = await warn_user_in_group(ctx, bot)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.GROUP_BAN)
async def handle_ban(ctx: BrainContext, bot) -> None:
    if not await _require_moderator(ctx, bot):
        return
    from world.groups.moderation import ban_user_in_group
    text = await ban_user_in_group(ctx, bot)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.GROUP_MUTE)
async def handle_mute(ctx: BrainContext, bot) -> None:
    if not await _require_moderator(ctx, bot):
        return
    from world.groups.moderation import mute_user_in_group
    text = await mute_user_in_group(ctx, bot)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.GROUP_KICK)
async def handle_kick(ctx: BrainContext, bot) -> None:
    if not await _require_moderator(ctx, bot):
        return
    from world.groups.moderation import kick_user_from_group
    text = await kick_user_from_group(ctx, bot)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.GROUP_SETTINGS)
async def handle_group_settings(ctx: BrainContext, bot) -> None:
    if not await _require_moderator(ctx, bot):
        return
    from world.groups.settings import get_group_settings_menu
    text, keyboard = await get_group_settings_menu(ctx.group_id, ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown", reply_markup=keyboard)


@register(Intent.GROUP_STATS)
async def handle_group_stats(ctx: BrainContext, bot) -> None:
    from world.groups.stats import get_group_stats
    text = await get_group_stats(ctx.group_id, ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.GROUP_WELCOME)
async def handle_group_welcome(ctx: BrainContext, bot) -> None:
    if not await _require_moderator(ctx, bot):
        return
    from world.groups.settings import set_welcome_message
    text = await set_welcome_message(ctx, bot)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")

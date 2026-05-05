"""
brain/handlers/groups.py — Модерация и управление группами.
"""

from bot.brain.router import register
from bot.brain.intent import Intent
from bot.brain.context import BrainContext


async def _send(ctx, bot, text: str) -> None:
    if text:
        await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.GROUP_WARN)
async def handle_warn(ctx: BrainContext, bot) -> None:
    from world.groups.moderation import warn_user_in_group
    await _send(ctx, bot, await warn_user_in_group(ctx, bot))


@register(Intent.GROUP_UNWARN)
async def handle_unwarn(ctx: BrainContext, bot) -> None:
    from world.groups.moderation import unwarn_user_in_group
    await _send(ctx, bot, await unwarn_user_in_group(ctx, bot))


@register(Intent.GROUP_WARNS)
async def handle_warns(ctx: BrainContext, bot) -> None:
    from world.groups.moderation import warns_user_in_group
    await _send(ctx, bot, await warns_user_in_group(ctx, bot))


@register(Intent.GROUP_BAN)
async def handle_ban(ctx: BrainContext, bot) -> None:
    from world.groups.moderation import ban_user_in_group
    await _send(ctx, bot, await ban_user_in_group(ctx, bot))


@register(Intent.GROUP_UNBAN)
async def handle_unban(ctx: BrainContext, bot) -> None:
    from world.groups.moderation import unban_user_in_group
    await _send(ctx, bot, await unban_user_in_group(ctx, bot))


@register(Intent.GROUP_MUTE)
async def handle_mute(ctx: BrainContext, bot) -> None:
    from world.groups.moderation import mute_user_in_group
    await _send(ctx, bot, await mute_user_in_group(ctx, bot))


@register(Intent.GROUP_UNMUTE)
async def handle_unmute(ctx: BrainContext, bot) -> None:
    from world.groups.moderation import unmute_user_in_group
    await _send(ctx, bot, await unmute_user_in_group(ctx, bot))


@register(Intent.GROUP_KICK)
async def handle_kick(ctx: BrainContext, bot) -> None:
    from world.groups.moderation import kick_user_from_group
    await _send(ctx, bot, await kick_user_from_group(ctx, bot))


@register(Intent.GROUP_PROMOTE)
async def handle_promote(ctx: BrainContext, bot) -> None:
    from world.groups.moderation import promote_user_in_group
    await _send(ctx, bot, await promote_user_in_group(ctx, bot))


@register(Intent.GROUP_DEMOTE)
async def handle_demote(ctx: BrainContext, bot) -> None:
    from world.groups.moderation import demote_user_in_group
    await _send(ctx, bot, await demote_user_in_group(ctx, bot))


@register(Intent.GROUP_SETTINGS)
async def handle_group_settings(ctx: BrainContext, bot) -> None:
    from infra.safety.group_moderation import can_moderate
    if not ctx.group_id or not await can_moderate(ctx.group_id, ctx.user_id):
        await bot.send_message(ctx.chat_id, "❌ Нет прав.")
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
    from infra.safety.group_moderation import can_moderate
    if not ctx.group_id or not await can_moderate(ctx.group_id, ctx.user_id):
        await bot.send_message(ctx.chat_id, "❌ Нет прав.")
        return
    from world.groups.settings import set_welcome_message
    text = await set_welcome_message(ctx, bot)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")

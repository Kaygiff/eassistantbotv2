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


@register(Intent.GROUP_CLEARWARNS)
async def handle_clearwarns(ctx: BrainContext, bot) -> None:
    from world.groups.moderation import clearwarns_user_in_group
    await _send(ctx, bot, await clearwarns_user_in_group(ctx, bot))


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


@register(Intent.GROUP_ROLE)
async def handle_my_role(ctx: BrainContext, bot) -> None:
    if not ctx.group_id:
        await bot.send_message(ctx.chat_id, "❌ Эта команда работает только в группе.")
        return
    from infra.safety.group_moderation import get_group_member_role
    role = await get_group_member_role(ctx.group_id, ctx.user_id)
    role_names = {
        "owner":     "👑 Владелец",
        "co_owner":  "🌟 Со-владелец",
        "admin":     "🛡 Администратор",
        "moderator": "⚔️ Модератор",
        "vip":       "💎 VIP",
        "user":      "👤 Участник",
    }
    name = ctx.user.first_name or "Пользователь"
    role_label = role_names.get(role, "👤 Участник")
    await bot.send_message(
        ctx.chat_id,
        f"👤 *{name}*, твоя роль в этой группе: {role_label}",
        parse_mode="Markdown",
    )


@register(Intent.GROUP_ADMINS)
async def handle_group_admins(ctx: BrainContext, bot) -> None:
    if not ctx.group_id:
        await bot.send_message(ctx.chat_id, "❌ Эта команда работает только в группе.")
        return

    from infra.safety.group_moderation import sync_group_owner
    await sync_group_owner(ctx.group_id, bot, ctx.chat_id)

    from infra.db.supabase import get_supabase_admin
    res = (
        get_supabase_admin()
        .table("group_members")
        .select("role, users(first_name, username)")
        .eq("group_id", ctx.group_id)
        .in_("role", ["owner", "co_owner", "admin", "moderator"])
        .execute()
    )
    if not res or not res.data:
        await bot.send_message(ctx.chat_id, "👥 В группе нет назначенных администраторов.")
        return
    role_names = {
        "owner":     "👑 Владелец",
        "co_owner":  "🌟 Со-владелец",
        "admin":     "🛡 Администратор",
        "moderator": "⚔️ Модератор",
    }
    lines = ["👥 *Администраторы группы:*\n"]
    for m in res.data:
        user = m.get("users") or {}
        first_name = user.get("first_name")
        username = user.get("username")
        name = first_name or (f"@{username}" if username else "—")
        role_label = role_names.get(m["role"], m["role"])
        lines.append(f"{role_label} — {name}")
    await bot.send_message(ctx.chat_id, "\n".join(lines), parse_mode="Markdown")

"""
bot/handlers/group.py — Обработка сообщений в групповых чатах.
"""

from __future__ import annotations
import logging

from aiogram import Router, F
from aiogram.types import Message

from bot.brain.router import register
from bot.brain.intent import Intent
from bot.brain.context import BrainContext

logger = logging.getLogger(__name__)

group_router = Router()
group_router.message.filter(F.chat.type.in_({"group", "supergroup"}))


@group_router.message()
async def handle_group_message(message: Message) -> None:
    from api.auth.identity import get_or_create_user
    from bot.brain.group_router import process_group_message

    user, _ = await get_or_create_user(
        telegram_id=message.from_user.id,
        first_name=message.from_user.first_name or "",
        username=message.from_user.username,
    )

    ctx = BrainContext(
        telegram_id=message.from_user.id,
        chat_id=message.chat.id,
        message_id=message.message_id,
        text=message.text or "",
        is_group=True,
    )
    ctx.user = user
    ctx.language = user.language if user else "ru"
    ctx.extra["chat_title"] = message.chat.title or ""

    # Заполняем reply_to_user_telegram_id + имя если это ответ на сообщение
    if message.reply_to_message and message.reply_to_message.from_user:
        reply_user = message.reply_to_message.from_user
        ctx.reply_to_user_telegram_id = reply_user.id
        ctx.extra["reply_to_user_name"] = (
            reply_user.first_name
            or (f"@{reply_user.username}" if reply_user.username else None)
            or f"id:{reply_user.id}"
        )

    await process_group_message(ctx, message.bot)


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

    # Пересинхронизируем owner с Telegram — чтобы всегда показывал правильного
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
        # Защита от None: first_name или @username или заглушка
        first_name = user.get("first_name")
        username = user.get("username")
        name = first_name or (f"@{username}" if username else "—")
        role_label = role_names.get(m["role"], m["role"])
        lines.append(f"{role_label} — {name}")
    await bot.send_message(ctx.chat_id, "\n".join(lines), parse_mode="Markdown")

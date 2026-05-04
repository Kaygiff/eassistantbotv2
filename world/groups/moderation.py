"""
groups/moderation.py — Команды модерации в группах (варн, бан, мут, кик).
"""

from __future__ import annotations
import re
import logging
from datetime import datetime, timezone, timedelta

from bot.brain.context import BrainContext
from infra.safety.group_moderation import warn_user, can_moderate
from core.i18n import t
from infra.notifications.sender import notify_user

logger = logging.getLogger(__name__)


async def _get_target(ctx: BrainContext) -> tuple[str | None, str | None]:
    """Извлекает целевого пользователя из reply или @username."""
    from api.auth.identity import get_user_by_telegram_id
    from infra.db.supabase import supabase_admin

    if ctx.reply_to_user_telegram_id:
        user = await get_user_by_telegram_id(ctx.reply_to_user_telegram_id)
        if user:
            return str(user.id), user.first_name or f"@{user.username}"

    match = re.search(r"@(\w+)", ctx.text)
    if match:
        res = supabase_admin.table("users").select("id, first_name, username").eq("username", match.group(1)).maybe_single().execute()
        if res.data:
            name = res.data.get("first_name") or f"@{res.data.get('username')}"
            return res.data["id"], name

    return None, None


def _extract_reason(text: str) -> str | None:
    match = re.search(r"причина[:\s]+(.+)", text, re.IGNORECASE)
    return match.group(1).strip() if match else None


async def warn_user_in_group(ctx: BrainContext, bot) -> str:
    if not ctx.group_id:
        return t(ctx.language, "common.error")

    target_id, target_name = await _get_target(ctx)
    if not target_id:
        return "👥 Укажи пользователя через @username или ответь на его сообщение."

    reason = _extract_reason(ctx.text)
    count, threshold = await warn_user(ctx.group_id, target_id, str(ctx.user.id), reason)

    if count >= threshold:
        # Автобан
        from infra.safety.user_ban import ban_user
        await ban_user(target_id, reason=f"Автобан: {count} варнов", banned_by=str(ctx.user.id))
        return t(ctx.language, "moderation.auto_banned", username=target_name, max=threshold)

    return t(ctx.language, "moderation.warned", username=target_name, count=count, max=threshold)


async def ban_user_in_group(ctx: BrainContext, bot) -> str:
    target_id, target_name = await _get_target(ctx)
    if not target_id:
        return "👥 Укажи пользователя."

    reason = _extract_reason(ctx.text)
    from infra.safety.user_ban import ban_user
    await ban_user(target_id, reason=reason, banned_by=str(ctx.user.id))

    try:
        from infra.db.supabase import supabase_admin
        user_res = supabase_admin.table("users").select("telegram_id").eq("id", target_id).maybe_single().execute()
        if user_res.data:
            await bot.ban_chat_member(ctx.chat_id, user_res.data["telegram_id"])
    except Exception as e:
        logger.warning(f"[Moderation] Telegram ban failed: {e}")

    return t(ctx.language, "moderation.banned", username=target_name)


async def mute_user_in_group(ctx: BrainContext, bot) -> str:
    target_id, target_name = await _get_target(ctx)
    if not target_id:
        return "👥 Укажи пользователя."

    # Мут на 1 час по умолчанию
    until = datetime.now(timezone.utc) + timedelta(hours=1)
    from aiogram.types import ChatPermissions

    try:
        from infra.db.supabase import supabase_admin
        user_res = supabase_admin.table("users").select("telegram_id").eq("id", target_id).maybe_single().execute()
        if user_res.data:
            await bot.restrict_chat_member(
                ctx.chat_id,
                user_res.data["telegram_id"],
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until,
            )
    except Exception as e:
        logger.warning(f"[Moderation] Telegram mute failed: {e}")

    return t(ctx.language, "moderation.muted", username=target_name, duration="1 час")


async def kick_user_from_group(ctx: BrainContext, bot) -> str:
    target_id, target_name = await _get_target(ctx)
    if not target_id:
        return "👥 Укажи пользователя."

    try:
        from infra.db.supabase import supabase_admin
        user_res = supabase_admin.table("users").select("telegram_id").eq("id", target_id).maybe_single().execute()
        if user_res.data:
            await bot.ban_chat_member(ctx.chat_id, user_res.data["telegram_id"])
            await bot.unban_chat_member(ctx.chat_id, user_res.data["telegram_id"])
    except Exception as e:
        logger.warning(f"[Moderation] Telegram kick failed: {e}")

    return t(ctx.language, "moderation.kicked", username=target_name)

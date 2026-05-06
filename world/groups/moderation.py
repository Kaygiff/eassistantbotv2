"""
groups/moderation.py — Команды модерации в группах.
"""

from __future__ import annotations
import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from bot.brain.context import BrainContext
from infra.safety.group_moderation import (
    warn_user, unwarn_user, clear_warns, get_warn_count,
    ban_from_group, unban_from_group,
    mute_in_group, unmute_in_group,
    promote_member, demote_member,
    get_group_member_role,
    CAN_BAN, CAN_MUTE, CAN_KICK, CAN_WARN, CAN_PROMOTE,
    ROLE_HIERARCHY,
)
from core.i18n import t

logger = logging.getLogger(__name__)

ROLE_NAMES = {
    "owner":    "👑 Владелец",
    "co_owner": "🌟 Со-владелец",
    "admin":    "🛡 Администратор",
    "moderator": "⚔️ Модератор",
    "vip":      "💎 VIP",
    "user":     "👤 Участник",
}

_TIME_RE = re.compile(
    r"(\d+)\s*(м|мин|минут|ч|час|часов|д|день|дней|дня|н|нед|неделю|недел|w|d|h|m)",
    re.IGNORECASE | re.UNICODE,
)
_TIME_MAP = {
    "м": 60, "мин": 60, "минут": 60, "m": 60,
    "ч": 3600, "час": 3600, "часов": 3600, "h": 3600,
    "д": 86400, "день": 86400, "дней": 86400, "дня": 86400, "d": 86400,
    "н": 604800, "нед": 604800, "неделю": 604800, "недел": 604800, "w": 604800,
}

def _parse_duration(text: str) -> Optional[timedelta]:
    match = _TIME_RE.search(text)
    if not match:
        return None
    amount = int(match.group(1))
    unit = match.group(2).lower()
    seconds = _TIME_MAP.get(unit)
    return timedelta(seconds=amount * seconds) if seconds else None

def _format_duration(td: timedelta) -> str:
    total = int(td.total_seconds())
    if total >= 86400:
        return f"{total // 86400} д."
    if total >= 3600:
        return f"{total // 3600} ч."
    return f"{total // 60} мин."

async def _get_target(ctx: BrainContext, bot=None) -> tuple[Optional[str], Optional[str], Optional[int]]:
    from api.auth.identity import get_user_by_telegram_id
    if ctx.reply_to_user_telegram_id:
        user = await get_user_by_telegram_id(ctx.reply_to_user_telegram_id)
        if user:
            name = user.first_name or (f"@{user.username}" if user.username else f"id:{user.telegram_id}")
            return str(user.id), name, user.telegram_id
        tg_name = ctx.extra.get("reply_to_user_name") or f"id:{ctx.reply_to_user_telegram_id}"
        return None, tg_name, ctx.reply_to_user_telegram_id
    return None, None, None

def _extract_reason(text: str) -> Optional[str]:
    match = re.search(r"причина[:\s]+(.+)", text, re.IGNORECASE)
    return match.group(1).strip() if match else None

async def _check_permission(ctx: BrainContext, allowed_set: set, bot) -> bool:
    if not ctx.group_id:
        await bot.send_message(ctx.chat_id, "❌ Группа не найдена.")
        return False
    role = await get_group_member_role(ctx.group_id, ctx.user_id)
    if role not in allowed_set:
        await bot.send_message(ctx.chat_id, t(ctx.language, "common.access_denied"))
        return False
    return True

async def _get_warn_threshold(group_id: str) -> int:
    from infra.db.supabase import get_supabase_admin
    res = get_supabase_admin().table("groups").select("warn_threshold").eq("id", group_id).maybe_single().execute()
    return res.data["warn_threshold"] if res.data else 3

async def _get_telegram_id(user_uuid: str) -> Optional[int]:
    from infra.db.supabase import get_supabase_admin
    res = get_supabase_admin().table("users").select("telegram_id").eq("id", user_uuid).maybe_single().execute()
    return res.data["telegram_id"] if res.data else None

# ВАРН
async def warn_user_in_group(ctx: BrainContext, bot) -> str:
    if not await _check_permission(ctx, CAN_WARN, bot):
        return ""
    target_id, target_name, target_tg_id = await _get_target(ctx, bot)
    if not target_id and not target_tg_id:
        return "👥 Укажи пользователя через реплей на его сообщение."
    if not target_id:
        return f"⚠️ *{target_name}* не зарегистрирован в боте, варн не может быть сохранён."
    reason = _extract_reason(ctx.text)
    count, threshold = await warn_user(ctx.group_id, target_id, ctx.user_id, reason)
    if count >= threshold:
        await ban_from_group(ctx.group_id, target_id, ctx.user_id, reason=f"Автобан: {count} варнов")
        try:
            tg_res = await _get_telegram_id(target_id)
            if tg_res:
                await bot.ban_chat_member(ctx.chat_id, tg_res)
        except Exception as e:
            logger.warning(f"[Moderation] Autoban telegram failed: {e}")
        return t(ctx.language, "moderation.auto_banned", username=target_name, max=threshold)
    reason_text = f"\nПричина: _{reason}_" if reason else ""
    return f"⚠️ *{target_name}* получает предупреждение [{count}/{threshold}]{reason_text}"

# СНЯТЬ ВАРН
async def unwarn_user_in_group(ctx: BrainContext, bot) -> str:
    if not await _check_permission(ctx, CAN_WARN, bot):
        return ""
    target_id, target_name, target_tg_id = await _get_target(ctx, bot)
    if not target_id and not target_tg_id:
        return "👥 Укажи пользователя."
    if not target_id:
        return f"⚠️ *{target_name}* не зарегистрирован в боте."
    remaining = await unwarn_user(ctx.group_id, target_id)
    threshold = await _get_warn_threshold(ctx.group_id)
    return f"✅ С *{target_name}* снято одно предупреждение. Осталось: [{remaining}/{threshold}]"

async def clearwarns_user_in_group(ctx: BrainContext, bot) -> str:
    if not await _check_permission(ctx, CAN_WARN, bot):
        return ""
    target_id, target_name, target_tg_id = await _get_target(ctx, bot)
    if not target_id and not target_tg_id:
        return "👥 Укажи пользователя."
    if not target_id:
        return f"⚠️ *{target_name}* не зарегистрирован в боте."
    await clear_warns(ctx.group_id, target_id)
    return f"✅ Все предупреждения *{target_name}* сняты."

async def warns_user_in_group(ctx: BrainContext, bot) -> str:
    target_id, target_name, target_tg_id = await _get_target(ctx, bot)
    if not target_id and not target_tg_id:
        target_id = ctx.user_id
        target_name = ctx.user.first_name or "Вы"
    if not target_id:
        return f"⚠️ *{target_name}* не зарегистрирован в боте."
    count = await get_warn_count(ctx.group_id, target_id)
    threshold = await _get_warn_threshold(ctx.group_id)
    return f"📋 Предупреждения *{target_name}*: [{count}/{threshold}]"

# МУТ / РАЗМУТ
async def mute_user_in_group(ctx: BrainContext, bot) -> str:
    if not await _check_permission(ctx, CAN_MUTE, bot):
        return ""
    target_id, target_name, target_tg_id = await _get_target(ctx, bot)
    if not target_id and not target_tg_id:
        return "👥 Укажи пользователя."
    duration = _parse_duration(ctx.text) or timedelta(hours=1)
    until = datetime.now(timezone.utc) + duration
    reason = _extract_reason(ctx.text)
    if target_id:
        await mute_in_group(ctx.group_id, target_id, ctx.user_id, until, reason)
    if target_tg_id:
        try:
            from aiogram.types import ChatPermissions
            await bot.restrict_chat_member(ctx.chat_id, target_tg_id,
                permissions=ChatPermissions(can_send_messages=False), until_date=until)
        except Exception as e:
            logger.warning(f"[Moderation] Telegram mute failed: {e}")
    reason_text = f"\nПричина: _{reason}_" if reason else ""
    return f"🔇 *{target_name}* замучен на {_format_duration(duration)}{reason_text}"

async def unmute_user_in_group(ctx: BrainContext, bot) -> str:
    if not await _check_permission(ctx, CAN_MUTE, bot):
        return ""
    target_id, target_name, target_tg_id = await _get_target(ctx, bot)
    if not target_id and not target_tg_id:
        return "👥 Укажи пользователя."
    if target_id:
        await unmute_in_group(ctx.group_id, target_id)
    if target_tg_id:
        try:
            from aiogram.types import ChatPermissions
            await bot.restrict_chat_member(ctx.chat_id, target_tg_id,
                permissions=ChatPermissions(can_send_messages=True, can_send_media_messages=True,
                    can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True))
        except Exception as e:
            logger.warning(f"[Moderation] Telegram unmute failed: {e}")
    return f"🔊 *{target_name}* размучен."

# БАН / РАЗБАН
async def ban_user_in_group(ctx: BrainContext, bot) -> str:
    if not await _check_permission(ctx, CAN_BAN, bot):
        return ""
    target_id, target_name, target_tg_id = await _get_target(ctx, bot)
    if not target_id and not target_tg_id:
        return "👥 Укажи пользователя."
    duration = _parse_duration(ctx.text)
    until = datetime.now(timezone.utc) + duration if duration else None
    reason = _extract_reason(ctx.text)
    if target_id:
        await ban_from_group(ctx.group_id, target_id, ctx.user_id, reason, until)
    if target_tg_id:
        try:
            await bot.ban_chat_member(ctx.chat_id, target_tg_id, until_date=until)
        except Exception as e:
            logger.warning(f"[Moderation] Telegram ban failed: {e}")
    reason_text = f"\nПричина: _{reason}_" if reason else ""
    if until:
        return f"🚫 *{target_name}* забанен на {_format_duration(duration)}{reason_text}"
    return f"🚫 *{target_name}* забанен навсегда{reason_text}"

async def unban_user_in_group(ctx: BrainContext, bot) -> str:
    if not await _check_permission(ctx, CAN_BAN, bot):
        return ""
    target_id, target_name, target_tg_id = await _get_target(ctx, bot)
    if not target_id and not target_tg_id:
        return "👥 Укажи пользователя."
    if target_id:
        await unban_from_group(ctx.group_id, target_id)
    if target_tg_id:
        try:
            await bot.unban_chat_member(ctx.chat_id, target_tg_id, only_if_banned=True)
        except Exception as e:
            logger.warning(f"[Moderation] Telegram unban failed: {e}")
    return f"✅ *{target_name}* разбанен."

# КИК
async def kick_user_from_group(ctx: BrainContext, bot) -> str:
    if not await _check_permission(ctx, CAN_KICK, bot):
        return ""
    target_id, target_name, target_tg_id = await _get_target(ctx, bot)
    logger.info(f"[Kick] target_id={target_id} target_name={target_name} target_tg_id={target_tg_id}")
    if not target_id and not target_tg_id:
        return "👥 Укажи пользователя через реплей на его сообщение."
    if not target_tg_id:
        return f"❌ Не удалось кикнуть *{target_name}* — Telegram ID не найден."
    logger.info(f"[Kick] Attempting ban chat_id={ctx.chat_id} tg_id={target_tg_id} type={type(target_tg_id)}")
    try:
        await bot.ban_chat_member(ctx.chat_id, int(target_tg_id))
        await bot.unban_chat_member(ctx.chat_id, int(target_tg_id))
        logger.info(f"[Kick] Success: {target_name} kicked")
    except Exception as e:
        logger.warning(f"[Moderation] Telegram kick failed: {e}")
        return f"❌ Не удалось кикнуть *{target_name}*: {e}"
    return f"👢 *{target_name}* кикнут из группы."

# ПОВЫСИТЬ / ПОНИЗИТЬ
def _extract_steps(text: str) -> int:
    match = re.search(r"\b([1-4])\b", text)
    return int(match.group(1)) if match else 1

async def promote_user_in_group(ctx: BrainContext, bot) -> str:
    if not await _check_permission(ctx, CAN_PROMOTE, bot):
        return ""
    target_id, target_name, target_tg_id = await _get_target(ctx, bot)
    if not target_id and not target_tg_id:
        return "👥 Укажи пользователя — ответь на его сообщение."
    if not target_id:
        return f"❌ *{target_name}* не зарегистрирован в боте — роли недоступны."
    steps = _extract_steps(ctx.text)
    success, old_role, new_role = await promote_member(ctx.group_id, ctx.user_id, target_id, steps)
    if not success:
        return f"❌ Не удалось повысить *{target_name}*. Недостаточно прав или достигнут максимум."
    return f"⬆️ *{target_name}*: {ROLE_NAMES.get(old_role, old_role)} → {ROLE_NAMES.get(new_role, new_role)}"

async def demote_user_in_group(ctx: BrainContext, bot) -> str:
    if not await _check_permission(ctx, CAN_PROMOTE, bot):
        return ""
    target_id, target_name, target_tg_id = await _get_target(ctx, bot)
    if not target_id and not target_tg_id:
        return "👥 Укажи пользователя — ответь на его сообщение."
    if not target_id:
        return f"❌ *{target_name}* не зарегистрирован в боте — роли недоступны."
    steps = _extract_steps(ctx.text)
    success, old_role, new_role = await demote_member(ctx.group_id, ctx.user_id, target_id, steps)
    if not success:
        return f"❌ Не удалось понизить *{target_name}*. Недостаточно прав."
    return f"⬇️ *{target_name}*: {ROLE_NAMES.get(old_role, old_role)} → {ROLE_NAMES.get(new_role, new_role)}"

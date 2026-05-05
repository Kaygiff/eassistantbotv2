"""
groups/moderation.py — Команды модерации в группах.
Мут/размут, бан/разбан, кик, варны, повышение/понижение ролей.
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

# ---------------------------------------------------------------------------
# Названия ролей для вывода
# ---------------------------------------------------------------------------

ROLE_NAMES = {
    "owner":    "👑 Владелец",
    "co_owner": "🌟 Со-владелец",
    "admin":    "🛡 Администратор",
    "moderator": "⚔️ Модератор",
    "vip":      "💎 VIP",
    "user":     "👤 Участник",
}

# ---------------------------------------------------------------------------
# Парсинг времени: 30м, 1ч, 2д и т.д.
# ---------------------------------------------------------------------------

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
    """Парсит строку вида '30м', '2ч', '7д' в timedelta. None если не найдено."""
    match = _TIME_RE.search(text)
    if not match:
        return None
    amount = int(match.group(1))
    unit = match.group(2).lower()
    seconds = _TIME_MAP.get(unit)
    if not seconds:
        return None
    return timedelta(seconds=amount * seconds)


def _format_duration(td: timedelta) -> str:
    total = int(td.total_seconds())
    if total >= 86400:
        return f"{total // 86400} д."
    if total >= 3600:
        return f"{total // 3600} ч."
    return f"{total // 60} мин."


# ---------------------------------------------------------------------------
# Получение цели (reply или @username)
# ---------------------------------------------------------------------------

async def _get_target(ctx: BrainContext) -> tuple[Optional[str], Optional[str], Optional[int]]:
    """
    Возвращает (user_uuid, display_name, telegram_id).
    Ищет по reply → @username.
    """
    from api.auth.identity import get_user_by_telegram_id
    from infra.db.supabase import get_supabase_admin

    if ctx.reply_to_user_telegram_id:
        user = await get_user_by_telegram_id(ctx.reply_to_user_telegram_id)
        if user:
            name = user.first_name or f"@{user.username}"
            return str(user.id), name, user.telegram_id

    match = re.search(r"@(\w+)", ctx.text)
    if match:
        res = (
            get_supabase_admin()
            .table("users")
            .select("id, first_name, username, telegram_id")
            .eq("username", match.group(1))
            .maybe_single()
            .execute()
        )
        if res.data:
            name = res.data.get("first_name") or f"@{res.data.get('username')}"
            return res.data["id"], name, res.data["telegram_id"]

    return None, None, None


def _extract_reason(text: str) -> Optional[str]:
    match = re.search(r"причина[:\s]+(.+)", text, re.IGNORECASE)
    return match.group(1).strip() if match else None


async def _check_permission(ctx: BrainContext, allowed_set: set, bot) -> bool:
    """Проверяет права и отправляет ошибку если нет доступа."""
    if not ctx.group_id:
        await bot.send_message(ctx.chat_id, "❌ Группа не найдена.")
        return False
    role = await get_group_member_role(ctx.group_id, ctx.user_id)
    if role not in allowed_set:
        await bot.send_message(ctx.chat_id, t(ctx.language, "common.access_denied"))
        return False
    return True


# ---------------------------------------------------------------------------
# ВАРН
# ---------------------------------------------------------------------------

async def warn_user_in_group(ctx: BrainContext, bot) -> str:
    if not await _check_permission(ctx, CAN_WARN, bot):
        return ""

    target_id, target_name, _ = await _get_target(ctx)
    if not target_id:
        return "👥 Укажи пользователя через @username или ответь на его сообщение."

    reason = _extract_reason(ctx.text)
    count, threshold = await warn_user(ctx.group_id, target_id, ctx.user_id, reason)

    if count >= threshold:
        await ban_from_group(ctx.group_id, target_id, ctx.user_id,
                             reason=f"Автобан: {count} варнов")
        try:
            tg_res = _get_telegram_id(target_id)
            if tg_res:
                await bot.ban_chat_member(ctx.chat_id, tg_res)
        except Exception as e:
            logger.warning(f"[Moderation] Autoban telegram failed: {e}")
        return t(ctx.language, "moderation.auto_banned", username=target_name, max=threshold)

    reason_text = f"\nПричина: _{reason}_" if reason else ""
    return f"⚠️ *{target_name}* получает предупреждение [{count}/{threshold}]{reason_text}"


# ---------------------------------------------------------------------------
# СНЯТЬ ВАРН / СНЯТЬ ВАРНЫ
# ---------------------------------------------------------------------------

async def unwarn_user_in_group(ctx: BrainContext, bot) -> str:
    if not await _check_permission(ctx, CAN_WARN, bot):
        return ""

    target_id, target_name, _ = await _get_target(ctx)
    if not target_id:
        return "👥 Укажи пользователя."

    remaining = await unwarn_user(ctx.group_id, target_id)
    group_res = _get_warn_threshold(ctx.group_id)
    return f"✅ С *{target_name}* снято одно предупреждение. Осталось: [{remaining}/{group_res}]"


async def clearwarns_user_in_group(ctx: BrainContext, bot) -> str:
    if not await _check_permission(ctx, CAN_WARN, bot):
        return ""

    target_id, target_name, _ = await _get_target(ctx)
    if not target_id:
        return "👥 Укажи пользователя."

    await clear_warns(ctx.group_id, target_id)
    return f"✅ Все предупреждения *{target_name}* сняты."


async def warns_user_in_group(ctx: BrainContext, bot) -> str:
    target_id, target_name, _ = await _get_target(ctx)
    if not target_id:
        # Если не указан — показываем свои варны
        target_id = ctx.user_id
        target_name = ctx.user.first_name or "Вы"

    count = await get_warn_count(ctx.group_id, target_id)
    threshold = _get_warn_threshold(ctx.group_id)
    return f"📋 Предупреждения *{target_name}*: [{count}/{threshold}]"


def _get_warn_threshold(group_id: str) -> int:
    from infra.db.supabase import get_supabase_admin
    res = (
        get_supabase_admin()
        .table("groups")
        .select("warn_threshold")
        .eq("id", group_id)
        .maybe_single()
        .execute()
    )
    return res.data["warn_threshold"] if res.data else 3


def _get_telegram_id(user_uuid: str) -> Optional[int]:
    from infra.db.supabase import get_supabase_admin
    res = (
        get_supabase_admin()
        .table("users")
        .select("telegram_id")
        .eq("id", user_uuid)
        .maybe_single()
        .execute()
    )
    return res.data["telegram_id"] if res.data else None


# ---------------------------------------------------------------------------
# МУТ / РАЗМУТ
# ---------------------------------------------------------------------------

async def mute_user_in_group(ctx: BrainContext, bot) -> str:
    if not await _check_permission(ctx, CAN_MUTE, bot):
        return ""

    target_id, target_name, target_tg_id = await _get_target(ctx)
    if not target_id:
        return "👥 Укажи пользователя."

    duration = _parse_duration(ctx.text) or timedelta(hours=1)
    until = datetime.now(timezone.utc) + duration
    reason = _extract_reason(ctx.text)

    await mute_in_group(ctx.group_id, target_id, ctx.user_id, until, reason)

    if target_tg_id:
        try:
            from aiogram.types import ChatPermissions
            await bot.restrict_chat_member(
                ctx.chat_id,
                target_tg_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until,
            )
        except Exception as e:
            logger.warning(f"[Moderation] Telegram mute failed: {e}")

    reason_text = f"\nПричина: _{reason}_" if reason else ""
    return f"🔇 *{target_name}* замучен на {_format_duration(duration)}{reason_text}"


async def unmute_user_in_group(ctx: BrainContext, bot) -> str:
    if not await _check_permission(ctx, CAN_MUTE, bot):
        return ""

    target_id, target_name, target_tg_id = await _get_target(ctx)
    if not target_id:
        return "👥 Укажи пользователя."

    await unmute_in_group(ctx.group_id, target_id)

    if target_tg_id:
        try:
            from aiogram.types import ChatPermissions
            await bot.restrict_chat_member(
                ctx.chat_id,
                target_tg_id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_polls=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                ),
            )
        except Exception as e:
            logger.warning(f"[Moderation] Telegram unmute failed: {e}")

    return f"🔊 *{target_name}* размучен."


# ---------------------------------------------------------------------------
# БАН / РАЗБАН
# ---------------------------------------------------------------------------

async def ban_user_in_group(ctx: BrainContext, bot) -> str:
    if not await _check_permission(ctx, CAN_BAN, bot):
        return ""

    target_id, target_name, target_tg_id = await _get_target(ctx)
    if not target_id:
        return "👥 Укажи пользователя."

    duration = _parse_duration(ctx.text)
    until = datetime.now(timezone.utc) + duration if duration else None
    reason = _extract_reason(ctx.text)

    await ban_from_group(ctx.group_id, target_id, ctx.user_id, reason, until)

    if target_tg_id:
        try:
            await bot.ban_chat_member(
                ctx.chat_id,
                target_tg_id,
                until_date=until,
            )
        except Exception as e:
            logger.warning(f"[Moderation] Telegram ban failed: {e}")

    reason_text = f"\nПричина: _{reason}_" if reason else ""
    if until:
        return f"🚫 *{target_name}* забанен на {_format_duration(duration)}{reason_text}"
    return f"🚫 *{target_name}* забанен навсегда{reason_text}"


async def unban_user_in_group(ctx: BrainContext, bot) -> str:
    if not await _check_permission(ctx, CAN_BAN, bot):
        return ""

    target_id, target_name, target_tg_id = await _get_target(ctx)
    if not target_id:
        return "👥 Укажи пользователя."

    await unban_from_group(ctx.group_id, target_id)

    if target_tg_id:
        try:
            await bot.unban_chat_member(ctx.chat_id, target_tg_id,
                                        only_if_banned=True)
        except Exception as e:
            logger.warning(f"[Moderation] Telegram unban failed: {e}")

    return f"✅ *{target_name}* разбанен."


# ---------------------------------------------------------------------------
# КИК
# ---------------------------------------------------------------------------

async def kick_user_from_group(ctx: BrainContext, bot) -> str:
    if not await _check_permission(ctx, CAN_KICK, bot):
        return ""

    target_id, target_name, target_tg_id = await _get_target(ctx)
    if not target_id:
        return "👥 Укажи пользователя."

    if target_tg_id:
        try:
            await bot.ban_chat_member(ctx.chat_id, target_tg_id)
            await bot.unban_chat_member(ctx.chat_id, target_tg_id)
        except Exception as e:
            logger.warning(f"[Moderation] Telegram kick failed: {e}")

    return f"👢 *{target_name}* кикнут из группы."


# ---------------------------------------------------------------------------
# ПОВЫСИТЬ / ПОНИЗИТЬ
# ---------------------------------------------------------------------------

def _extract_steps(text: str) -> int:
    match = re.search(r"\b([1-4])\b", text)
    return int(match.group(1)) if match else 1


async def promote_user_in_group(ctx: BrainContext, bot) -> str:
    if not await _check_permission(ctx, CAN_PROMOTE, bot):
        return ""

    target_id, target_name, _ = await _get_target(ctx)
    if not target_id:
        return "👥 Укажи пользователя."

    steps = _extract_steps(ctx.text)
    success, old_role, new_role = await promote_member(
        ctx.group_id, ctx.user_id, target_id, steps
    )

    if not success:
        return f"❌ Не удалось повысить *{target_name}*. Недостаточно прав или достигнут максимум."

    old_name = ROLE_NAMES.get(old_role, old_role)
    new_name = ROLE_NAMES.get(new_role, new_role)
    return f"⬆️ *{target_name}*: {old_name} → {new_name}"


async def demote_user_in_group(ctx: BrainContext, bot) -> str:
    if not await _check_permission(ctx, CAN_PROMOTE, bot):
        return ""

    target_id, target_name, _ = await _get_target(ctx)
    if not target_id:
        return "👥 Укажи пользователя."

    steps = _extract_steps(ctx.text)
    success, old_role, new_role = await demote_member(
        ctx.group_id, ctx.user_id, target_id, steps
    )

    if not success:
        return f"❌ Не удалось понизить *{target_name}*. Недостаточно прав."

    old_name = ROLE_NAMES.get(old_role, old_role)
    new_name = ROLE_NAMES.get(new_role, new_role)
    return f"⬇️ *{target_name}*: {old_name} → {new_name}"

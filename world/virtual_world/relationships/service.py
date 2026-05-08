"""
virtual_world/relationships/service.py — Отношения и браки.

Команды (через reply на сообщение партнёра):
  встречаться  — предложить отношения
  расстаться   — разорвать отношения (только dating)
  брак         — предложить брак (только если уже dating)
  развод       — развестись (только married)

Команды (без reply):
  мои отношения / мой брак — статус с датой, длительностью и совместимостью

Совместимость 0–100: +1 очко каждые 12 часов вместе, максимум 100.
Cooldown: 1 час общий + 24 часа к конкретному человеку после отказа.
"""

from __future__ import annotations
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from infra.db.supabase import get_supabase_admin
from core.models.user import User
from bot.brain.context import BrainContext
from infra.db.redis import get_redis

logger = logging.getLogger(__name__)

# --- Cooldown ключи ---
def _propose_global_key(user_id: str) -> str:
    return f"rel:propose_global:{user_id}"

def _propose_rejected_key(from_id: str, to_id: str) -> str:
    return f"rel:propose_rejected:{from_id}:{to_id}"

PROPOSE_GLOBAL_COOLDOWN   = 3600   # 1 час между любыми предложениями
PROPOSE_REJECTED_COOLDOWN = 86400  # 24 часа к конкретному после отказа

# --- Уровни совместимости ---
COMPAT_LEVELS = [
    (0,  "🌱 Знакомые"),
    (20, "🌸 Симпатия"),
    (40, "💛 Привязанность"),
    (60, "❤️ Влюблённость"),
    (80, "🔥 Страсть"),
    (95, "💎 Вечная любовь"),
]


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _compat_label(score: int) -> str:
    label = COMPAT_LEVELS[0][1]
    for threshold, name in COMPAT_LEVELS:
        if score >= threshold:
            label = name
    return label


def _ordered_pair(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a < b else (b, a)


def _days_together(started_at: str) -> int:
    try:
        dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        return max(0, (datetime.now(timezone.utc) - dt).days)
    except Exception:
        return 0


def _calc_compatibility(started_at: str) -> int:
    """1 очко за каждые 12 часов вместе, максимум 100."""
    try:
        dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        return min(100, int(hours / 12))
    except Exception:
        return 0


def _partner_display(partner_data: dict) -> str:
    """Имя (@username) или просто имя если username нет."""
    name = partner_data.get("first_name") or "Пользователь"
    username = partner_data.get("username")
    if username:
        return f"{name} (@{username})"
    return name


async def _get_partner_data(rel: dict, user_id: str) -> dict:
    partner_id = rel["user_b_id"] if rel["user_a_id"] == user_id else rel["user_a_id"]
    p = get_supabase_admin().table("users").select("first_name, username").eq("id", partner_id).maybe_single().execute()
    return p.data or {}


# ---------------------------------------------------------------------------
# Cooldown
# ---------------------------------------------------------------------------

async def _check_propose_cooldown(from_id: str, to_id: str) -> Optional[str]:
    redis = get_redis()
    ttl_global = await redis.ttl(_propose_global_key(from_id))
    if ttl_global > 0:
        mins = ttl_global // 60 + 1
        return f"⏳ Подожди ещё {mins} мин. перед следующим предложением."
    ttl_rejected = await redis.ttl(_propose_rejected_key(from_id, to_id))
    if ttl_rejected > 0:
        hours = ttl_rejected // 3600 + 1
        return f"⏳ Этот человек уже отклонял тебя. Попробуй через {hours} ч."
    return None


async def _set_propose_cooldown(from_id: str) -> None:
    redis = get_redis()
    await redis.set(_propose_global_key(from_id), "1", ex=PROPOSE_GLOBAL_COOLDOWN)


async def _set_rejected_cooldown(from_id: str, to_id: str) -> None:
    redis = get_redis()
    await redis.set(_propose_rejected_key(from_id, to_id), "1", ex=PROPOSE_REJECTED_COOLDOWN)


# ---------------------------------------------------------------------------
# Уведомление с кнопками
# ---------------------------------------------------------------------------

async def _notify_with_buttons(user_id: str, text: str, buttons: list[list[dict]]) -> None:
    """Отправляет уведомление с inline-кнопками по UUID пользователя."""
    from infra.notifications.sender import send_message_async
    res = get_supabase_admin().table("users").select("telegram_id").eq("id", user_id).maybe_single().execute()
    if not res.data:
        return
    await send_message_async(
        res.data["telegram_id"],
        text,
        reply_markup={"inline_keyboard": buttons},
    )


# ---------------------------------------------------------------------------
# Профиль: строка семейного положения
# ---------------------------------------------------------------------------

async def get_current_relationship(user_id: str) -> Optional[dict]:
    res = (
        get_supabase_admin().table("relationships")
        .select("*")
        .or_(f"user_a_id.eq.{user_id},user_b_id.eq.{user_id}")
        .maybe_single()
        .execute()
    )
    return res.data


async def get_relationship_profile_line(user_id: str) -> Optional[str]:
    """Динамическая строка для профиля. Обновляется автоматически."""
    rel = await get_current_relationship(user_id)
    if not rel:
        return None
    partner_data = await _get_partner_data(rel, user_id)
    if not partner_data:
        return None
    partner = _partner_display(partner_data)
    if rel["status"] == "married":
        return f"💍 В браке с *{partner}*"
    return f"❤️ Встречается с *{partner}*"


# ---------------------------------------------------------------------------
# Предложение отношений (через reply)
# ---------------------------------------------------------------------------

async def propose_dating(initiator: User, target: User, bot) -> str:
    init_id   = str(initiator.id)
    target_id = str(target.id)

    if init_id == target_id:
        return "💔 Нельзя начать отношения с самим собой."

    if await get_current_relationship(init_id):
        return "💔 У тебя уже есть отношения. Сначала расстанься."

    if await get_current_relationship(target_id):
        return "💔 Этот человек уже в отношениях."

    bl = (
        get_supabase_admin().table("blacklist")
        .select("id")
        .eq("blocker_id", target_id)
        .eq("blocked_id", init_id)
        .maybe_single()
        .execute()
    )
    if bl.data:
        return "🚫 Этот человек тебя заблокировал."

    cooldown_msg = await _check_propose_cooldown(init_id, target_id)
    if cooldown_msg:
        return cooldown_msg

    await _set_propose_cooldown(init_id)

    await _notify_with_buttons(
        target_id,
        f"💌 *{initiator.display_name}* предлагает тебе встречаться!\n\nПринять предложение?",
        [[
            {"text": "❤️ Принять",   "callback_data": f"relationship:accept_dating:{init_id}"},
            {"text": "❌ Отклонить", "callback_data": f"relationship:decline_dating:{init_id}"},
        ]],
    )
    return f"💌 Предложение отправлено *{target.display_name}*. Ждём ответа..."


# ---------------------------------------------------------------------------
# Расставание
# ---------------------------------------------------------------------------

async def breakup(user_id: str) -> str:
    rel = await get_current_relationship(user_id)
    if not rel:
        return "💔 У тебя нет активных отношений."
    if rel["status"] == "married":
        return "💍 Вы в браке. Для развода напиши «развод»."

    partner_id = rel["user_b_id"] if rel["user_a_id"] == user_id else rel["user_a_id"]
    get_supabase_admin().table("relationships").delete().eq("id", rel["id"]).execute()

    from infra.notifications.sender import notify_user
    await notify_user(partner_id, "💔 Ваши отношения завершены.")
    return "💔 Вы расстались."


# ---------------------------------------------------------------------------
# Предложение брака (через reply, только если уже dating)
# ---------------------------------------------------------------------------

async def propose_marriage(initiator: User, target: User, bot) -> str:
    init_id   = str(initiator.id)
    target_id = str(target.id)

    rel = await get_current_relationship(init_id)
    if not rel:
        return "💔 Для предложения брака нужно сначала встречаться."
    if rel["status"] == "married":
        return "💍 Вы уже женаты!"

    partner_id = rel["user_b_id"] if rel["user_a_id"] == init_id else rel["user_a_id"]
    if partner_id != target_id:
        return "💔 Предложение можно сделать только своему партнёру."

    cooldown_msg = await _check_propose_cooldown(init_id, target_id)
    if cooldown_msg:
        return cooldown_msg

    await _set_propose_cooldown(init_id)

    await _notify_with_buttons(
        target_id,
        f"💍 *{initiator.display_name}* делает тебе предложение руки и сердца!\n\nСогласен(а)?",
        [[
            {"text": "💍 Да!",  "callback_data": f"relationship:accept_marriage:{init_id}"},
            {"text": "❌ Нет", "callback_data": f"relationship:decline_marriage:{init_id}"},
        ]],
    )
    return f"💍 Предложение о браке отправлено *{target.display_name}*."


# ---------------------------------------------------------------------------
# Развод
# ---------------------------------------------------------------------------

async def divorce(user_id: str) -> str:
    rel = await get_current_relationship(user_id)
    if not rel or rel["status"] != "married":
        return "📝 Вы не состоите в браке."

    partner_id = rel["user_b_id"] if rel["user_a_id"] == user_id else rel["user_a_id"]
    get_supabase_admin().table("relationships").delete().eq("id", rel["id"]).execute()

    from infra.notifications.sender import notify_user
    await notify_user(partner_id, "📝 Ваш брак расторгнут.")
    return "📝 Развод оформлен."


# ---------------------------------------------------------------------------
# Статус отношений («мои отношения» / «мой брак»)
# ---------------------------------------------------------------------------

async def get_relationship_status(user_id: str) -> str:
    rel = await get_current_relationship(user_id)
    if not rel:
        return (
            "💔 Ты сейчас свободен(а).\n\n"
            "Чтобы начать отношения — ответь на сообщение человека командой «встречаться»."
        )

    partner_data = await _get_partner_data(rel, user_id)
    partner = _partner_display(partner_data) if partner_data else "Неизвестно"

    started      = rel["started_at"][:10]
    days_dating  = _days_together(rel["started_at"])
    compat       = _calc_compatibility(rel["started_at"])
    level        = _compat_label(compat)

    if rel["status"] == "married":
        married_at   = rel.get("married_at") or rel["started_at"]
        married_date = married_at[:10]
        days_married = _days_together(married_at)
        return (
            f"💍 *Брак*\n\n"
            f"👫 Партнёр: *{partner}*\n"
            f"📅 Начали встречаться: {started} ({days_dating} дн.)\n"
            f"💒 Дата свадьбы: {married_date} ({days_married} дн. в браке)\n"
            f"💞 Совместимость: {compat}/100 — {level}"
        )

    return (
        f"❤️ *Отношения*\n\n"
        f"👫 Партнёр: *{partner}*\n"
        f"📅 Вместе с: {started} ({days_dating} дн.)\n"
        f"💞 Совместимость: {compat}/100 — {level}\n\n"
        f"_Хочешь жениться? Ответь на сообщение партнёра командой «брак»._"
    )


# ---------------------------------------------------------------------------
# Callback: принять / отклонить
# ---------------------------------------------------------------------------

async def handle_relationship_callback(ctx: BrainContext, action: str, param: str | None) -> str | None:
    user_id = str(ctx.user.id)

    if action == "accept_dating" and param:
        if await get_current_relationship(user_id) or await get_current_relationship(param):
            return "💔 Кто-то из вас уже в отношениях. Предложение недействительно."
        user_a, user_b = _ordered_pair(param, user_id)
        get_supabase_admin().table("relationships").insert({
            "id": str(uuid.uuid4()),
            "user_a_id": user_a,
            "user_b_id": user_b,
            "status": "dating",
        }).execute()
        from infra.notifications.sender import notify_user
        await notify_user(param, f"❤️ *{ctx.user.display_name}* принял(а) твоё предложение! Вы теперь вместе 🎉")
        return "❤️ Вы теперь встречаетесь! 🎉"

    elif action == "decline_dating" and param:
        await _set_rejected_cooldown(param, user_id)
        from infra.notifications.sender import notify_user
        await notify_user(param, "💔 Твоё предложение отклонено.")
        return "❌ Предложение отклонено."

    elif action == "accept_marriage" and param:
        rel = await get_current_relationship(user_id)
        if not rel:
            return "💔 Отношения не найдены."
        get_supabase_admin().table("relationships").update({
            "status": "married",
            "married_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", rel["id"]).execute()
        from infra.notifications.sender import notify_user
        await notify_user(param, "💒 Она(он) сказал(а) «Да»! Поздравляем с браком! 🎊")
        return "💒 Поздравляем! Вы теперь женаты! 🎊"

    elif action == "decline_marriage" and param:
        await _set_rejected_cooldown(param, user_id)
        from infra.notifications.sender import notify_user
        await notify_user(param, "💔 Предложение о браке отклонено.")
        return "❌ Предложение о браке отклонено."

    return None


async def handle_relationship_fsm(ctx: BrainContext, bot, state: str) -> bool:
    return False

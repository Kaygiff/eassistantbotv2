"""
virtual_world/actions/service.py — Действия между пользователями.
Работает в групповом чате, реплаит на сообщение цели.
"""

from __future__ import annotations
import uuid
import logging
from typing import Optional

from infra.db.supabase import get_supabase_admin
from infra.db.redis import get_redis, cooldown_key
from bot.brain.context import BrainContext
from infra.notifications.sender import notify_user

logger = logging.getLogger(__name__)

COOLDOWN_SECONDS = 300  # 5 минут между одинаковыми действиями на одну пару

# ---------------------------------------------------------------------------
# Словарь действий
#
# text        — шаблон сообщения в чат ({initiator}, {target})
# notify      — шаблон личного уведомления цели
# emoji       — основное эмодзи
# category    — friendly / emotional / aggressive / gift
# gif_file_id — Telegram file_id GIF (None = без GIF)
#               Заполни свои file_id после получения через @RawDataBot
# ---------------------------------------------------------------------------
ACTIONS: dict[str, dict] = {

    # ── Дружеские ──────────────────────────────────────────────────────────
    "обнять": {
        "category": "friendly", "emoji": "🤗",
        "text": "{initiator} крепко обнял(а) {target}!",
        "notify": "{initiator} обнял(а) тебя! 🤗",
        "gif_file_id": None,
    },
    "обними": {
        "category": "friendly", "emoji": "🤗",
        "text": "{initiator} крепко обнял(а) {target}!",
        "notify": "{initiator} обнял(а) тебя! 🤗",
        "gif_file_id": None,
    },
    "погладить": {
        "category": "friendly", "emoji": "🤚",
        "text": "{initiator} нежно погладил(а) {target} по голове.",
        "notify": "{initiator} погладил(а) тебя по голове 🤚",
        "gif_file_id": None,
    },
    "погладь": {
        "category": "friendly", "emoji": "🤚",
        "text": "{initiator} нежно погладил(а) {target} по голове.",
        "notify": "{initiator} погладил(а) тебя по голове 🤚",
        "gif_file_id": None,
    },
    "похлопать": {
        "category": "friendly", "emoji": "👏",
        "text": "{initiator} одобрительно похлопал(а) {target} по плечу!",
        "notify": "{initiator} похлопал(а) тебя по плечу 👏",
        "gif_file_id": None,
    },
    "похлопай": {
        "category": "friendly", "emoji": "👏",
        "text": "{initiator} одобрительно похлопал(а) {target} по плечу!",
        "notify": "{initiator} похлопал(а) тебя по плечу 👏",
        "gif_file_id": None,
    },
    "дать пять": {
        "category": "friendly", "emoji": "🙏",
        "text": "{initiator} дал(а) пять {target}! Огонь! 🔥",
        "notify": "{initiator} дал(а) тебе пять! 🙏",
        "gif_file_id": None,
    },
    "дай пять": {
        "category": "friendly", "emoji": "🙏",
        "text": "{initiator} дал(а) пять {target}! Огонь! 🔥",
        "notify": "{initiator} дал(а) тебе пять! 🙏",
        "gif_file_id": None,
    },
    "подбодрить": {
        "category": "friendly", "emoji": "💪",
        "text": "{initiator} подбодрил(а) {target}: «Ты справишься, я верю в тебя!»",
        "notify": "{initiator} подбодрил(а) тебя 💪",
        "gif_file_id": None,
    },
    "подбодри": {
        "category": "friendly", "emoji": "💪",
        "text": "{initiator} подбодрил(а) {target}: «Ты справишься, я верю в тебя!»",
        "notify": "{initiator} подбодрил(а) тебя 💪",
        "gif_file_id": None,
    },
    "угостить": {
        "category": "friendly", "emoji": "🍕",
        "text": "{initiator} угостил(а) {target} чем-то вкусненьким! Приятного аппетита 😋",
        "notify": "{initiator} угостил(а) тебя! 🍕",
        "gif_file_id": None,
    },
    "угости": {
        "category": "friendly", "emoji": "🍕",
        "text": "{initiator} угостил(а) {target} чем-то вкусненьким! Приятного аппетита 😋",
        "notify": "{initiator} угостил(а) тебя! 🍕",
        "gif_file_id": None,
    },
    "поаплодировать": {
        "category": "friendly", "emoji": "👏",
        "text": "{initiator} устроил(а) настоящие овации для {target}! 👏👏👏",
        "notify": "{initiator} аплодирует тебе! 👏",
        "gif_file_id": None,
    },
    "поаплодируй": {
        "category": "friendly", "emoji": "👏",
        "text": "{initiator} устроил(а) настоящие овации для {target}! 👏👏👏",
        "notify": "{initiator} аплодирует тебе! 👏",
        "gif_file_id": None,
    },
    "станцевать": {
        "category": "friendly", "emoji": "💃",
        "text": "{initiator} пригласил(а) {target} на танец! 🕺💃",
        "notify": "{initiator} зовёт тебя танцевать! 💃",
        "gif_file_id": None,
    },
    "станцуй": {
        "category": "friendly", "emoji": "💃",
        "text": "{initiator} пригласил(а) {target} на танец! 🕺💃",
        "notify": "{initiator} зовёт тебя танцевать! 💃",
        "gif_file_id": None,
    },
    "потанцевать": {
        "category": "friendly", "emoji": "💃",
        "text": "{initiator} пригласил(а) {target} на танец! 🕺💃",
        "notify": "{initiator} зовёт тебя танцевать! 💃",
        "gif_file_id": None,
    },
    "подмигнуть": {
        "category": "friendly", "emoji": "😉",
        "text": "{initiator} подмигнул(а) {target}. Интригует... 😏",
        "notify": "{initiator} подмигнул(а) тебе 😉",
        "gif_file_id": None,
    },
    "подмигни": {
        "category": "friendly", "emoji": "😉",
        "text": "{initiator} подмигнул(а) {target}. Интригует... 😏",
        "notify": "{initiator} подмигнул(а) тебе 😉",
        "gif_file_id": None,
    },
    "прижать": {
        "category": "friendly", "emoji": "🫂",
        "text": "{initiator} нежно прижал(а) {target} к себе.",
        "notify": "{initiator} прижал(а) тебя к себе 🫂",
        "gif_file_id": None,
    },
    "прижми": {
        "category": "friendly", "emoji": "🫂",
        "text": "{initiator} нежно прижал(а) {target} к себе.",
        "notify": "{initiator} прижал(а) тебя к себе 🫂",
        "gif_file_id": None,
    },

    # ── Эмоциональные ──────────────────────────────────────────────────────
    "поцеловать": {
        "category": "emotional", "emoji": "💋",
        "text": "{initiator} поцеловал(а) {target}! 😘",
        "notify": "{initiator} поцеловал(а) тебя! 💋",
        "gif_file_id": None,
    },
    "поцелуй": {
        "category": "emotional", "emoji": "💋",
        "text": "{initiator} поцеловал(а) {target}! 😘",
        "notify": "{initiator} поцеловал(а) тебя! 💋",
        "gif_file_id": None,
    },

    # ── Подарок ────────────────────────────────────────────────────────────
    "подарить": {
        "category": "gift", "emoji": "🎁",
        "text": "{initiator} подарил(а) {target} подарок! 🎁",
        "notify": "{initiator} подарил(а) тебе подарок! 🎁",
        "gif_file_id": None,
    },
    "подари": {
        "category": "gift", "emoji": "🎁",
        "text": "{initiator} подарил(а) {target} подарок! 🎁",
        "notify": "{initiator} подарил(а) тебе подарок! 🎁",
        "gif_file_id": None,
    },

    # ── Агрессивные ────────────────────────────────────────────────────────
    "ударить": {
        "category": "aggressive", "emoji": "👊",
        "text": "{initiator} ударил(а) {target} кулаком! Ай! 😤",
        "notify": "{initiator} ударил(а) тебя! 👊",
        "gif_file_id": None,
    },
    "ударь": {
        "category": "aggressive", "emoji": "👊",
        "text": "{initiator} ударил(а) {target} кулаком! Ай! 😤",
        "notify": "{initiator} ударил(а) тебя! 👊",
        "gif_file_id": None,
    },
    "укусить": {
        "category": "aggressive", "emoji": "😬",
        "text": "{initiator} укусил(а) {target}! Зубастый! 😬",
        "notify": "{initiator} укусил(а) тебя! 😬",
        "gif_file_id": None,
    },
    "укуси": {
        "category": "aggressive", "emoji": "😬",
        "text": "{initiator} укусил(а) {target}! Зубастый! 😬",
        "notify": "{initiator} укусил(а) тебя! 😬",
        "gif_file_id": None,
    },
}

# Длинные ключи проверяются первыми — "дать пять" раньше чем "дать"
_SORTED_KEYS = sorted(ACTIONS.keys(), key=len, reverse=True)


def _detect_action(text: str) -> tuple[str, dict] | None:
    text_lower = text.lower()
    for keyword in _SORTED_KEYS:
        if keyword in text_lower:
            return keyword, ACTIONS[keyword]
    return None


async def _check_cooldown(initiator_id: str, target_id: str, action_type: str) -> bool:
    """True если кулдаун активен (действие недоступно)."""
    redis = get_redis()
    key = cooldown_key(initiator_id, target_id, action_type)
    return bool(await redis.get(key))


async def _set_cooldown(initiator_id: str, target_id: str, action_type: str) -> None:
    redis = get_redis()
    key = cooldown_key(initiator_id, target_id, action_type)
    await redis.setex(key, COOLDOWN_SECONDS, "1")


async def perform_action(ctx: BrainContext, bot) -> None:
    """
    Выполняет действие между пользователями.
    Отправляет сообщение в групповой чат с реплаем на сообщение цели.
    Возвращает None — вся отправка происходит внутри.
    """
    initiator = ctx.user
    initiator_id = str(initiator.id)

    # 1. Определяем действие
    action_data = _detect_action(ctx.text)
    if not action_data:
        return
    action_type, action_info = action_data

    # 2. Определяем цель — через реплай (приоритет) или @username
    target = None
    if ctx.reply_to_user_telegram_id:
        from api.auth.identity import get_user_by_telegram_id
        target = await get_user_by_telegram_id(ctx.reply_to_user_telegram_id)

    if not target:
        import re
        match = re.search(r"@(\w+)", ctx.text)
        if match:
            res = (
                get_supabase_admin()
                .table("users")
                .select("*")
                .eq("username", match.group(1))
                .maybe_single()
                .execute()
            )
            if res.data:
                from core.models.user import User
                target = User(**res.data)

    if not target:
        await bot.send_message(
            ctx.chat_id,
            "👥 Ответь на сообщение пользователя или укажи *@username*.",
            parse_mode="Markdown",
            reply_to_message_id=ctx.message_id,
        )
        return

    target_id = str(target.id)

    # 3. Нельзя действовать на себя
    if target_id == initiator_id:
        await bot.send_message(
            ctx.chat_id,
            "🤔 Нельзя выполнить действие на самого себя.",
            reply_to_message_id=ctx.message_id,
        )
        return

    # 4. Проверяем чёрный список
    bl = (
        get_supabase_admin()
        .table("blacklist")
        .select("id")
        .eq("blocker_id", target_id)
        .eq("blocked_id", initiator_id)
        .maybe_single()
        .execute()
    )
    if bl.data:
        await bot.send_message(
            ctx.chat_id,
            "🚫 Этот пользователь заблокировал тебя.",
            reply_to_message_id=ctx.message_id,
        )
        return

    # 5. Проверяем кулдаун
    if await _check_cooldown(initiator_id, target_id, action_type):
        await bot.send_message(
            ctx.chat_id,
            f"⏳ Подожди немного перед следующим *{action_type}*!",
            parse_mode="Markdown",
            reply_to_message_id=ctx.message_id,
        )
        return

    # 6. Логируем действие
    get_supabase_admin().table("actions_log").insert({
        "id": str(uuid.uuid4()),
        "initiator_id": initiator_id,
        "target_id": target_id,
        "action_type": action_type,
        "category": action_info["category"],
    }).execute()

    # 7. Устанавливаем кулдаун
    await _set_cooldown(initiator_id, target_id, action_type)

    # 8. Формируем имена
    initiator_name = (
        initiator.first_name
        or (f"@{initiator.username}" if initiator.username else "Пользователь")
    )
    target_name = (
        target.first_name
        or (f"@{target.username}" if target.username else "Пользователь")
    )

    emoji = action_info["emoji"]
    text = emoji + " " + action_info["text"].format(
        initiator=initiator_name, target=target_name
    )

    # 9. reply_to_message_id:
    #    — если пришёл реплай → реплаим на сообщение ЦЕЛИ
    #    — иначе → реплаим на сообщение инициатора
    reply_msg_id: Optional[int] = ctx.reply_to_message_id or ctx.message_id

    # 10. Отправка: GIF + подпись или просто текст
    gif_file_id: Optional[str] = action_info.get("gif_file_id")
    try:
        if gif_file_id:
            await bot.send_animation(
                ctx.chat_id,
                animation=gif_file_id,
                caption=text,
                parse_mode="Markdown",
                reply_to_message_id=reply_msg_id,
            )
        else:
            await bot.send_message(
                ctx.chat_id,
                text,
                parse_mode="Markdown",
                reply_to_message_id=reply_msg_id,
            )
    except Exception as e:
        logger.error(f"[Actions] Failed to send action message: {e}")
        # Фолбэк без реплая
        await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")

    # 11. Личное уведомление цели
    try:
        notify_text = action_info["notify"].format(
            initiator=initiator_name, target=target_name
        )
        await notify_user(target_id, notify_text)
    except Exception as e:
        logger.warning(f"[Actions] notify_user failed: {e}")

"""
brain/handlers/family.py — Семейные команды.

Семейные команды обрабатываются ПРЯМЫМ совпадением текста (startswith/exact),
без NLP-классификации через brain — чтобы не спамить в группах.

Триггеры (в нижнем регистре, без знаков):
  Усыновить / удочерить          → reply обязателен
  Принять усыновление            → без reply
  Отказаться от усыновления      → без reply (отклонить входящий запрос)
  Отказаться от ребёнка          → reply обязателен
  Отказаться от родителя         → без reply
  Моя семья / семья              → без reply
"""

import re
import logging

logger = logging.getLogger(__name__)

# Паттерны — только startswith / точное совпадение, re.IGNORECASE
_ADOPT_RE = re.compile(r"^(усынови|удочери)", re.IGNORECASE | re.UNICODE)
_ACCEPT_RE = re.compile(r"^принять усыновление$", re.IGNORECASE | re.UNICODE)
_DECLINE_ADOPTION_RE = re.compile(r"^отказаться от усыновления$", re.IGNORECASE | re.UNICODE)
_REMOVE_CHILD_RE = re.compile(r"^отказаться от ребёнка$|^отказываюсь от ребёнка$", re.IGNORECASE | re.UNICODE)
_LEAVE_FAMILY_RE = re.compile(r"^отказаться от родителя$|^выйти из семьи$", re.IGNORECASE | re.UNICODE)
_FAMILY_VIEW_RE = re.compile(r"^(моя семья|семья)$", re.IGNORECASE | re.UNICODE)


def is_family_command(text: str) -> bool:
    """Быстрая проверка — является ли текст семейной командой."""
    t = text.strip()
    return bool(
        _ADOPT_RE.match(t)
        or _ACCEPT_RE.match(t)
        or _DECLINE_ADOPTION_RE.match(t)
        or _REMOVE_CHILD_RE.match(t)
        or _LEAVE_FAMILY_RE.match(t)
        or _FAMILY_VIEW_RE.match(t)
    )


async def handle_family_command(ctx, bot) -> None:
    """
    Точка входа для семейных команд из group_router.
    ctx.text уже в нижнем регистре не нужен — паттерны IGNORECASE.
    ctx.reply_to_user_telegram_id — telegram_id пользователя из reply.
    """
    from world.virtual_world.family import service as fam

    text = ctx.text.strip()
    reply_tg_id = ctx.reply_to_user_telegram_id
    my_tg_id = ctx.telegram_id

    # --- усыновить/удочерить (reply обязателен) ---
    if _ADOPT_RE.match(text):
        if not reply_tg_id:
            result = "👆 Ответь на сообщение того, кого хочешь усыновить/удочерить."
        else:
            result = await fam.adopt(my_tg_id, reply_tg_id)
        await bot.send_message(ctx.chat_id, result, parse_mode="Markdown",
                               reply_to_message_id=ctx.message_id)
        return

    # --- принять усыновление ---
    if _ACCEPT_RE.match(text):
        result = await fam.accept_adoption(my_tg_id)
        await bot.send_message(ctx.chat_id, result, parse_mode="Markdown",
                               reply_to_message_id=ctx.message_id)
        return

    # --- отказаться от усыновления (входящий запрос) ---
    if _DECLINE_ADOPTION_RE.match(text):
        result = await fam.decline_adoption(my_tg_id)
        await bot.send_message(ctx.chat_id, result, parse_mode="Markdown",
                               reply_to_message_id=ctx.message_id)
        return

    # --- отказаться от ребёнка (reply обязателен) ---
    if _REMOVE_CHILD_RE.match(text):
        if not reply_tg_id:
            result = "👆 Ответь на сообщение ребёнка, от которого хочешь отказаться."
        else:
            result = await fam.remove_child(my_tg_id, reply_tg_id)
        await bot.send_message(ctx.chat_id, result, parse_mode="Markdown",
                               reply_to_message_id=ctx.message_id)
        return

    # --- отказаться от родителя / выйти из семьи ---
    if _LEAVE_FAMILY_RE.match(text):
        result = await fam.leave_family(my_tg_id)
        await bot.send_message(ctx.chat_id, result, parse_mode="Markdown",
                               reply_to_message_id=ctx.message_id)
        return

    # --- моя семья / семья ---
    if _FAMILY_VIEW_RE.match(text):
        result = await fam.get_family_list(my_tg_id)
        await bot.send_message(ctx.chat_id, result, parse_mode="Markdown",
                               reply_to_message_id=ctx.message_id)
        return

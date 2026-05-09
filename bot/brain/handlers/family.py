"""
brain/handlers/family.py — Семейные команды.

В ГРУППАХ: жёсткий match по тексту (is_family_command + handle_family_command),
           вызывается из group_router ДО brain-классификации — без NLP, без спама.

В ЛИЧКЕ: brain классифицирует как FAMILY_ADD / FAMILY_VIEW и попадает сюда
         через стандартный @register.
"""

import re
import logging

from bot.brain.router import register
from bot.brain.intent import Intent
from bot.brain.context import BrainContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Паттерны для групп — только startswith / точное совпадение, IGNORECASE
# ---------------------------------------------------------------------------
_ADOPT_RE        = re.compile(r"^(усынови|удочери)", re.IGNORECASE | re.UNICODE)
_ACCEPT_RE       = re.compile(r"^принять усыновление$", re.IGNORECASE | re.UNICODE)
_DECLINE_RE      = re.compile(r"^отказаться от усыновления$", re.IGNORECASE | re.UNICODE)
_REMOVE_CHILD_RE = re.compile(r"^отказаться от ребёнка$|^отказываюсь от ребёнка$", re.IGNORECASE | re.UNICODE)
_LEAVE_RE        = re.compile(r"^отказаться от родителя$|^выйти из семьи$", re.IGNORECASE | re.UNICODE)
_VIEW_RE         = re.compile(r"^(моя семья|семья)$", re.IGNORECASE | re.UNICODE)


def is_family_command(text: str) -> bool:
    """Быстрая проверка для group_router — является ли текст семейной командой."""
    t = text.strip()
    return bool(
        _ADOPT_RE.match(t)
        or _ACCEPT_RE.match(t)
        or _DECLINE_RE.match(t)
        or _REMOVE_CHILD_RE.match(t)
        or _LEAVE_RE.match(t)
        or _VIEW_RE.match(t)
    )


async def handle_family_command(ctx: BrainContext, bot) -> None:
    """
    Точка входа для семейных команд из group_router (группы).
    Также вызывается из @register-хендлеров ниже (личка).
    """
    from world.virtual_world.family.service import (
        adopt, accept_adoption, decline_adoption,
        remove_child, leave_family, get_family_list,
    )

    text = ctx.text.strip()
    reply_tg_id = ctx.reply_to_user_telegram_id
    my_tg_id = ctx.telegram_id

    # усыновить / удочерить
    if _ADOPT_RE.match(text):
        if not reply_tg_id:
            result = "👆 Ответь на сообщение того, кого хочешь усыновить/удочерить."
        else:
            result = await adopt(my_tg_id, reply_tg_id)
        await bot.send_message(ctx.chat_id, result, parse_mode="Markdown",
                               reply_to_message_id=ctx.message_id)
        return

    # принять усыновление
    if _ACCEPT_RE.match(text):
        result = await accept_adoption(my_tg_id)
        await bot.send_message(ctx.chat_id, result, parse_mode="Markdown",
                               reply_to_message_id=ctx.message_id)
        return

    # отказаться от усыновления (входящий запрос)
    if _DECLINE_RE.match(text):
        result = await decline_adoption(my_tg_id)
        await bot.send_message(ctx.chat_id, result, parse_mode="Markdown",
                               reply_to_message_id=ctx.message_id)
        return

    # отказаться от ребёнка
    if _REMOVE_CHILD_RE.match(text):
        if not reply_tg_id:
            result = "👆 Ответь на сообщение ребёнка, от которого хочешь отказаться."
        else:
            result = await remove_child(my_tg_id, reply_tg_id)
        await bot.send_message(ctx.chat_id, result, parse_mode="Markdown",
                               reply_to_message_id=ctx.message_id)
        return

    # отказаться от родителя / выйти из семьи
    if _LEAVE_RE.match(text):
        result = await leave_family(my_tg_id)
        await bot.send_message(ctx.chat_id, result, parse_mode="Markdown",
                               reply_to_message_id=ctx.message_id)
        return

    # моя семья / семья — и любой FAMILY_VIEW из brain
    result = await get_family_list(my_tg_id)
    await bot.send_message(ctx.chat_id, result, parse_mode="Markdown",
                           reply_to_message_id=ctx.message_id)


# ---------------------------------------------------------------------------
# Регистрация для личного чата (brain классифицирует → попадает сюда)
# ---------------------------------------------------------------------------

@register(Intent.FAMILY_ADD)
async def handle_family_add(ctx: BrainContext, bot) -> None:
    """
    В личке brain может распознать 'усынови', 'хочу стать отцом' и т.п.
    Если это reply — обрабатываем как adopt. Иначе — подсказываем.
    """
    from world.virtual_world.family.service import adopt, accept_adoption, decline_adoption

    text = ctx.text.strip()
    reply_tg_id = ctx.reply_to_user_telegram_id
    my_tg_id = ctx.telegram_id

    # Если это явно "принять усыновление"
    if _ACCEPT_RE.match(text):
        result = await accept_adoption(my_tg_id)
    # Если это явно "отказаться от усыновления"
    elif _DECLINE_RE.match(text):
        result = await decline_adoption(my_tg_id)
    # Если есть reply — усыновляем
    elif reply_tg_id:
        result = await adopt(my_tg_id, reply_tg_id)
    else:
        result = (
            "👨‍👩‍👧 *Семья*\n\n"
            "Чтобы усыновить/удочерить — ответь на сообщение нужного пользователя "
            "и напиши *усыновить* или *удочерить*.\n\n"
            "Чтобы принять входящий запрос — напиши *принять усыновление*.\n"
            "Чтобы отклонить — *отказаться от усыновления*."
        )

    await bot.send_message(ctx.chat_id, result, parse_mode="Markdown")


@register(Intent.FAMILY_VIEW)
async def handle_family_view(ctx: BrainContext, bot) -> None:
    from world.virtual_world.family.service import get_family_list
    result = await get_family_list(ctx.telegram_id)
    await bot.send_message(ctx.chat_id, result, parse_mode="Markdown")

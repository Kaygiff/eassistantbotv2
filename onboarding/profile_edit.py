"""
onboarding/profile_edit.py — FSM для редактирования профиля пользователя.
Обрабатывает текстовый ввод после нажатия кнопок в /settings.
"""

from __future__ import annotations
from datetime import datetime

from auth.identity import update_user_field
from auth.session import clear_fsm_state
from audit.logger import log_profile_change
from brain.context import BrainContext
from i18n import t


async def handle_profile_edit_fsm(ctx: BrainContext, bot, state: str) -> bool:
    """
    Обрабатывает ввод пользователя при редактировании профиля.
    Возвращает True если FSM обработал сообщение.
    """
    user_id = str(ctx.user.id)
    text = ctx.text.strip()
    lang = ctx.language

    if not text:
        return True

    if state == "settings:assistant_name":
        if len(text) > 50:
            await bot.send_message(ctx.chat_id, t(lang, "onboarding.name_too_long"))
            return True
        await update_user_field(user_id, assistant_name=text)
        await log_profile_change(user_id, ["assistant_name"])
        await clear_fsm_state(user_id)
        await bot.send_message(ctx.chat_id, f"✅ Имя ассистента изменено на *{text}*", parse_mode="Markdown")

    elif state == "settings:nickname":
        if len(text) > 50:
            await bot.send_message(ctx.chat_id, "⚠️ Никнейм слишком длинный. Максимум 50 символов.")
            return True
        await update_user_field(user_id, nickname=text)
        await log_profile_change(user_id, ["nickname"])
        await clear_fsm_state(user_id)
        await bot.send_message(ctx.chat_id, f"✅ Никнейм изменён на *{text}*", parse_mode="Markdown")

    elif state == "settings:bio":
        if len(text) > 300:
            await bot.send_message(ctx.chat_id, "⚠️ Описание слишком длинное. Максимум 300 символов.")
            return True
        await update_user_field(user_id, bio=text)
        await log_profile_change(user_id, ["bio"])
        await clear_fsm_state(user_id)
        await bot.send_message(ctx.chat_id, "✅ Описание профиля обновлено.")

    elif state == "settings:birthday":
        try:
            birthday = datetime.strptime(text, "%d.%m.%Y").date()
        except ValueError:
            await bot.send_message(ctx.chat_id, "⚠️ Формат: ДД.ММ.ГГГГ (например: 15.03.1995)")
            return True
        await update_user_field(user_id, birthday=str(birthday))
        await log_profile_change(user_id, ["birthday"])
        await clear_fsm_state(user_id)
        await bot.send_message(ctx.chat_id, f"✅ День рождения сохранён: {text}")

    else:
        # Неизвестное settings-состояние — сбрасываем
        await clear_fsm_state(user_id)
        return False

    return True

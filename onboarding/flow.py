"""
onboarding/flow.py — FSM-онбординг нового пользователя.

Шаги:
  1. Приветствие + выбор языка
  2. Ввод имени ассистента
  3. Создание профиля → показ intro

FSM-состояния хранятся в Redis (auth/session.py).
"""

from __future__ import annotations
import logging

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from auth.session import get_fsm_state, set_fsm_state, clear_fsm_state, get_fsm_data, set_fsm_data, clear_fsm_data
from auth.identity import update_user_field
from brain.context import BrainContext
from i18n import t, get_language_keyboard

logger = logging.getLogger(__name__)

# FSM States
STATE_CHOOSE_LANGUAGE = "onboarding:language"
STATE_ENTER_NAME = "onboarding:name"
STATE_COMPLETE = "onboarding:complete"


async def start_onboarding(ctx: BrainContext, bot) -> None:
    """
    Запускает онбординг для нового пользователя.
    Шаг 1: показываем приветствие + кнопки выбора языка.
    """
    await set_fsm_state(str(ctx.user.id), STATE_CHOOSE_LANGUAGE)

    buttons = get_language_keyboard()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b["text"], callback_data=f"onboarding:lang:{b['callback_data'].split(':')[1]}")]
            for b in buttons
        ]
    )

    await bot.send_message(
        ctx.chat_id,
        t("ru", "onboarding.welcome"),
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


async def handle_onboarding_callback(
    ctx: BrainContext,
    callback: CallbackQuery,
    action: str,
    param: str | None,
) -> None:
    """
    Обрабатывает callback кнопок во время онбординга.
    Вызывается из bot/handlers/callbacks.py.
    """
    if not ctx.user:
        return

    user_id = str(ctx.user.id)
    state = await get_fsm_state(user_id)

    # Шаг 1: пользователь выбрал язык
    if action == "lang" and param and state == STATE_CHOOSE_LANGUAGE:
        # Сохраняем язык
        await update_user_field(user_id, language=param)
        ctx.language = param

        # Переходим к шагу 2
        await set_fsm_state(user_id, STATE_ENTER_NAME)
        await set_fsm_data(user_id, {"language": param})

        await callback.message.edit_text(
            t(param, "onboarding.enter_assistant_name"),
            parse_mode="Markdown",
        )

    await callback.answer()


async def handle_onboarding_text(ctx: BrainContext, bot) -> bool:
    """
    Обрабатывает текстовый ввод во время онбординга.
    Возвращает True если сообщение было обработано онбордингом.
    Вызывается из brain/router.py перед классификацией.
    """
    if not ctx.user:
        return False

    user_id = str(ctx.user.id)
    state = await get_fsm_state(user_id)

    if not state or not state.startswith("onboarding:"):
        return False

    # Шаг 2: пользователь вводит имя ассистента
    if state == STATE_ENTER_NAME:
        name = ctx.text.strip()

        if len(name) > 50:
            await bot.send_message(
                ctx.chat_id,
                t(ctx.language, "onboarding.name_too_long"),
            )
            return True

        if not name:
            await bot.send_message(
                ctx.chat_id,
                t(ctx.language, "onboarding.enter_assistant_name"),
                parse_mode="Markdown",
            )
            return True

        # Сохраняем имя ассистента
        await update_user_field(user_id, assistant_name=name)

        # Завершаем онбординг
        await clear_fsm_state(user_id)
        await clear_fsm_data(user_id)

        await bot.send_message(
            ctx.chat_id,
            t(ctx.language, "onboarding.name_saved"),
        )

        await _show_intro(ctx, bot, name)
        return True

    return False


async def _show_intro(ctx: BrainContext, bot, assistant_name: str) -> None:
    """Показывает финальный экран с возможностями бота."""
    await bot.send_message(
        ctx.chat_id,
        t(ctx.language, "onboarding.profile_created"),
    )

    intro_text = t(ctx.language, "onboarding.intro")
    await bot.send_message(
        ctx.chat_id,
        intro_text,
        parse_mode="Markdown",
    )

    logger.info(f"[Onboarding] Completed for user {ctx.telegram_id}, assistant_name={assistant_name}")


async def is_in_onboarding(user_id: str) -> bool:
    """Проверяет находится ли пользователь в процессе онбординга."""
    state = await get_fsm_state(user_id)
    return bool(state and state.startswith("onboarding:"))

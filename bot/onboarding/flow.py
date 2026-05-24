"""
onboarding/flow.py — FSM-онбординг нового пользователя.

Шаги:
  1. Приветствие + выбор языка
  2. Ввод имени бота          (с подсказкой о макс. длине)
  3. Выбор характера бота     (с пояснением что изменится)
  4. Ввод никнейма пользователя
  5. Интро с обращением по имени
"""

from __future__ import annotations
import logging

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from api.auth.session import (
    get_fsm_state, set_fsm_state, clear_fsm_state,
    get_fsm_data, set_fsm_data, clear_fsm_data,
)
from api.auth.identity import update_user_field
from bot.brain.context import BrainContext
from core.i18n import t, get_language_keyboard

logger = logging.getLogger(__name__)

STATE_CHOOSE_LANGUAGE  = "onboarding:language"
STATE_ENTER_BOT_NAME   = "onboarding:bot_name"
STATE_CHOOSE_PERSONA   = "onboarding:personality"
STATE_ENTER_NICKNAME   = "onboarding:nickname"
STATE_COMPLETE         = "onboarding:complete"

PERSONALITIES = {
    "kind":    ("😊", "onboarding.persona_kind"),
    "evil":    ("😈", "onboarding.persona_evil"),
    "neutral": ("😐", "onboarding.persona_neutral"),
}

# Прогресс: шаг → точки
_PROGRESS = {
    STATE_CHOOSE_LANGUAGE: "● ○ ○ ○",
    STATE_ENTER_BOT_NAME:  "● ● ○ ○",
    STATE_CHOOSE_PERSONA:  "● ● ● ○",
    STATE_ENTER_NICKNAME:  "● ● ● ●",
}


def _progress_line(state: str) -> str:
    dots = _PROGRESS.get(state, "")
    return f"`{dots}`\n\n" if dots else ""


def _persona_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{emoji} {t(lang, key)}",
                callback_data=f"onboarding:persona:{code}",
            )]
            for code, (emoji, key) in PERSONALITIES.items()
        ]
    )


async def start_onboarding(ctx: BrainContext, bot) -> None:
    """Шаг 1 — приветствие + выбор языка."""
    await set_fsm_state(str(ctx.user.id), STATE_CHOOSE_LANGUAGE)

    buttons = get_language_keyboard()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=b["text"],
                callback_data=f"onboarding:lang:{b['callback_data'].split(':')[1]}",
            )]
            for b in buttons
        ]
    )

    progress = _progress_line(STATE_CHOOSE_LANGUAGE)
    await bot.send_message(
        ctx.chat_id,
        progress + t("ru", "onboarding.welcome"),
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


async def handle_onboarding_callback(
    ctx: BrainContext,
    callback: CallbackQuery,
    action: str,
    param: str | None,
) -> None:
    """Обрабатывает callback кнопок во время онбординга."""
    if not ctx.user:
        return

    user_id = str(ctx.user.id)
    state = await get_fsm_state(user_id)
    data = await get_fsm_data(user_id) or {}
    lang = data.get("language", "ru")

    # Шаг 1 → 2: выбрали язык
    if action == "lang" and param and state == STATE_CHOOSE_LANGUAGE:
        await update_user_field(user_id, language=param)
        lang = param
        await set_fsm_state(user_id, STATE_ENTER_BOT_NAME)
        await set_fsm_data(user_id, {"language": lang, "pending_ref_code": data.get("pending_ref_code")})

        progress = _progress_line(STATE_ENTER_BOT_NAME)
        await callback.message.edit_text(
            progress + t(lang, "onboarding.enter_bot_name"),
            parse_mode="Markdown",
        )

    # Шаг 3: выбрали характер
    elif action == "persona" and param and state == STATE_CHOOSE_PERSONA:
        await update_user_field(user_id, assistant_personality=param)
        data["personality"] = param
        await set_fsm_data(user_id, data)
        await set_fsm_state(user_id, STATE_ENTER_NICKNAME)

        progress = _progress_line(STATE_ENTER_NICKNAME)
        await callback.message.edit_text(
            progress + t(lang, "onboarding.enter_nickname"),
            parse_mode="Markdown",
        )

    await callback.answer()


async def handle_onboarding_text(ctx: BrainContext, bot) -> bool:
    """
    Обрабатывает текстовый ввод во время онбординга.
    Возвращает True если сообщение было обработано.
    """
    if not ctx.user:
        return False

    user_id = str(ctx.user.id)
    state = await get_fsm_state(user_id)

    if not state or not state.startswith("onboarding:"):
        return False

    data = await get_fsm_data(user_id) or {}
    lang = data.get("language", "ru")
    text = ctx.text.strip()

    # Шаг 2: ввод имени бота
    if state == STATE_ENTER_BOT_NAME:
        if not text:
            progress = _progress_line(STATE_ENTER_BOT_NAME)
            await bot.send_message(ctx.chat_id, progress + t(lang, "onboarding.enter_bot_name"), parse_mode="Markdown")
            return True
        if len(text) > 50:
            await bot.send_message(ctx.chat_id, t(lang, "onboarding.name_too_long"))
            return True

        await update_user_field(user_id, assistant_name=text)
        data["bot_name"] = text
        await set_fsm_data(user_id, data)
        await set_fsm_state(user_id, STATE_CHOOSE_PERSONA)

        progress = _progress_line(STATE_CHOOSE_PERSONA)
        await bot.send_message(
            ctx.chat_id,
            progress + t(lang, "onboarding.choose_personality"),
            parse_mode="Markdown",
            reply_markup=_persona_keyboard(lang),
        )
        return True

    # Шаг 4: ввод никнейма
    if state == STATE_ENTER_NICKNAME:
        if not text:
            progress = _progress_line(STATE_ENTER_NICKNAME)
            await bot.send_message(ctx.chat_id, progress + t(lang, "onboarding.enter_nickname"), parse_mode="Markdown")
            return True
        if len(text) > 32:
            await bot.send_message(ctx.chat_id, t(lang, "onboarding.nickname_too_long"))
            return True

        await update_user_field(user_id, nickname=text)
        data["nickname"] = text
        await set_fsm_data(user_id, data)

        # Обрабатываем реферальный код если есть — пользователь уже в базе
        pending_ref_code = data.get("pending_ref_code")
        if pending_ref_code:
            from world.economy.referral import process_referral
            try:
                await process_referral(ctx.telegram_id, pending_ref_code)
                logger.info(f"[Referral] Processed ref_code={pending_ref_code} for user={ctx.telegram_id}")
            except Exception as e:
                logger.warning(f"[Referral] Failed to process ref_code={pending_ref_code}: {e}")

        await clear_fsm_state(user_id)
        await clear_fsm_data(user_id)

        await _show_intro(ctx, bot, data.get("bot_name", ""), text, lang)
        return True

    return False


async def _show_intro(ctx: BrainContext, bot, bot_name: str, nickname: str, lang: str) -> None:
    """Шаг 5 — финальный экран с обращением по имени и кнопкой руководства."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    import os

    RAILWAY_URL = os.getenv("RAILWAY_PUBLIC_DOMAIN", "eassistantbotv2-production.up.railway.app")
    guide_url = f"https://{RAILWAY_URL}/guide"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="📖 Открыть руководство",
                web_app={"url": guide_url},
            )]
        ]
    )

    await bot.send_message(
        ctx.chat_id,
        t(lang, "onboarding.profile_created", nickname=nickname, bot_name=bot_name),
        parse_mode="Markdown",
    )
    await bot.send_message(
        ctx.chat_id,
        t(lang, "onboarding.intro"),
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
    logger.info(f"[Onboarding] Completed user={ctx.telegram_id} bot_name={bot_name} nickname={nickname}")


async def is_in_onboarding(user_id: str) -> bool:
    state = await get_fsm_state(user_id)
    return bool(state and state.startswith("onboarding:"))


async def resume_onboarding(ctx: BrainContext, bot) -> bool:
    """
    Возобновляет онбординг с того шага, где пользователь остановился.
    Вызывается при повторном /start если онбординг не завершён.
    Возвращает True если онбординг был возобновлён.
    """
    if not ctx.user:
        return False

    user_id = str(ctx.user.id)
    state = await get_fsm_state(user_id)

    if not state or not state.startswith("onboarding:"):
        return False

    data = await get_fsm_data(user_id) or {}
    lang = data.get("language", "ru")

    if state == STATE_CHOOSE_LANGUAGE:
        await start_onboarding(ctx, bot)
        return True

    if state == STATE_ENTER_BOT_NAME:
        progress = _progress_line(STATE_ENTER_BOT_NAME)
        await bot.send_message(ctx.chat_id, progress + t(lang, "onboarding.enter_bot_name"), parse_mode="Markdown")
        return True

    if state == STATE_CHOOSE_PERSONA:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        progress = _progress_line(STATE_CHOOSE_PERSONA)
        await bot.send_message(
            ctx.chat_id,
            progress + t(lang, "onboarding.choose_personality"),
            parse_mode="Markdown",
            reply_markup=_persona_keyboard(lang),
        )
        return True

    if state == STATE_ENTER_NICKNAME:
        progress = _progress_line(STATE_ENTER_NICKNAME)
        await bot.send_message(ctx.chat_id, progress + t(lang, "onboarding.enter_nickname"), parse_mode="Markdown")
        return True

    return False

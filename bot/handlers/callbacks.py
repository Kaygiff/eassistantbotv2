"""
bot/handlers/callbacks.py — Обработка всех inline callback кнопок.
Централизованная точка для callback_data.
Формат callback_data: "namespace:action:param"
"""

from __future__ import annotations
import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery

logger = logging.getLogger(__name__)

callback_router = Router()


async def _get_ctx_and_user(callback: CallbackQuery):
    """Получает пользователя для callback."""
    from auth.identity import get_user_by_telegram_id
    from brain.context import BrainContext

    user = await get_user_by_telegram_id(callback.from_user.id)
    lang = user.language if user else "ru"

    ctx = BrainContext(
        telegram_id=callback.from_user.id,
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        text="",
        is_group=callback.message.chat.type in ("group", "supergroup"),
    )
    ctx.user = user
    ctx.language = lang
    return ctx


# --- Язык ---
@callback_router.callback_query(F.data.startswith("lang:"))
async def cb_language(callback: CallbackQuery) -> None:
    lang = callback.data.split(":")[1]
    from auth.identity import get_user_by_telegram_id, update_user_field
    user = await get_user_by_telegram_id(callback.from_user.id)
    if user:
        await update_user_field(str(user.id), language=lang)
    await callback.answer(f"✅ Язык изменён")
    await callback.message.edit_text(f"🌐 Язык установлен: *{lang.upper()}*", parse_mode="Markdown")


# --- Онбординг ---
@callback_router.callback_query(F.data.startswith("onboarding:"))
async def cb_onboarding(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    action = parts[1]
    ctx = await _get_ctx_and_user(callback)

    from onboarding.flow import handle_onboarding_callback
    await handle_onboarding_callback(ctx, callback, action, parts[2] if len(parts) > 2 else None)


# --- Профиль ---
@callback_router.callback_query(F.data.startswith("profile:"))
async def cb_profile(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    action = parts[1]
    ctx = await _get_ctx_and_user(callback)

    if action == "edit":
        from brain.handlers.profile import handle_profile_edit
        await handle_profile_edit(ctx, callback.message.bot)
    await callback.answer()


# --- Питомец ---
@callback_router.callback_query(F.data.startswith("pet:"))
async def cb_pet(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    action = parts[1]
    ctx = await _get_ctx_and_user(callback)

    if action == "new" and len(parts) > 2:
        species = parts[2]
        from auth.session import set_fsm_state, set_fsm_data
        await set_fsm_state(str(ctx.user.id), "pet:naming")
        await set_fsm_data(str(ctx.user.id), {"species": species})
        from i18n import t
        await callback.message.edit_text(t(ctx.language, "pets.name_pet"))
    elif action == "feed":
        from brain.handlers.pet import handle_pet_feed
        await handle_pet_feed(ctx, callback.message.bot)
    elif action == "play":
        from brain.handlers.pet import handle_pet_play
        await handle_pet_play(ctx, callback.message.bot)
    elif action == "heal":
        from brain.handlers.pet import handle_pet_heal
        await handle_pet_heal(ctx, callback.message.bot)

    await callback.answer()


# --- Казино ---
@callback_router.callback_query(F.data.startswith("casino:"))
async def cb_casino(callback: CallbackQuery) -> None:
    game = callback.data.split(":")[1]
    ctx = await _get_ctx_and_user(callback)
    ctx.text = f"/{game}"

    from brain.intent import Intent
    intent_map = {
        "slots": Intent.CASINO_SLOTS,
        "roulette": Intent.CASINO_ROULETTE,
        "blackjack": Intent.CASINO_BLACKJACK,
        "crash": Intent.CASINO_CRASH,
        "poker": Intent.CASINO_POKER,
    }
    ctx.set_intent(intent_map.get(game, Intent.CASINO_OPEN))

    from i18n import t
    await callback.message.edit_text(t(ctx.language, "casino.enter_bet"))
    await callback.answer()


# --- Настройки ---
@callback_router.callback_query(F.data.startswith("settings:"))
async def cb_settings(callback: CallbackQuery) -> None:
    action = callback.data.split(":")[1]
    ctx = await _get_ctx_and_user(callback)

    if action == "language":
        from i18n import get_language_keyboard
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = get_language_keyboard()
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=b["text"], callback_data=b["callback_data"])]
                             for b in buttons]
        )
        await callback.message.edit_text("🌐 Выбери язык:", reply_markup=keyboard)

    elif action == "assistant_name":
        from auth.session import set_fsm_state
        await set_fsm_state(str(ctx.user.id), "settings:assistant_name")
        await callback.message.edit_text("✏️ Введи новое имя ассистента:")

    await callback.answer()


# --- Отношения ---
@callback_router.callback_query(F.data.startswith("relationship:"))
async def cb_relationship(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    action = parts[1]
    ctx = await _get_ctx_and_user(callback)

    from virtual_world.relationships.service import handle_relationship_callback
    text = await handle_relationship_callback(ctx, action, parts[2] if len(parts) > 2 else None)
    if text:
        await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()

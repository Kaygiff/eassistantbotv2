"""
bot/handlers/callbacks_dice.py — Inline-обработчики игры Кости.

Подключение в bot/handlers/callbacks.py (в конце файла):
    from bot.handlers.callbacks_dice import register_dice_callbacks
    register_dice_callbacks(callback_router)

callback_data схема:
  dice:start              — открыть экран выбора ставки
  dice:bet:<сумма>        — выбрана быстрая ставка (число)
  dice:bet:custom         — игрок хочет ввести сумму вручную
  dice:noop               — заблокированная кнопка (не хватает баланса)
  dice:choice:<h|l>:<bet> — игрок выбрал Больше/Меньше
"""

from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery

from api.auth.session import (
    set_fsm_state, clear_fsm_state,
    set_fsm_data, clear_fsm_data,
)
from bot.handlers.callbacks import _get_ctx_and_user

dice_router = Router()


# ── dice:noop ─────────────────────────────────────────────────────────────────

@dice_router.callback_query(F.data == "dice:noop")
async def cb_dice_noop(callback: CallbackQuery) -> None:
    await callback.answer("💸 Недостаточно средств для этой ставки", show_alert=False)


# ── dice:start / casino:dice ──────────────────────────────────────────────────

@dice_router.callback_query(F.data.in_({"dice:start", "casino:dice"}))
async def cb_dice_start(callback: CallbackQuery) -> None:
    ctx = await _get_ctx_and_user(callback)
    await callback.answer()

    from world.casino.games.dice import open_dice
    await open_dice(
        user_id=str(ctx.user.id),
        language=ctx.language,
        bot=callback.bot,
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
    )


# ── dice:bet:<amount|custom> ──────────────────────────────────────────────────

@dice_router.callback_query(F.data.startswith("dice:bet:"))
async def cb_dice_bet(callback: CallbackQuery) -> None:
    ctx = await _get_ctx_and_user(callback)
    raw = callback.data.split(":")[2]

    if raw == "custom":
        user_id = str(ctx.user.id)
        await set_fsm_state(user_id, "casino:dice_custom_bet")
        await set_fsm_data(user_id, {
            "chat_id": callback.message.chat.id,
            "message_id": callback.message.message_id,
        })
        await callback.message.edit_text(
            "✏️ *Введи сумму ставки* (от 10 до 100 000 Ecoins):",
            parse_mode="Markdown",
        )
        await callback.answer()
        return

    try:
        bet = int(raw)
    except ValueError:
        await callback.answer("❌ Некорректная ставка", show_alert=True)
        return

    await callback.answer()

    from world.casino.games.dice import show_choice_screen
    await show_choice_screen(
        user_id=str(ctx.user.id),
        bet=bet,
        language=ctx.language,
        bot=callback.bot,
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
    )


# ── dice:choice:<high|low>:<bet> ──────────────────────────────────────────────

@dice_router.callback_query(F.data.startswith("dice:choice:"))
async def cb_dice_choice(callback: CallbackQuery) -> None:
    ctx = await _get_ctx_and_user(callback)
    parts = callback.data.split(":")   # ["dice", "choice", "high|low", "<bet>"]

    if len(parts) < 4:
        await callback.answer("❌ Ошибка данных", show_alert=True)
        return

    choice = parts[2]
    try:
        bet = int(parts[3])
    except ValueError:
        await callback.answer("❌ Некорректная ставка", show_alert=True)
        return

    await callback.answer("🎲 Бросаю кубики...")

    from world.casino.games.dice import play_dice_inline
    await play_dice_inline(
        user_id=str(ctx.user.id),
        bet=bet,
        choice=choice,
        language=ctx.language,
        bot=callback.bot,
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
    )


# ── Регистрация ───────────────────────────────────────────────────────────────

def register_dice_callbacks(parent_router: Router) -> None:
    parent_router.include_router(dice_router)

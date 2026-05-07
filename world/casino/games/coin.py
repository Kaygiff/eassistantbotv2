"""casino/games/coin.py — Монетка. Орёл или решка, x2.

UX:
  1. Экран выбора стороны (кнопки Орёл / Решка)
  2. Экран выбора суммы ставки (быстрые кнопки + ½ + Всё)
  3. send_dice(🎲) — нативная анимация Telegram (~3 сек)
  4. Результат с кнопками «Сыграть снова» и «Казино»

send_dice результат игнорируется — исход считается по нашей логике.
"""

from __future__ import annotations

import asyncio
import uuid

import random
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from infra.db.supabase import get_supabase_admin
from world.economy.wallet import debit, credit, get_balance
from core.i18n import t

SIDES = {
    "орёл": "орёл", "орел": "орёл", "о": "орёл", "heads": "орёл",
    "решка": "решка", "р": "решка", "tails": "решка",
}

SIDE_ICON = {"орёл": "🦅", "решка": "🪙"}

QUICK_BETS = [50, 100, 500, 1_000, 5_000]


def parse_coin_choice(raw: str) -> str | None:
    return SIDES.get(raw.strip().lower())


# ---------------------------------------------------------------------------
# Клавиатуры
# ---------------------------------------------------------------------------

def _keyboard_choose_side() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🦅 Орёл", callback_data="coin:side:орёл"),
            InlineKeyboardButton(text="🪙 Решка", callback_data="coin:side:решка"),
        ],
        [InlineKeyboardButton(text="🎰 Казино", callback_data="profile:casino")],
    ])


def _keyboard_bet_amount(side: str, current: int, balance: int) -> InlineKeyboardMarkup:
    rows = []

    quick_row = []
    for q in QUICK_BETS:
        if current + q <= balance:
            quick_row.append(InlineKeyboardButton(
                text=f"+{q}",
                callback_data=f"coin:amount:{side}:{current + q}",
            ))
        if len(quick_row) == 5:
            rows.append(quick_row)
            quick_row = []
    if quick_row:
        rows.append(quick_row)

    halves = []
    if balance > 0:
        halves.append(InlineKeyboardButton(
            text=f"½ ({balance // 2})",
            callback_data=f"coin:amount:{side}:{balance // 2}",
        ))
        halves.append(InlineKeyboardButton(
            text=f"Всё ({balance})",
            callback_data=f"coin:amount:{side}:{balance}",
        ))
    if halves:
        rows.append(halves)

    if current > 0:
        rows.append([InlineKeyboardButton(
            text=f"🗑 Сбросить (текущая: {current})",
            callback_data=f"coin:amount:{side}:0",
        )])

    if current >= 10:
        rows.append([InlineKeyboardButton(
            text=f"🪙 Бросить монетку! Ставка: {current} Ecoins",
            callback_data=f"coin:flip:{side}:{current}",
        )])

    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="coin:back:sides")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _keyboard_result(side: str, bet: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"🔄 Снова ({bet} Ecoins)",
            callback_data=f"coin:flip:{side}:{bet}",
        )],
        [
            InlineKeyboardButton(text="🪙 Другая сторона", callback_data="coin:back:sides"),
            InlineKeyboardButton(text="🎰 Казино",         callback_data="profile:casino"),
        ],
    ])


# ---------------------------------------------------------------------------
# Тексты
# ---------------------------------------------------------------------------

def _text_choose_side(balance: int) -> str:
    return (
        f"🪙 *Монетка*\n\n"
        f"💰 Баланс: *{balance} Ecoins*\n\n"
        f"Выбери сторону:"
    )


def _text_choose_amount(side: str, current: int, balance: int) -> str:
    icon = SIDE_ICON[side]
    return (
        f"🪙 *Монетка* — {icon} {side.capitalize()} (×2)\n\n"
        f"💰 Баланс: *{balance} Ecoins*\n"
        f"🎯 Текущая ставка: *{current} Ecoins*\n\n"
        f"_Минимум: 10 Ecoins_"
    )


# ---------------------------------------------------------------------------
# Открытие экрана
# ---------------------------------------------------------------------------

async def open_coin(
    user_id: str,
    language: str,
    bot: Bot,
    chat_id: int,
    message_id: int | None = None,
) -> None:
    balance = await get_balance(user_id)
    text = _text_choose_side(balance)
    kb = _keyboard_choose_side()
    if message_id:
        try:
            await bot.edit_message_text(
                text, chat_id=chat_id, message_id=message_id,
                parse_mode="Markdown", reply_markup=kb,
            )
            return
        except Exception:
            pass
    await bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=kb)


async def show_coin_bet_screen(
    user_id: str,
    side: str,
    current: int,
    bot: Bot,
    chat_id: int,
    message_id: int,
) -> None:
    balance = await get_balance(user_id)
    text = _text_choose_amount(side, current, balance)
    kb = _keyboard_bet_amount(side, current, balance)
    try:
        await bot.edit_message_text(
            text, chat_id=chat_id, message_id=message_id,
            parse_mode="Markdown", reply_markup=kb,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Бросок
# ---------------------------------------------------------------------------

async def play_coin_inline(
    user_id: str,
    bet: int,
    language: str,
    side: str,
    bot: Bot,
    chat_id: int,
    message_id: int,
) -> None:
    # 1. Списать ставку
    success, balance = await debit(user_id, bet, "casino_bet")
    if not success:
        try:
            await bot.edit_message_text(
                t(language, "economy.insufficient_funds", balance=balance),
                chat_id=chat_id, message_id=message_id,
                parse_mode="Markdown", reply_markup=_keyboard_choose_side(),
            )
        except Exception:
            pass
        return

    # 2. Скрыть кнопки перед анимацией
    try:
        icon = SIDE_ICON[side]
        await bot.edit_message_text(
            f"🪙 *Монетка*\n\n{icon} Ставка на *{side}*...\n\n_Бросаем монетку..._",
            chat_id=chat_id, message_id=message_id,
            parse_mode="Markdown",
        )
    except Exception:
        pass

    # 3. Считаем результат заранее
    result = random.choice(["орёл", "решка"])
    won = side == result

    # 4. Анимация кадрами через edit_message_text
    frames = ["🪙", "🦅", "🪙", "🦅", "🪙", SIDE_ICON[result]]
    delays = [0.30, 0.30, 0.35, 0.35, 0.40, 0.50]

    for frame, delay in zip(frames, delays):
        try:
            await bot.edit_message_text(
                f"🪙 *Монетка*\n\n"
                f"Ставка на {SIDE_ICON[side]} *{side}*\n\n"
                f"{frame}",
                chat_id=chat_id, message_id=message_id,
                parse_mode="Markdown",
            )
        except Exception:
            pass
        await asyncio.sleep(delay)

    # 5. Начисляем
    payout = 0
    if won:
        payout = bet * 2
        await credit(user_id, payout, "game_win")
        outcome = "win"
    else:
        outcome = "loss"

    balance = await get_balance(user_id)

    try:
        get_supabase_admin().table("casino_rounds").insert({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "game_type": "coin",
            "amount": bet,
            "payout": payout,
            "house_fee": 0,
            "outcome": outcome,
            "result": {"choice": side, "result": result},
        }).execute()
    except Exception:
        pass

    # 5. Ждём анимацию
    await asyncio.sleep(3)

    result_icon = SIDE_ICON[result]
    if won:
        profit = payout - bet
        outcome_line = f"🎉 *Победа!* +{profit} Ecoins (×2)"
    else:
        outcome_line = f"😔 *Проигрыш.* −{bet} Ecoins"

    text = (
        f"🪙 *Монетка*\n\n"
        f"Твой выбор: {SIDE_ICON[side]} *{side}*\n"
        f"Выпало: {result_icon} *{result}*\n\n"
        f"{outcome_line}\n\n"
        f"💰 Баланс: *{balance} Ecoins*"
    )

    try:
        await bot.edit_message_text(
            text, chat_id=chat_id, message_id=message_id,
            parse_mode="Markdown",
            reply_markup=_keyboard_result(side, bet),
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Текстовая версия (обратная совместимость)
# ---------------------------------------------------------------------------

async def play_coin(user_id: str, bet: int, language: str, choice: str = "орёл") -> str:
    success, balance = await debit(user_id, bet, "casino_bet")
    if not success:
        return t(language, "economy.insufficient_funds", balance=balance)

    result = random.choice(["орёл", "решка"])
    icon = SIDE_ICON[result]
    won = choice == result
    payout = 0

    if won:
        payout = bet * 2
        await credit(user_id, payout, "game_win")
        msg = t(language, "casino.win", amount=payout - bet)
    else:
        msg = t(language, "casino.loss", amount=bet)

    try:
        get_supabase_admin().table("casino_rounds").insert({
            "id": str(uuid.uuid4()), "user_id": user_id, "game_type": "coin",
            "amount": bet, "payout": payout, "house_fee": 0,
            "outcome": "win" if won else "loss",
            "result": {"choice": choice, "result": result},
        }).execute()
    except Exception:
        pass

    return (
        f"🪙 *Монетка*\n\n"
        f"Твой выбор: *{choice}*\n"
        f"{icon} Выпало: *{result}*\n\n"
        f"{msg}"
    )

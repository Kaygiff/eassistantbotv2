"""casino/games/dice.py — Кости. Угадай: больше, меньше или ровно 7.

UX:
  1. Экран выбора ставки (Больше 7 ×2 / Меньше 7 ×2 / Ровно 7 ×5)
  2. Экран выбора суммы (быстрые кнопки + ½ + Всё)
  3. send_dice(🎲) × 2 — нативная анимация Telegram
  4. Результат с кнопками «Сыграть снова» и «Казино»

Исход считается по нашей логике, dice результат игнорируется.
"""

from __future__ import annotations

import asyncio
import random
import uuid

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from infra.db.supabase import get_supabase_admin
from world.economy.wallet import debit, credit, get_balance
from core.i18n import t

QUICK_BETS = [50, 100, 500, 1_000, 5_000]

CHOICE_INFO = {
    "больше": ("📈 Больше 7", 2),
    "меньше": ("📉 Меньше 7", 2),
    "ровно":  ("🎯 Ровно 7",  5),
}

# Визуализация кубика
DICE_FACES = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]


def _dice_face(n: int) -> str:
    return DICE_FACES[n - 1] if 1 <= n <= 6 else str(n)


# ---------------------------------------------------------------------------
# Клавиатуры
# ---------------------------------------------------------------------------

def _keyboard_choose_type() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📈 Больше 7  (×2)", callback_data="dice:type:больше"),
            InlineKeyboardButton(text="📉 Меньше 7  (×2)", callback_data="dice:type:меньше"),
        ],
        [
            InlineKeyboardButton(text="🎯 Ровно 7  (×5)",  callback_data="dice:type:ровно"),
        ],
        [InlineKeyboardButton(text="🎰 Казино", callback_data="profile:casino")],
    ])


def _keyboard_bet_amount(choice: str, current: int, balance: int) -> InlineKeyboardMarkup:
    rows = []

    quick_row = []
    for q in QUICK_BETS:
        if current + q <= balance:
            quick_row.append(InlineKeyboardButton(
                text=f"+{q}",
                callback_data=f"dice:amount:{choice}:{current + q}",
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
            callback_data=f"dice:amount:{choice}:{balance // 2}",
        ))
        halves.append(InlineKeyboardButton(
            text=f"Всё ({balance})",
            callback_data=f"dice:amount:{choice}:{balance}",
        ))
    if halves:
        rows.append(halves)

    if current > 0:
        rows.append([InlineKeyboardButton(
            text=f"🗑 Сбросить (текущая: {current})",
            callback_data=f"dice:amount:{choice}:0",
        )])

    label, mult = CHOICE_INFO[choice]
    if current >= 10:
        rows.append([InlineKeyboardButton(
            text=f"🎲 Бросить! Ставка: {current} Ecoins (×{mult})",
            callback_data=f"dice:roll:{choice}:{current}",
        )])

    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="dice:back:types")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _keyboard_result(choice: str, bet: int) -> InlineKeyboardMarkup:
    label, mult = CHOICE_INFO[choice]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"🔄 Снова ({bet} Ecoins, ×{mult})",
            callback_data=f"dice:roll:{choice}:{bet}",
        )],
        [
            InlineKeyboardButton(text="🎲 Другая ставка", callback_data="dice:back:types"),
            InlineKeyboardButton(text="🎰 Казино",        callback_data="profile:casino"),
        ],
    ])


# ---------------------------------------------------------------------------
# Тексты
# ---------------------------------------------------------------------------

def _text_choose_type(balance: int) -> str:
    return (
        f"🎲 *Кости*\n\n"
        f"💰 Баланс: *{balance} Ecoins*\n\n"
        f"Два кубика. Сумма 2–12.\n"
        f"Выбери ставку:"
    )


def _text_choose_amount(choice: str, current: int, balance: int) -> str:
    label, mult = CHOICE_INFO[choice]
    return (
        f"🎲 *Кости* — {label} (×{mult})\n\n"
        f"💰 Баланс: *{balance} Ecoins*\n"
        f"🎯 Текущая ставка: *{current} Ecoins*\n\n"
        f"_Минимум: 10 Ecoins_"
    )


# ---------------------------------------------------------------------------
# Открытие / экран ставки
# ---------------------------------------------------------------------------

async def open_dice(
    user_id: str,
    language: str,
    bot: Bot,
    chat_id: int,
    message_id: int | None = None,
) -> None:
    balance = await get_balance(user_id)
    text = _text_choose_type(balance)
    kb = _keyboard_choose_type()
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


async def show_dice_bet_screen(
    user_id: str,
    choice: str,
    current: int,
    bot: Bot,
    chat_id: int,
    message_id: int,
) -> None:
    balance = await get_balance(user_id)
    text = _text_choose_amount(choice, current, balance)
    kb = _keyboard_bet_amount(choice, current, balance)
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

async def play_dice_inline(
    user_id: str,
    bet: int,
    language: str,
    choice: str,
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
                parse_mode="Markdown", reply_markup=_keyboard_choose_type(),
            )
        except Exception:
            pass
        return

    label, mult = CHOICE_INFO[choice]

    # 2. Скрыть кнопки
    try:
        await bot.edit_message_text(
            f"🎲 *Кости*\n\n{label} — Ставка: *{bet} Ecoins*\n\n_Бросаем кубики..._",
            chat_id=chat_id, message_id=message_id,
            parse_mode="Markdown",
        )
    except Exception:
        pass

    # 3. Два кубика — нативная анимация
    await bot.send_dice(chat_id, emoji="🎲")
    await asyncio.sleep(0.3)
    await bot.send_dice(chat_id, emoji="🎲")

    # 4. Считаем исход
    die1 = random.randint(1, 6)
    die2 = random.randint(1, 6)
    total = die1 + die2

    if choice == "ровно":
        won = total == 7
        push = False
    elif choice == "больше":
        won = total > 7
        push = total == 7
    else:  # меньше
        won = total < 7
        push = total == 7

    payout = 0
    outcome = "loss"

    if push:
        await credit(user_id, bet, "casino_bet")
        outcome = "push"
    elif won:
        payout = bet * mult
        await credit(user_id, payout, "game_win")
        outcome = "win"

    balance = await get_balance(user_id)

    try:
        get_supabase_admin().table("casino_rounds").insert({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "game_type": "dice",
            "amount": bet,
            "payout": payout,
            "house_fee": 0,
            "outcome": outcome,
            "result": {
                "die1": die1, "die2": die2,
                "total": total, "choice": choice,
            },
        }).execute()
    except Exception:
        pass

    # 5. Ждём анимацию (два кубика — чуть дольше)
    await asyncio.sleep(3.5)

    f1 = _dice_face(die1)
    f2 = _dice_face(die2)

    if push:
        outcome_line = f"↩️ *Ничья!* Ровно 7 — ставка возвращена."
    elif won:
        profit = payout - bet
        outcome_line = f"🎉 *Победа!* +{profit} Ecoins (×{mult})"
    else:
        outcome_line = f"😔 *Проигрыш.* −{bet} Ecoins"

    text = (
        f"🎲 *Кости*\n\n"
        f"Твоя ставка: {label}\n"
        f"{f1} + {f2} = *{total}*\n\n"
        f"{outcome_line}\n\n"
        f"💰 Баланс: *{balance} Ecoins*"
    )

    await bot.send_message(
        chat_id, text,
        parse_mode="Markdown",
        reply_markup=_keyboard_result(choice, bet),
    )


# ---------------------------------------------------------------------------
# Текстовая версия (обратная совместимость)
# ---------------------------------------------------------------------------

async def play_dice(user_id: str, bet: int, language: str) -> str:
    success, balance = await debit(user_id, bet, "casino_bet")
    if not success:
        return t(language, "economy.insufficient_funds", balance=balance)

    die1 = random.randint(1, 6)
    die2 = random.randint(1, 6)
    total = die1 + die2
    player_choice = random.choice(["больше", "меньше"])

    if total == 7:
        await credit(user_id, bet, "casino_bet")
        outcome = "push"
        payout = bet
        msg = "🎲 Ровно 7 — ничья! Ставка возвращена."
    elif (player_choice == "больше" and total > 7) or (player_choice == "меньше" and total < 7):
        payout = bet * 2
        outcome = "win"
        await credit(user_id, payout, "game_win")
        msg = t(language, "casino.win", amount=payout - bet)
    else:
        payout = 0
        outcome = "loss"
        msg = t(language, "casino.loss", amount=bet)

    try:
        get_supabase_admin().table("casino_rounds").insert({
            "id": str(uuid.uuid4()), "user_id": user_id, "game_type": "dice",
            "amount": bet, "payout": payout, "house_fee": 0, "outcome": outcome,
            "result": {"die1": die1, "die2": die2, "total": total, "choice": player_choice},
        }).execute()
    except Exception:
        pass

    f1 = _dice_face(die1)
    f2 = _dice_face(die2)
    return (
        f"🎲 *Кости*\n\n"
        f"Твой выбор: *{player_choice} 7*\n"
        f"{f1} + {f2} = *{total}*\n\n"
        f"{msg}"
    )

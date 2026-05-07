<<<<<<< HEAD
"""casino/games/dice.py — Кости. Угадай: больше или меньше 7."""

from __future__ import annotations
import random
import uuid
from infra.db.supabase import get_supabase_admin
from world.economy.wallet import debit, credit
from core.i18n import t


async def play_dice(user_id: str, bet: int, language: str) -> str:
    success, balance = await debit(user_id, bet, "casino_bet")
    if not success:
        return t(language, "economy.insufficient_funds", balance=balance)

    die1 = random.randint(1, 6)
    die2 = random.randint(1, 6)
    total = die1 + die2

    # Игрок ставит на "больше 7" или "меньше 7" — рандомно выбирается
    # (в команде можно передавать выбор, но для кнопочного режима — рандом)
    player_choice = random.choice(["больше", "меньше"])

    if total == 7:
        # Ничья — возврат ставки
        await credit(user_id, bet, "casino_bet")
        outcome = "push"
        msg = f"🎲 Ровно 7 — ничья! Ставка возвращена."
        payout = bet
    elif (player_choice == "больше" and total > 7) or (player_choice == "меньше" and total < 7):
        payout = bet * 2
        outcome = "win"
        await credit(user_id, payout, "game_win")
        msg = t(language, "casino.win", amount=payout - bet)
    else:
        payout = 0
        outcome = "loss"
        msg = t(language, "casino.loss", amount=bet)

    get_supabase_admin().table("casino_rounds").insert({
        "id": str(uuid.uuid4()), "user_id": user_id, "game_type": "dice",
        "amount": bet, "payout": payout, "house_fee": 0, "outcome": outcome,
        "result": {"die1": die1, "die2": die2, "total": total, "choice": player_choice},
    }).execute()

    return (
        f"🎲 *Кости*\n\n"
        f"Твой выбор: *{player_choice} 7*\n"
        f"Выпало: [{die1}] + [{die2}] = *{total}*\n\n"
        f"{msg}"
    )
=======
"""casino/games/dice.py — Кости. Полный inline-flow с send_dice.

UX-флоу:
  1. /кости или кнопка 🎲 → экран выбора ставки (быстрые суммы + своя)
  2. Игрок выбирает сумму → экран Больше 7 / Меньше 7
  3. Telegram анимирует два кубика (send_dice 🎲🎲) → результат

Логика:
  • total > 7  → выигрыш ×2
  • total < 7  → проигрыш
  • total == 7 → ничья, ставка возвращается

Вероятности (честные):
  P(>7) = 15/36 ≈ 41.7%
  P(<7) = 15/36 ≈ 41.7%
  P(=7) =  6/36 ≈ 16.7%
"""

from __future__ import annotations

import asyncio
import uuid

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from infra.db.supabase import get_supabase_admin
from world.economy.wallet import debit, credit, get_balance
from core.i18n import t

# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------

QUICK_BETS = [50, 100, 500, 1_000, 5_000, 10_000]

DICE_FACE = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}

# ---------------------------------------------------------------------------
# Клавиатуры
# ---------------------------------------------------------------------------

def _kb_bet(balance: int) -> InlineKeyboardMarkup:
    """Экран выбора суммы ставки — быстрые кнопки + своя сумма."""
    rows = []
    row = []
    for b in QUICK_BETS:
        row.append(
            InlineKeyboardButton(
                text=f"{b:,} 🪙" if b <= balance else f"╌{b:,}╌",
                callback_data=f"dice:bet:{b}" if b <= balance else "dice:noop",
            )
        )
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append([
        InlineKeyboardButton(text="✏️ Своя сумма", callback_data="dice:bet:custom"),
    ])
    rows.append([
        InlineKeyboardButton(text="🔙 В казино", callback_data="casino:back"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _kb_choice(bet: int) -> InlineKeyboardMarkup:
    """Экран выбора Больше / Меньше 7."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📈 Больше 7  (×2)",
                callback_data=f"dice:choice:high:{bet}",
            ),
            InlineKeyboardButton(
                text="📉 Меньше 7  (×2)",
                callback_data=f"dice:choice:low:{bet}",
            ),
        ],
        [
            InlineKeyboardButton(text="🔙 Изменить ставку", callback_data="dice:start"),
        ],
    ])


def _kb_again() -> InlineKeyboardMarkup:
    """Кнопки после результата."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎲 Играть снова", callback_data="dice:start"),
            InlineKeyboardButton(text="🎰 В казино",     callback_data="casino:back"),
        ],
    ])


# ---------------------------------------------------------------------------
# Экраны
# ---------------------------------------------------------------------------

async def open_dice(
    user_id: str,
    language: str,
    bot: Bot,
    chat_id: int,
    message_id: int | None = None,
) -> None:
    """Открыть экран выбора ставки (старт игры или «играть снова»)."""
    balance = await get_balance(user_id)
    text = (
        "🎲 *Кости*\n\n"
        f"💰 Баланс: *{balance:,} Ecoins*\n\n"
        "Угадай сумму двух кубиков:\n"
        "• *Больше 7* — выигрыш ×2\n"
        "• *Меньше 7* — проигрыш\n"
        "• *Ровно 7* — ничья, ставка вернётся\n\n"
        "Выбери сумму ставки:"
    )
    kb = _kb_bet(balance)

    if message_id:
        await bot.edit_message_text(
            text=text,
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="Markdown",
            reply_markup=kb,
        )
    else:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=kb,
        )


async def show_choice_screen(
    user_id: str,
    bet: int,
    language: str,
    bot: Bot,
    chat_id: int,
    message_id: int,
) -> None:
    """Показать экран Больше / Меньше после выбора суммы."""
    balance = await get_balance(user_id)
    text = (
        "🎲 *Кости*\n\n"
        f"💰 Баланс: *{balance:,} Ecoins*\n"
        f"🪙 Ставка: *{bet:,} Ecoins*\n\n"
        "Твой прогноз — сумма двух кубиков будет…"
    )
    await bot.edit_message_text(
        text=text,
        chat_id=chat_id,
        message_id=message_id,
        parse_mode="Markdown",
        reply_markup=_kb_choice(bet),
    )


# ---------------------------------------------------------------------------
# Основная логика
# ---------------------------------------------------------------------------

async def play_dice_inline(
    user_id: str,
    bet: int,
    choice: str,        # "high" | "low"
    language: str,
    bot: Bot,
    chat_id: int,
    message_id: int,
) -> None:
    """
    Списывает ставку, кидает два send_dice, ждёт анимацию,
    считает результат и редактирует сообщение.
    """
    # 1. Списываем ставку
    success, balance = await debit(user_id, bet, "casino_bet")
    if not success:
        await bot.edit_message_text(
            text=t(language, "economy.insufficient_funds", balance=balance),
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="Markdown",
        )
        return

    # 2. Показываем «кидаю...»
    await bot.edit_message_text(
        text="🎲 *Кидаю кубики...*",
        chat_id=chat_id,
        message_id=message_id,
        parse_mode="Markdown",
    )

    # 3. Два send_dice — Telegram анимирует сам
    msg1 = await bot.send_dice(chat_id=chat_id, emoji="🎲")
    await asyncio.sleep(0.3)
    msg2 = await bot.send_dice(chat_id=chat_id, emoji="🎲")

    die1 = msg1.dice.value
    die2 = msg2.dice.value
    total = die1 + die2

    # 4. Ждём завершения анимации Telegram (~3 сек)
    await asyncio.sleep(3.2)

    # 5. Определяем исход
    choice_label = "Больше 7 📈" if choice == "high" else "Меньше 7 📉"

    if total == 7:
        await credit(user_id, bet, "casino_push")
        outcome = "push"
        payout = bet
        icon = "🟡"
        result_line = f"*Ровно 7 — ничья!* Ставка возвращена."
    elif (choice == "high" and total > 7) or (choice == "low" and total < 7):
        payout = bet * 2
        await credit(user_id, payout, "game_win")
        outcome = "win"
        icon = "🟢"
        result_line = f"*Победа!* +{bet:,} Ecoins"
    else:
        payout = 0
        outcome = "loss"
        icon = "🔴"
        result_line = f"*Проигрыш.* −{bet:,} Ecoins"

    balance_after = await get_balance(user_id)
    d1 = DICE_FACE[die1]
    d2 = DICE_FACE[die2]

    # 6. Редактируем сообщение с итогом
    await bot.edit_message_text(
        text=(
            f"🎲 *Кости — результат*\n\n"
            f"Твой выбор: *{choice_label}*\n"
            f"Выпало: {d1} + {d2} = *{total}*\n\n"
            f"{icon} {result_line}\n\n"
            f"💰 Баланс: *{balance_after:,} Ecoins*"
        ),
        chat_id=chat_id,
        message_id=message_id,
        parse_mode="Markdown",
        reply_markup=_kb_again(),
    )

    # 7. Логируем раунд в БД
    get_supabase_admin().table("casino_rounds").insert({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "game_type": "dice",
        "amount": bet,
        "payout": payout,
        "house_fee": 0,
        "outcome": outcome,
        "result": {
            "die1": die1,
            "die2": die2,
            "total": total,
            "choice": choice,
        },
    }).execute()
>>>>>>> 463e2dc762cb529f9c4cb051846d8c19c1987331

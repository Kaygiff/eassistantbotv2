"""casino/games/slots.py — Игровые автоматы.

send_dice(🎰) используется только для нативной анимации Telegram.
Его результат игнорируется — исход считается по нашей логике
с взвешенными символами и контролируемым RTP ~92%.
"""

from __future__ import annotations

import asyncio
import random
import uuid

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from infra.db.supabase import get_supabase_admin
from world.economy.wallet import credit, debit, get_balance
from core.i18n import t

# ---------------------------------------------------------------------------
# Символы и веса (контроль RTP)
# ---------------------------------------------------------------------------

SYMBOL_WEIGHTS: list[tuple[str, int]] = [
    ("🍒", 30),
    ("🍋", 25),
    ("🍊", 20),
    ("🍇", 15),
    ("💎",  6),
    ("7️⃣",  2),
    ("⭐",   5),   # Wild — заменяет любой символ
]

SYMBOLS  = [s for s, _ in SYMBOL_WEIGHTS]
WEIGHTS  = [w for _, w in SYMBOL_WEIGHTS]
WILD     = "⭐"

PAYOUTS_3: dict[str, float] = {
    "7️⃣": 50.0,
    "💎": 20.0,
    "🍇":  8.0,
    "🍊":  5.0,
    "🍋":  4.0,
    "🍒":  3.0,
    "⭐":  15.0,
}

PAYOUTS_2: dict[str, float] = {
    "7️⃣":  3.0,
    "💎":   2.0,
    "🍇":   1.5,
    "🍊":   1.5,
    "🍋":   1.5,
    "🍒":   1.5,
}

HOUSE_FEE_PERCENT  = 3
STREAK_BOOST_AFTER = 5   # после N проигрышей подряд — лёгкий буст


# ---------------------------------------------------------------------------
# Логика спина
# ---------------------------------------------------------------------------

def _spin(boost: bool = False) -> list[str]:
    if boost:
        w = [wt + (15 if s in ("7️⃣", "💎", "🍇") else 0) for s, wt in SYMBOL_WEIGHTS]
    else:
        w = WEIGHTS
    return random.choices(SYMBOLS, weights=w, k=3)


def _resolve_wilds(reels: list[str]) -> list[str]:
    non_wild = [s for s in reels if s != WILD]
    if not non_wild:
        return reels
    base = max(set(non_wild), key=non_wild.count)
    return [base if s == WILD else s for s in reels]


def _calculate(reels: list[str]) -> tuple[float, str]:
    """Возвращает (multiplier, win_type)."""
    resolved = _resolve_wilds(reels)

    # Тройка
    if resolved[0] == resolved[1] == resolved[2]:
        sym = resolved[0]
        mult = PAYOUTS_3.get(sym, 2.0)
        return mult, "jackpot" if sym == "7️⃣" else "triple"

    # Пара (первые два или последние два)
    for i in range(2):
        if resolved[i] == resolved[i + 1]:
            sym = resolved[i]
            return PAYOUTS_2.get(sym, 1.5), "double"

    return 0.0, "loss"


def _get_loss_streak(user_id: str) -> int:
    try:
        rows = (
            get_supabase_admin()
            .table("casino_rounds")
            .select("outcome")
            .eq("user_id", user_id)
            .eq("game_type", "slots")
            .order("created_at", desc=True)
            .limit(STREAK_BOOST_AFTER)
            .execute()
            .data or []
        )
        streak = 0
        for r in rows:
            if r["outcome"] == "loss":
                streak += 1
            else:
                break
        return streak
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Текст результата и клавиатура
# ---------------------------------------------------------------------------

def _result_text(
    reels: list[str],
    win_type: str,
    multiplier: float,
    payout: int,
    bet: int,
    balance: int,
) -> str:
    reel_str = " · ".join(reels)

    if win_type == "jackpot":
        line = f"🎆 *ДЖЕКПОТ!*  × {int(multiplier)} → *+{payout} Ecoins*"
    elif win_type == "triple":
        line = f"✨ *Тройка!*  × {int(multiplier)} → *+{payout} Ecoins*"
    elif win_type == "double":
        line = f"👍 *Пара!*  × {multiplier} → *+{payout} Ecoins*"
    else:
        line = f"😔 Не повезло  *−{bet} Ecoins*"

    return (
        f"🎰 *Слоты*\n\n"
        f"{reel_str}\n\n"
        f"{line}\n\n"
        f"💰 Баланс: *{balance} Ecoins*"
    )


def _keyboard(bet: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"🔄 Крутить снова ({bet} Ecoins)",
            callback_data=f"slots:spin:{bet}",
        )],
        [
            InlineKeyboardButton(text="📊 Выплаты", callback_data=f"slots:paytable:{bet}"),
            InlineKeyboardButton(text="🎰 Казино",  callback_data="profile:casino"),
        ],
    ])


def paytable_text() -> str:
    return (
        "📊 *Таблица выплат*\n\n"
        "```\n"
        "7️⃣ 7️⃣ 7️⃣  →  × 50   ДЖЕКПОТ\n"
        "💎 💎 💎  →  × 20\n"
        "⭐ ⭐ ⭐  →  × 15   Wild × 3\n"
        "🍇 🍇 🍇  →  × 8\n"
        "🍊 🍊 🍊  →  × 5\n"
        "🍋 🍋 🍋  →  × 4\n"
        "🍒 🍒 🍒  →  × 3\n"
        "──────────────────\n"
        "7️⃣ 7️⃣  ?  →  × 3    пара\n"
        "💎 💎  ?  →  × 2    пара\n"
        "любая пара →  × 1.5\n"
        "──────────────────\n"
        "⭐  =  Wild (замена)\n"
        "```\n\n"
        "_RTP ≈ 92%  |  Комиссия: 3%_"
    )


# ---------------------------------------------------------------------------
# Основная функция
# ---------------------------------------------------------------------------

async def play_slots(
    user_id: str,
    bet: int,
    language: str,
    bot: Bot,
    chat_id: int,
    is_freespin: bool = False,
    freespins_left: int = 0,
) -> None:
    """
    1. Списывает ставку
    2. Отправляет send_dice(🎰) — Telegram показывает анимацию
    3. Параллельно считает исход по своей логике
    4. Ждёт окончания анимации (~3 сек)
    5. Отправляет результат с кнопками
    """
    if not is_freespin:
        success, balance = await debit(user_id, bet, "casino_bet")
        if not success:
            await bot.send_message(
                chat_id,
                t(language, "economy.insufficient_funds", balance=balance),
                parse_mode="Markdown",
            )
            return

    # Отправляем анимацию (результат dice игнорируем)
    await bot.send_dice(chat_id, emoji="🎰")

    # Считаем исход пока играет анимация
    streak = _get_loss_streak(user_id)
    reels = _spin(boost=streak >= STREAK_BOOST_AFTER)
    multiplier, win_type = _calculate(reels)

    house_fee = int(bet * HOUSE_FEE_PERCENT / 100) if multiplier > 0 else 0
    if multiplier > 0:
        payout = max(0, int(bet * multiplier) - house_fee)
        outcome = "win"
        await credit(user_id, payout, "game_win")
    else:
        payout = 0
        outcome = "loss"

    balance = await get_balance(user_id)

    try:
        get_supabase_admin().table("casino_rounds").insert({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "game_type": "slots",
            "amount": bet if not is_freespin else 0,
            "payout": payout,
            "house_fee": house_fee,
            "outcome": outcome,
            "result": {
                "reels": reels,
                "multiplier": multiplier,
                "win_type": win_type,
                "streak_boost": streak >= STREAK_BOOST_AFTER,
                "is_freespin": is_freespin,
            },
        }).execute()
    except Exception:
        pass

    # Ждём окончания анимации
    await asyncio.sleep(3)

    text = _result_text(reels, win_type, multiplier, payout, bet, balance)
    await bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=_keyboard(bet))

    if is_freespin and freespins_left > 1:
        await asyncio.sleep(1.5)
        await play_slots(
            user_id=user_id, bet=bet, language=language,
            bot=bot, chat_id=chat_id,
            is_freespin=True, freespins_left=freespins_left - 1,
        )

"""casino/games/wheel.py — Колесо фортуны.

UX:
  1. Экран выбора суммы ставки (быстрые кнопки + ½ + Всё)
  2. send_dice(🎡) — нативная анимация Telegram (результат игнорируется)
  3. Исход считается по нашей взвешенной логике
  4. Результат с таблицей секторов, кнопки «Снова» и «Казино»

RTP ≈ 91%
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

# Сектора: (множитель, вес, эмодзи, название)
SECTORS = [
    (0,    30, "💀", "Пусто"),
    (1.5,  25, "🟡", "×1.5"),
    (2.0,  20, "🟠", "×2"),
    (3.0,  12, "🔵", "×3"),
    (5.0,   8, "🟣", "×5"),
    (10.0,  4, "🔴", "×10"),
    (25.0,  1, "⭐", "×25"),
]

QUICK_BETS = [50, 100, 500, 1_000, 5_000]


def _spin() -> tuple[float, str, str]:
    """Возвращает (multiplier, emoji, label)."""
    population = [(m, e, l) for m, w, e, l in SECTORS for _ in range(w)]
    return random.choice(population)


def _paytable_text() -> str:
    lines = ["🎡 *Таблица секторов*\n", "```"]
    for mult, w, icon, label in SECTORS:
        chance = round(w / sum(s[1] for s in SECTORS) * 100, 1)
        lines.append(f"{icon}  {label:<6}  шанс {chance}%")
    lines.append("```\n_RTP ≈ 91%_")
    return "\n".join(lines)


def _render_wheel(winner_icon: str | None = None) -> str:
    """Показывает все сектора, выделяет победный."""
    parts = []
    for _, _, icon, label in SECTORS:
        if winner_icon and icon == winner_icon:
            parts.append(f"►{icon}◄")
        else:
            parts.append(icon)
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Клавиатуры
# ---------------------------------------------------------------------------

def _keyboard_bet_amount(current: int, balance: int) -> InlineKeyboardMarkup:
    rows = []

    quick_row = []
    for q in QUICK_BETS:
        if current + q <= balance:
            quick_row.append(InlineKeyboardButton(
                text=f"+{q}",
                callback_data=f"wheel:amount:{current + q}",
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
            callback_data=f"wheel:amount:{balance // 2}",
        ))
        halves.append(InlineKeyboardButton(
            text=f"Всё ({balance})",
            callback_data=f"wheel:amount:{balance}",
        ))
    if halves:
        rows.append(halves)

    if current > 0:
        rows.append([InlineKeyboardButton(
            text=f"🗑 Сбросить (текущая: {current})",
            callback_data="wheel:amount:0",
        )])

    if current >= 10:
        rows.append([InlineKeyboardButton(
            text=f"🎡 Крутить! Ставка: {current} Ecoins",
            callback_data=f"wheel:spin:{current}",
        )])

    rows.append([
        InlineKeyboardButton(text="📊 Сектора", callback_data="wheel:paytable"),
        InlineKeyboardButton(text="🎰 Казино",  callback_data="profile:casino"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _keyboard_result(bet: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"🔄 Снова ({bet} Ecoins)",
            callback_data=f"wheel:spin:{bet}",
        )],
        [
            InlineKeyboardButton(text="💰 Изменить ставку", callback_data="wheel:back:bet"),
            InlineKeyboardButton(text="🎰 Казино",          callback_data="profile:casino"),
        ],
    ])


def _keyboard_paytable(bet: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"wheel:back:{bet}")],
    ])


# ---------------------------------------------------------------------------
# Тексты
# ---------------------------------------------------------------------------

def _text_bet_screen(current: int, balance: int) -> str:
    wheel_str = _render_wheel()
    return (
        f"🎡 *Колесо фортуны*\n\n"
        f"{wheel_str}\n\n"
        f"💰 Баланс: *{balance} Ecoins*\n"
        f"🎯 Текущая ставка: *{current} Ecoins*\n\n"
        f"_Минимум: 10 Ecoins_"
    )


# ---------------------------------------------------------------------------
# Открытие
# ---------------------------------------------------------------------------

async def open_wheel(
    user_id: str,
    language: str,
    bot: Bot,
    chat_id: int,
    message_id: int | None = None,
    initial_bet: int = 0,
) -> None:
    balance = await get_balance(user_id)
    text = _text_bet_screen(initial_bet, balance)
    kb = _keyboard_bet_amount(initial_bet, balance)
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


async def show_wheel_bet_screen(
    user_id: str,
    current: int,
    bot: Bot,
    chat_id: int,
    message_id: int,
) -> None:
    balance = await get_balance(user_id)
    text = _text_bet_screen(current, balance)
    kb = _keyboard_bet_amount(current, balance)
    try:
        await bot.edit_message_text(
            text, chat_id=chat_id, message_id=message_id,
            parse_mode="Markdown", reply_markup=kb,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Спин
# ---------------------------------------------------------------------------

async def play_wheel_inline(
    user_id: str,
    bet: int,
    language: str,
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
                parse_mode="Markdown",
                reply_markup=_keyboard_bet_amount(0, balance),
            )
        except Exception:
            pass
        return

    # 2. Удаляем старое сообщение со ставкой, шлём "Крутим..."
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass

    wheel_str = _render_wheel()
    spinning_msg = await bot.send_message(
        chat_id,
        f"🎡 *Колесо фортуны*\n\n{wheel_str}\n\n_Крутим колесо..._",
        parse_mode="Markdown",
    )

    # 3. Текстовая анимация вращения
    frames = [
        "💀 🟡 🟠 🔵 🟣 🔴 ⭐\n\n_Крутим колесо..._",
        "⭐ 💀 🟡 🟠 🔵 🟣 🔴\n\n_Крутим колесо..._",
        "🔴 ⭐ 💀 🟡 🟠 🔵 🟣\n\n_Крутим колесо..._",
        "🟣 🔴 ⭐ 💀 🟡 🟠 🔵\n\n_Вот-вот..._",
    ]
    for frame in frames:
        try:
            await bot.edit_message_text(
                f"🎡 *Колесо фортуны*\n\n{frame}",
                chat_id=chat_id, message_id=spinning_msg.message_id,
                parse_mode="Markdown",
            )
        except Exception:
            pass
        await asyncio.sleep(0.9)


    # 4. Считаем исход
    multiplier, winner_icon, winner_label = _spin()
    payout = int(bet * multiplier) if multiplier > 0 else 0
    outcome = "win" if payout > 0 else "loss"

    if payout > 0:
        await credit(user_id, payout, "game_win")

    balance = await get_balance(user_id)

    try:
        get_supabase_admin().table("casino_rounds").insert({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "game_type": "wheel",
            "amount": bet,
            "payout": payout,
            "house_fee": 0,
            "outcome": outcome,
            "result": {"multiplier": multiplier, "sector": winner_icon},
        }).execute()
    except Exception:
        pass

    # 5. Показываем результат в том же сообщении
    wheel_result = _render_wheel(winner_icon)

    if payout > 0:
        profit = payout - bet
        outcome_line = f"🎉 *{winner_label}!* +{profit} Ecoins"
    else:
        outcome_line = f"💀 *Пусто!* −{bet} Ecoins"

    text = (
        f"🎡 *Колесо фортуны*\n\n"
        f"{wheel_result}\n\n"
        f"Выпало: {winner_icon} *{winner_label}*\n\n"
        f"{outcome_line}\n\n"
        f"💰 Баланс: *{balance} Ecoins*"
    )

    try:
        await bot.edit_message_text(
            text,
            chat_id=chat_id, message_id=spinning_msg.message_id,
            parse_mode="Markdown",
            reply_markup=_keyboard_result(bet),
        )
    except Exception:
        await bot.send_message(
            chat_id, text,
            parse_mode="Markdown",
            reply_markup=_keyboard_result(bet),
        )


# ---------------------------------------------------------------------------
# Текстовая версия (обратная совместимость)
# ---------------------------------------------------------------------------

async def play_wheel(user_id: str, bet: int, language: str) -> str:
    success, balance = await debit(user_id, bet, "casino_bet")
    if not success:
        return t(language, "economy.insufficient_funds", balance=balance)

    multiplier, icon, label = _spin()
    payout = int(bet * multiplier) if multiplier > 0 else 0
    outcome = "win" if payout > 0 else "loss"

    wheel_display = _render_wheel(icon)

    if payout > 0:
        await credit(user_id, payout, "game_win")
        msg = t(language, "casino.win", amount=payout - bet)
    else:
        msg = t(language, "casino.loss", amount=bet)

    try:
        get_supabase_admin().table("casino_rounds").insert({
            "id": str(uuid.uuid4()), "user_id": user_id, "game_type": "wheel",
            "amount": bet, "payout": payout, "house_fee": 0, "outcome": outcome,
            "result": {"multiplier": multiplier, "sector": icon},
        }).execute()
    except Exception:
        pass

    return (
        f"🎡 *Колесо фортуны*\n\n"
        f"{wheel_display}\n\n"
        f"Выпало: {icon} *{label}*\n\n"
        f"{msg}"
    )

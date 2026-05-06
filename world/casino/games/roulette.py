"""casino/games/roulette.py — Европейская рулетка.

Полный набор ставок:
  • Красное / Чёрное           × 2
  • Чётное / Нечётное          × 2
  • 1-18 (Manque) / 19-36 (Passe) × 2
  • Дюжина (1-12, 13-24, 25-36)   × 3
  • Колонка (1я, 2я, 3я)          × 3
  • Число напрямую (0-36)          × 36

UX: полностью inline-кнопки (кнопки ставки, суммы, крутить, история, назад).
    Анимация: редактирование сообщения с кадрами колеса.
    Команда /рулетка тоже работает (открывает меню).
"""

from __future__ import annotations

import asyncio
import random
import uuid
from typing import Optional

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from infra.db.supabase import get_supabase_admin
from world.economy.wallet import debit, credit, get_balance
from core.i18n import t

# ---------------------------------------------------------------------------
# Константы рулетки
# ---------------------------------------------------------------------------

REDS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

# Порядок чисел на европейском колесе (для анимации)
WHEEL_ORDER = [
    0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36,
    11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9,
    22, 18, 29, 7, 28, 12, 35, 3, 26,
]

# Кадры анимации колеса
WHEEL_FRAMES = [
    "🎡 ╔══════════╗\n   ║  · · · ·  ║\n   ╚══════════╝\n   _Колесо крутится..._",
    "🎡 ╔══════════╗\n   ║ · · · · ·║\n   ╚══════════╝\n   _Колесо крутится..._",
    "🎡 ╔══════════╗\n   ║· · · · · ║\n   ╚══════════╝\n   _Замедляется..._",
    "🎡 ╔══════════╗\n   ║ · · · ·  ║\n   ╚══════════╝\n   _Почти..._",
]

# Типы ставок: (label, bet_key, multiplier, description)
BET_TYPES = {
    # Внешние ставки
    "red":     ("🔴 Красное",      2,  "Все красные числа"),
    "black":   ("⚫ Чёрное",       2,  "Все чёрные числа"),
    "even":    ("2️⃣ Чётное",       2,  "Все чётные числа (кроме 0)"),
    "odd":     ("1️⃣ Нечётное",     2,  "Все нечётные числа"),
    "low":     ("📉 1-18",         2,  "Числа от 1 до 18"),
    "high":    ("📈 19-36",        2,  "Числа от 19 до 36"),
    "dozen1":  ("1️⃣2️⃣ Дюжина 1-12",   3,  "Числа от 1 до 12"),
    "dozen2":  ("2️⃣3️⃣ Дюжина 13-24",  3,  "Числа от 13 до 24"),
    "dozen3":  ("3️⃣4️⃣ Дюжина 25-36",  3,  "Числа от 25 до 36"),
    "col1":    ("1️⃣ Колонка 1",    3,  "1,4,7,10,13,16,19,22,25,28,31,34"),
    "col2":    ("2️⃣ Колонка 2",    3,  "2,5,8,11,14,17,20,23,26,29,32,35"),
    "col3":    ("3️⃣ Колонка 3",    3,  "3,6,9,12,15,18,21,24,27,30,33,36"),
    # Прямая ставка на число — обрабатывается отдельно (number:N)
}

QUICK_BETS = [50, 100, 500, 1_000, 5_000]


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------

def _number_color(n: int) -> str:
    if n == 0:
        return "🟢"
    return "🔴" if n in REDS else "⚫"


def _check_win(number: int, bet_type: str) -> bool:
    """Проверяет, выиграла ли ставка."""
    if bet_type == "red":
        return number in REDS
    if bet_type == "black":
        return number not in REDS and number != 0
    if bet_type == "even":
        return number != 0 and number % 2 == 0
    if bet_type == "odd":
        return number % 2 == 1
    if bet_type == "low":
        return 1 <= number <= 18
    if bet_type == "high":
        return 19 <= number <= 36
    if bet_type == "dozen1":
        return 1 <= number <= 12
    if bet_type == "dozen2":
        return 13 <= number <= 24
    if bet_type == "dozen3":
        return 25 <= number <= 36
    if bet_type == "col1":
        return number != 0 and number % 3 == 1
    if bet_type == "col2":
        return number != 0 and number % 3 == 2
    if bet_type == "col3":
        return number != 0 and number % 3 == 0
    if bet_type.startswith("number:"):
        return number == int(bet_type.split(":")[1])
    return False


def _get_multiplier(bet_type: str) -> int:
    if bet_type.startswith("number:"):
        return 36
    info = BET_TYPES.get(bet_type)
    return info[1] if info else 2


def _bet_label(bet_type: str) -> str:
    if bet_type.startswith("number:"):
        n = bet_type.split(":")[1]
        return f"🔢 Число {n}"
    info = BET_TYPES.get(bet_type)
    return info[0] if info else bet_type


# ---------------------------------------------------------------------------
# Визуализация стола (мини-таблица)
# ---------------------------------------------------------------------------

def _render_board(number: int) -> str:
    """Рисует мини-таблицу чисел рулетки с выделением выпавшего."""
    rows = [
        [3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36],
        [2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35],
        [1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34],
    ]
    lines = []
    for row in rows:
        cells = []
        for n in row:
            if n == number:
                cells.append(f"[{n:02d}]")
            else:
                color = "🔴" if n in REDS else "⚫"
                cells.append(f" {color} ")
        lines.append(" ".join(cells))
    # Нулевой сектор
    zero = "►0◄" if number == 0 else " 0 "
    return f"`{zero}`\n" + "\n".join(f"`{l}`" for l in lines)


def _get_last_numbers(user_id: str, limit: int = 7) -> list[dict]:
    """Возвращает последние числа рулетки этого пользователя."""
    try:
        rows = (
            get_supabase_admin()
            .table("casino_rounds")
            .select("result,outcome")
            .eq("user_id", user_id)
            .eq("game_type", "roulette")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
            .data or []
        )
        out = []
        for r in rows:
            res = r.get("result", {})
            if isinstance(res, dict) and "number" in res:
                out.append({"number": res["number"], "outcome": r["outcome"]})
        return list(reversed(out))
    except Exception:
        return []


def _render_history(history: list[dict]) -> str:
    if not history:
        return ""
    parts = []
    for h in history:
        n = h["number"]
        color = _number_color(n)
        parts.append(f"{color}{n}")
    return "🕐 История: " + "  ".join(parts)


# ---------------------------------------------------------------------------
# Клавиатуры
# ---------------------------------------------------------------------------

def _keyboard_bet_type() -> InlineKeyboardMarkup:
    """Главный экран — выбор типа ставки."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔴 Красное", callback_data="rlt:type:red"),
            InlineKeyboardButton(text="⚫ Чёрное",  callback_data="rlt:type:black"),
        ],
        [
            InlineKeyboardButton(text="2️⃣ Чётное",   callback_data="rlt:type:even"),
            InlineKeyboardButton(text="1️⃣ Нечётное", callback_data="rlt:type:odd"),
        ],
        [
            InlineKeyboardButton(text="📉 1-18",  callback_data="rlt:type:low"),
            InlineKeyboardButton(text="📈 19-36", callback_data="rlt:type:high"),
        ],
        [
            InlineKeyboardButton(text="1-12 (×3)",   callback_data="rlt:type:dozen1"),
            InlineKeyboardButton(text="13-24 (×3)",  callback_data="rlt:type:dozen2"),
            InlineKeyboardButton(text="25-36 (×3)",  callback_data="rlt:type:dozen3"),
        ],
        [
            InlineKeyboardButton(text="Колонка 1 (×3)", callback_data="rlt:type:col1"),
            InlineKeyboardButton(text="Колонка 2 (×3)", callback_data="rlt:type:col2"),
            InlineKeyboardButton(text="Колонка 3 (×3)", callback_data="rlt:type:col3"),
        ],
        [
            InlineKeyboardButton(text="🔢 Число (×36)", callback_data="rlt:type:number"),
        ],
        [
            InlineKeyboardButton(text="🎰 Казино", callback_data="profile:casino"),
        ],
    ])


def _keyboard_number_row(row: int) -> InlineKeyboardMarkup:
    """Выбор числа 0-36 разбитый по рядам (0-9, 10-19, 20-29, 30-36)."""
    ranges = [(0, 9), (10, 19), (20, 29), (30, 36)]
    start, end = ranges[row]
    numbers = list(range(start, end + 1))
    # Разбить по 5 кнопок в ряду
    rows_kb = []
    chunk = []
    for i, n in enumerate(numbers):
        color = _number_color(n)
        chunk.append(InlineKeyboardButton(
            text=f"{color}{n}",
            callback_data=f"rlt:num:{n}",
        ))
        if len(chunk) == 5 or i == len(numbers) - 1:
            rows_kb.append(chunk)
            chunk = []
    # Навигация по страницам
    nav = []
    if row > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"rlt:numpage:{row - 1}"))
    nav.append(InlineKeyboardButton(text=f"{start}-{end}", callback_data="rlt:noop"))
    if row < 3:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"rlt:numpage:{row + 1}"))
    rows_kb.append(nav)
    rows_kb.append([InlineKeyboardButton(text="◀️ Назад к типам", callback_data="rlt:back:types")])
    return InlineKeyboardMarkup(inline_keyboard=rows_kb)


def _keyboard_bet_amount(bet_type: str, current: int, balance: int) -> InlineKeyboardMarkup:
    """Экран выбора суммы ставки."""
    rows_kb = []

    # Быстрые кнопки +X
    quick_row = []
    for q in QUICK_BETS:
        if current + q <= balance:
            quick_row.append(InlineKeyboardButton(
                text=f"+{q}",
                callback_data=f"rlt:amount:{bet_type}:{current + q}",
            ))
        if len(quick_row) == 5:
            rows_kb.append(quick_row)
            quick_row = []
    if quick_row:
        rows_kb.append(quick_row)

    # Всё / Половина
    halves = []
    if balance > 0:
        halves.append(InlineKeyboardButton(
            text=f"½ ({balance // 2})",
            callback_data=f"rlt:amount:{bet_type}:{balance // 2}",
        ))
        halves.append(InlineKeyboardButton(
            text=f"Всё ({balance})",
            callback_data=f"rlt:amount:{bet_type}:{balance}",
        ))
    if halves:
        rows_kb.append(halves)

    # Сброс суммы
    if current > 0:
        rows_kb.append([InlineKeyboardButton(
            text=f"🗑 Сбросить (текущая: {current})",
            callback_data=f"rlt:amount:{bet_type}:0",
        )])

    # Крутить
    if current >= 10:
        mult = _get_multiplier(bet_type)
        rows_kb.append([InlineKeyboardButton(
            text=f"🎡 Крутить! Ставка: {current} Ecoins (×{mult})",
            callback_data=f"rlt:spin:{bet_type}:{current}",
        )])

    # Ввести своё число
    rows_kb.append([InlineKeyboardButton(
        text="✏️ Ввести своё число",
        callback_data=f"rlt:custom:{bet_type}",
    )])

    rows_kb.append([InlineKeyboardButton(text="◀️ Назад", callback_data="rlt:back:types")])

    return InlineKeyboardMarkup(inline_keyboard=rows_kb)


def _keyboard_result(bet_type: str, bet: int) -> InlineKeyboardMarkup:
    """Клавиатура после результата."""
    mult = _get_multiplier(bet_type)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"🔄 Снова ({bet} Ecoins, ×{mult})",
            callback_data=f"rlt:spin:{bet_type}:{bet}",
        )],
        [
            InlineKeyboardButton(text="🎡 Другая ставка", callback_data="rlt:back:types"),
            InlineKeyboardButton(text="🎰 Казино",        callback_data="profile:casino"),
        ],
    ])


# ---------------------------------------------------------------------------
# Тексты экранов
# ---------------------------------------------------------------------------

def _text_choose_type(balance: int) -> str:
    return (
        f"🎡 *Рулетка*\n\n"
        f"💰 Баланс: *{balance} Ecoins*\n\n"
        f"Выбери тип ставки:"
    )


def _text_choose_amount(bet_type: str, current: int, balance: int) -> str:
    label = _bet_label(bet_type)
    mult = _get_multiplier(bet_type)
    lines = [
        f"🎡 *Рулетка* — {label} (×{mult})\n",
        f"💰 Баланс: *{balance} Ecoins*",
        f"🎯 Текущая ставка: *{current} Ecoins*\n",
        "_Добавь сумму кнопками или введи своё число через кнопку ниже._",
        f"_Минимум: 10 Ecoins_",
    ]
    return "\n".join(lines)


def _text_result(
    number: int,
    bet_type: str,
    bet: int,
    won: bool,
    payout: int,
    balance: int,
    history: list[dict],
) -> str:
    color = _number_color(number)
    label = _bet_label(bet_type)
    mult = _get_multiplier(bet_type)
    board = _render_board(number)
    hist = _render_history(history)

    if won:
        profit = payout - bet
        outcome_line = f"🎉 *Победа!* +{profit} Ecoins (×{mult})"
    else:
        outcome_line = f"😔 *Проигрыш.* -{bet} Ecoins"

    lines = [
        f"🎡 *Рулетка*\n",
        f"Выпало: {color} *{number}*",
        f"Твоя ставка: {label}\n",
        board,
        f"\n{outcome_line}",
        f"💰 Баланс: *{balance} Ecoins*",
    ]
    if hist:
        lines.append(f"\n{hist}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Точка входа — открытие рулетки (из кнопки казино или /рулетка)
# ---------------------------------------------------------------------------

async def open_roulette(
    user_id: str,
    language: str,
    bot: Bot,
    chat_id: int,
    message_id: Optional[int] = None,
) -> None:
    """Показывает экран выбора типа ставки."""
    balance = await get_balance(user_id)
    text = _text_choose_type(balance)
    kb = _keyboard_bet_type()

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


async def show_bet_amount_screen(
    user_id: str,
    bet_type: str,
    current_amount: int,
    bot: Bot,
    chat_id: int,
    message_id: int,
) -> None:
    """Редактирует сообщение — экран выбора суммы."""
    balance = await get_balance(user_id)
    text = _text_choose_amount(bet_type, current_amount, balance)
    kb = _keyboard_bet_amount(bet_type, current_amount, balance)
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

async def play_roulette_inline(
    user_id: str,
    bet: int,
    language: str,
    bet_type: str,
    bot: Bot,
    chat_id: int,
    message_id: int,
) -> None:
    """Запускает спин и редактирует сообщение через анимацию."""

    # 1. Списать ставку
    success, balance = await debit(user_id, bet, "casino_bet")
    if not success:
        try:
            await bot.edit_message_text(
                t(language, "economy.insufficient_funds", balance=balance),
                chat_id=chat_id, message_id=message_id,
                parse_mode="Markdown",
                reply_markup=_keyboard_bet_type(),
            )
        except Exception:
            pass
        return

    # 2. Анимация колеса
    for frame in WHEEL_FRAMES:
        try:
            await bot.edit_message_text(
                f"🎡 *Рулетка*\n\n{frame}",
                chat_id=chat_id, message_id=message_id,
                parse_mode="Markdown",
            )
        except Exception:
            pass
        await asyncio.sleep(0.7)

    # 3. Бросок
    number = random.randint(0, 36)
    won = _check_win(number, bet_type)
    multiplier = _get_multiplier(bet_type)

    payout = 0
    if won:
        payout = bet * multiplier
        await credit(user_id, payout, "game_win")
        outcome = "win"
    else:
        outcome = "loss"

    balance = await get_balance(user_id)

    # 4. Запись в БД
    try:
        get_supabase_admin().table("casino_rounds").insert({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "game_type": "roulette",
            "amount": bet,
            "payout": payout,
            "house_fee": 0,
            "outcome": outcome,
            "result": {
                "number": number,
                "color": _number_color(number),
                "bet_type": bet_type,
            },
        }).execute()
    except Exception:
        pass

    # 5. История
    history = _get_last_numbers(user_id, limit=7)

    # 6. Показать результат
    text = _text_result(number, bet_type, bet, won, payout, balance, history)
    kb = _keyboard_result(bet_type, bet)
    try:
        await bot.edit_message_text(
            text, chat_id=chat_id, message_id=message_id,
            parse_mode="Markdown", reply_markup=kb,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Обратная совместимость — текстовая команда /рулетка
# ---------------------------------------------------------------------------

LEGACY_BET_ALIASES = {
    "к": "red", "красное": "red", "red": "red", "r": "red",
    "ч": "black", "чёрное": "black", "черное": "black", "black": "black", "b": "black",
    "чет": "even", "чётное": "even", "четное": "even", "even": "even",
    "нечет": "odd", "нечётное": "odd", "нечетное": "odd", "odd": "odd",
    "мало": "low", "1-18": "low", "low": "low",
    "много": "high", "19-36": "high", "high": "high",
}


def _parse_bet_type(raw: str) -> str | None:
    raw = raw.strip().lower()
    if raw in LEGACY_BET_ALIASES:
        return LEGACY_BET_ALIASES[raw]
    try:
        n = int(raw)
        if 0 <= n <= 36:
            return f"number:{n}"
    except ValueError:
        pass
    return None


async def play_roulette(user_id: str, bet: int, language: str, bet_type: str = "red") -> str:
    """Текстовая версия для команды /рулетка — возвращает строку."""
    success, balance = await debit(user_id, bet, "casino_bet")
    if not success:
        return t(language, "economy.insufficient_funds", balance=balance)

    number = random.randint(0, 36)
    color = _number_color(number)
    won = _check_win(number, bet_type)
    multiplier = _get_multiplier(bet_type)

    payout = 0
    if won:
        payout = bet * multiplier
        await credit(user_id, payout, "game_win")
        outcome = "win"
        msg = t(language, "casino.win", amount=payout - bet)
    else:
        outcome = "loss"
        msg = t(language, "casino.loss", amount=bet)

    try:
        get_supabase_admin().table("casino_rounds").insert({
            "id": str(uuid.uuid4()), "user_id": user_id, "game_type": "roulette",
            "amount": bet, "payout": payout, "house_fee": 0,
            "outcome": outcome,
            "result": {"number": number, "color": color, "bet_type": bet_type},
        }).execute()
    except Exception:
        pass

    history = _get_last_numbers(user_id, limit=5)
    hist_line = _render_history(history)
    board = _render_board(number)

    return (
        f"🎡 *Рулетка*\n\n"
        f"Ставка: {_bet_label(bet_type)}\n"
        f"Выпало: {color} *{number}*\n\n"
        f"{board}\n\n"
        f"{msg}"
        + (f"\n\n{hist_line}" if hist_line else "")
    )

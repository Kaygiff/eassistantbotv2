"""casino/games/mines.py — Мины. Сетка 5×5, 7 мин.

UX:
  1. Экран выбора суммы ставки (быстрые кнопки + ½ + Всё)
  2. Сетка 5×5 с прогрессом множителей
  3. Кнопка «Забрать» после каждой безопасной клетки
  4. После взрыва/забора — кнопки «Снова» и «Казино»

RTP ≈ 90%. Множители рассчитаны под 7 мин из 25 клеток.
"""

from __future__ import annotations

import random
import uuid

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from infra.db.supabase import get_supabase_admin
from world.economy.wallet import debit, credit, get_balance
from api.auth.session import set_fsm_state, set_fsm_data, get_fsm_data, clear_fsm_state, clear_fsm_data
from core.i18n import t

GRID_SIZE   = 25   # 5×5
MINE_COUNT  = 7
COLS        = 5
SAFE_CELLS  = GRID_SIZE - MINE_COUNT  # 18

QUICK_BETS = [50, 100, 500, 1_000, 5_000]

# Множители за каждую открытую безопасную клетку (индекс = кол-во открытых)
# Рассчитаны примерно как (25/18) ^ n * 0.9  (house edge ≈ 10%)
MULTIPLIERS = [
    1.00,  # старт
    1.12,  # 1
    1.26,  # 2
    1.42,  # 3
    1.60,  # 4
    1.82,  # 5
    2.08,  # 6
    2.40,  # 7
    2.78,  # 8
    3.24,  # 9
    3.80,  # 10
    4.50,  # 11
    5.40,  # 12
    6.55,  # 13
    8.10,  # 14
    10.20, # 15
    13.20, # 16
    17.80, # 17
    25.00, # 18 — максимум (все безопасные)
]


# ---------------------------------------------------------------------------
# Клавиатуры
# ---------------------------------------------------------------------------

def _keyboard_bet(current: int, balance: int) -> InlineKeyboardMarkup:
    rows = []
    quick_row = []
    for q in QUICK_BETS:
        if current + q <= balance:
            quick_row.append(InlineKeyboardButton(
                text=f"+{q}", callback_data=f"mines:amount:{current + q}",
            ))
        if len(quick_row) == 5:
            rows.append(quick_row)
            quick_row = []
    if quick_row:
        rows.append(quick_row)

    halves = []
    if balance > 0:
        halves.append(InlineKeyboardButton(
            text=f"½ ({balance // 2})", callback_data=f"mines:amount:{balance // 2}",
        ))
        halves.append(InlineKeyboardButton(
            text=f"Всё ({balance})", callback_data=f"mines:amount:{balance}",
        ))
    if halves:
        rows.append(halves)

    if current > 0:
        rows.append([InlineKeyboardButton(
            text=f"🗑 Сбросить (текущая: {current})", callback_data="mines:amount:0",
        )])

    if current >= 10:
        rows.append([InlineKeyboardButton(
            text=f"💣 Начать! Ставка: {current} Ecoins",
            callback_data=f"mines:start:{current}",
        )])

    rows.append([InlineKeyboardButton(text="🎰 Казино", callback_data="profile:casino")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _keyboard_grid(
    opened: list[int],
    mines_revealed: bool = False,
    mines: list[int] | None = None,
    game_over: bool = False,
    bet: int = 0,
) -> InlineKeyboardMarkup:
    """Рисует сетку 5×5."""
    rows = []
    row: list[InlineKeyboardButton] = []

    for i in range(GRID_SIZE):
        if i in opened:
            text = "✅"
            cb = "mines:noop"
        elif mines_revealed and mines and i in mines:
            text = "💣"
            cb = "mines:noop"
        elif game_over:
            text = "⬛"
            cb = "mines:noop"
        else:
            text = "⬜"
            cb = f"mines:open:{i}"

        row.append(InlineKeyboardButton(text=text, callback_data=cb))
        if len(row) == COLS:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    if not game_over and opened:
        mult = MULTIPLIERS[len(opened)]
        payout_now = int(bet * mult)
        rows.append([InlineKeyboardButton(
            text=f"💰 Забрать ({payout_now} Ecoins, ×{mult})",
            callback_data="mines:cashout",
        )])

    if game_over:
        rows.append([
            InlineKeyboardButton(text=f"🔄 Снова ({bet} Ecoins)", callback_data=f"mines:restart:{bet}"),
            InlineKeyboardButton(text="🎰 Казино", callback_data="profile:casino"),
        ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------------------------------------------------------------------------
# Тексты
# ---------------------------------------------------------------------------

def _text_bet_screen(current: int, balance: int) -> str:
    return (
        f"💣 *Мины* — 5×5, {MINE_COUNT} мин\n\n"
        f"💰 Баланс: *{balance} Ecoins*\n"
        f"🎯 Текущая ставка: *{current} Ecoins*\n\n"
        f"Открывай клетки и избегай мин.\n"
        f"Множитель растёт с каждой безопасной клеткой!\n\n"
        f"_Минимум: 10 Ecoins_"
    )


def _text_grid(opened: int, bet: int, alive: bool = True) -> str:
    if not alive:
        return (
            f"💣 *Мины*\n\n"
            f"💥 *Взрыв!* Мина!\n"
            f"Открыто безопасных: {opened}\n"
            f"Ставка сгорела: *{bet} Ecoins*"
        )

    mult = MULTIPLIERS[opened] if opened < len(MULTIPLIERS) else MULTIPLIERS[-1]
    payout = int(bet * mult)
    next_mult = MULTIPLIERS[opened + 1] if opened + 1 < len(MULTIPLIERS) else mult
    progress = "▓" * opened + "░" * (SAFE_CELLS - opened)

    return (
        f"💣 *Мины* — 5×5, {MINE_COUNT} мин\n\n"
        f"Прогресс: [{progress}] {opened}/{SAFE_CELLS}\n"
        f"Текущий множитель: *×{mult}* → *{payout} Ecoins*\n"
        f"Следующий: *×{next_mult}*\n\n"
        f"_Открывай или забирай!_"
    )


# ---------------------------------------------------------------------------
# Открытие
# ---------------------------------------------------------------------------

async def open_mines(
    user_id: str,
    language: str,
    bot: Bot,
    chat_id: int,
    message_id: int | None = None,
) -> None:
    balance = await get_balance(user_id)
    text = _text_bet_screen(0, balance)
    kb   = _keyboard_bet(0, balance)
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


async def show_mines_bet_screen(
    user_id: str,
    current: int,
    bot: Bot,
    chat_id: int,
    message_id: int,
) -> None:
    balance = await get_balance(user_id)
    text = _text_bet_screen(current, balance)
    kb   = _keyboard_bet(current, balance)
    try:
        await bot.edit_message_text(
            text, chat_id=chat_id, message_id=message_id,
            parse_mode="Markdown", reply_markup=kb,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Старт игры
# ---------------------------------------------------------------------------

async def start_mines_inline(
    user_id: str,
    bet: int,
    language: str,
    bot: Bot,
    chat_id: int,
    message_id: int,
) -> None:
    success, balance = await debit(user_id, bet, "casino_bet")
    if not success:
        await show_mines_bet_screen(user_id, 0, bot, chat_id, message_id)
        return

    mines = random.sample(range(GRID_SIZE), MINE_COUNT)
    await set_fsm_state(user_id, "casino:mines")
    await set_fsm_data(user_id, {
        "bet":      bet,
        "mines":    mines,
        "opened":   [],
        "language": language,
        "msg_id":   message_id,
    })

    text = _text_grid(0, bet, alive=True)
    kb   = _keyboard_grid([], False, None, False, bet)
    try:
        await bot.edit_message_text(
            text, chat_id=chat_id, message_id=message_id,
            parse_mode="Markdown", reply_markup=kb,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Обработка callback
# ---------------------------------------------------------------------------

async def handle_mines_callback(
    user_id: str,
    action: str,
    param: str | None,
    bot: Bot,
    chat_id: int,
    message_id: int,
) -> None:
    """Центральный обработчик для всех mines:* callback."""

    # --- Выбор суммы ставки ---
    if action == "amount":
        current = int(param) if param and param.isdigit() else 0
        await show_mines_bet_screen(user_id, current, bot, chat_id, message_id)
        return

    # --- Старт игры ---
    if action == "start":
        bet = int(param) if param and param.isdigit() else 0
        if bet < 10:
            await show_mines_bet_screen(user_id, 0, bot, chat_id, message_id)
            return
        await start_mines_inline(user_id, bet, "ru", bot, chat_id, message_id)
        return

    # --- Рестарт (кнопка «Снова») ---
    if action == "restart":
        bet = int(param) if param and param.isdigit() else 0
        await clear_fsm_state(user_id)
        await clear_fsm_data(user_id)
        if bet >= 10:
            await start_mines_inline(user_id, bet, "ru", bot, chat_id, message_id)
        else:
            await open_mines(user_id, "ru", bot, chat_id, message_id)
        return

    # --- noop (уже открытые клетки) ---
    if action == "noop":
        return

    # --- Игровые действия ---
    data = await get_fsm_data(user_id)
    if not data:
        await open_mines(user_id, "ru", bot, chat_id, message_id)
        return

    bet      = data["bet"]
    mines    = data["mines"]
    opened   = data["opened"]
    language = data.get("language", "ru")

    # --- Забрать ---
    if action == "cashout":
        if not opened:
            return
        mult   = MULTIPLIERS[len(opened)]
        payout = int(bet * mult)
        profit = payout - bet

        await credit(user_id, payout, "game_win")
        await clear_fsm_state(user_id)
        await clear_fsm_data(user_id)

        balance = await get_balance(user_id)

        try:
            get_supabase_admin().table("casino_rounds").insert({
                "id": str(uuid.uuid4()), "user_id": user_id, "game_type": "mines",
                "amount": bet, "payout": payout, "house_fee": 0, "outcome": "win",
                "result": {"opened": opened, "mines": mines, "multiplier": mult},
            }).execute()
        except Exception:
            pass

        text = (
            f"💰 *Забрал выигрыш!*\n\n"
            f"Открыто клеток: {len(opened)}\n"
            f"Множитель: ×{mult}\n"
            f"Выигрыш: *+{profit} Ecoins*\n\n"
            f"💰 Баланс: *{balance} Ecoins*"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🔄 Снова ({bet} Ecoins)", callback_data=f"mines:restart:{bet}")],
            [
                InlineKeyboardButton(text="💣 Новая ставка", callback_data="mines:amount:0"),
                InlineKeyboardButton(text="🎰 Казино",       callback_data="profile:casino"),
            ],
        ])
        try:
            await bot.edit_message_text(
                text, chat_id=chat_id, message_id=message_id,
                parse_mode="Markdown", reply_markup=kb,
            )
        except Exception:
            pass
        return

    # --- Открыть клетку ---
    if action == "open" and param is not None:
        cell = int(param)

        if cell in opened:
            return

        if cell in mines:
            # Взрыв!
            await clear_fsm_state(user_id)
            await clear_fsm_data(user_id)

            try:
                get_supabase_admin().table("casino_rounds").insert({
                    "id": str(uuid.uuid4()), "user_id": user_id, "game_type": "mines",
                    "amount": bet, "payout": 0, "house_fee": 0, "outcome": "loss",
                    "result": {"opened": opened, "mines": mines, "exploded_at": cell},
                }).execute()
            except Exception:
                pass

            balance = await get_balance(user_id)
            text = (
                f"💥 *Бум! Ты нашёл мину!*\n\n"
                f"Открыто безопасных: {len(opened)}\n"
                f"Ставка сгорела: *{bet} Ecoins*\n\n"
                f"💰 Баланс: *{balance} Ecoins*"
            )
            kb = _keyboard_grid(
                opened, mines_revealed=True, mines=mines,
                game_over=True, bet=bet,
            )
            try:
                await bot.edit_message_text(
                    text, chat_id=chat_id, message_id=message_id,
                    parse_mode="Markdown", reply_markup=kb,
                )
            except Exception:
                pass
            return

        # Безопасная клетка
        opened.append(cell)
        data["opened"] = opened
        await set_fsm_data(user_id, data)

        # Победа — все безопасные открыты
        if len(opened) == SAFE_CELLS:
            mult   = MULTIPLIERS[-1]
            payout = int(bet * mult)
            profit = payout - bet

            await credit(user_id, payout, "game_win")
            await clear_fsm_state(user_id)
            await clear_fsm_data(user_id)

            balance = await get_balance(user_id)

            try:
                get_supabase_admin().table("casino_rounds").insert({
                    "id": str(uuid.uuid4()), "user_id": user_id, "game_type": "mines",
                    "amount": bet, "payout": payout, "house_fee": 0, "outcome": "win",
                    "result": {"opened": opened, "mines": mines, "multiplier": mult},
                }).execute()
            except Exception:
                pass

            text = (
                f"🏆 *Легенда! Всё поле расчищено!*\n\n"
                f"Множитель: ×{mult}\n"
                f"Выигрыш: *+{profit} Ecoins*\n\n"
                f"💰 Баланс: *{balance} Ecoins*"
            )
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"🔄 Снова ({bet} Ecoins)", callback_data=f"mines:restart:{bet}")],
                [InlineKeyboardButton(text="🎰 Казино", callback_data="profile:casino")],
            ])
            try:
                await bot.edit_message_text(
                    text, chat_id=chat_id, message_id=message_id,
                    parse_mode="Markdown", reply_markup=kb,
                )
            except Exception:
                pass
            return

        # Обычный ход
        text = _text_grid(len(opened), bet, alive=True)
        kb   = _keyboard_grid(opened, False, None, False, bet)
        try:
            await bot.edit_message_text(
                text, chat_id=chat_id, message_id=message_id,
                parse_mode="Markdown", reply_markup=kb,
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Текстовая версия (обратная совместимость)
# ---------------------------------------------------------------------------

async def start_mines(user_id: str, bet: int, language: str) -> tuple[str, object]:
    success, balance = await debit(user_id, bet, "casino_bet")
    if not success:
        return t(language, "economy.insufficient_funds", balance=balance), None

    mines = random.sample(range(GRID_SIZE), MINE_COUNT)
    await set_fsm_state(user_id, "casino:mines")
    await set_fsm_data(user_id, {
        "bet": bet, "mines": mines, "opened": [], "language": language,
    })

    kb   = _keyboard_grid([], False, None, False, bet)
    text = _text_grid(0, bet, alive=True)
    return text, kb

"""casino/games/joker.py — Джокер. 3 карты (2 win + 1 джокер), до 5 раундов.

UX:
  1. Экран выбора суммы ставки (быстрые кнопки + ½ + Всё)
  2. Прошедшие раунды — строки не кликабельных кнопок в клавиатуре
  3. Текущий раунд — 3 кликабельные закрытые карты снизу
  4. После раунда — кнопки «Забрать» и «Следующий раунд»
  5. После финала/джокера — кнопки «Снова» и «Казино»

RTP ≈ 92%.
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

ROUND_MULTIPLIERS = [1.5, 2.5, 4.0, 6.5, 10.0]
MAX_ROUNDS        = len(ROUND_MULTIPLIERS)

QUICK_BETS = [50, 100, 500, 1_000, 5_000]

# Иконки карт
CARD_BACK  = "🎴"  # закрытая карта (кликабельная)
CARD_WIN   = "💎"  # выбранная победная карта
CARD_SAFE  = "⬜"  # другая безопасная (не выбранная, раскрытая)
CARD_JOKER = "💀"  # джокер


def _new_round() -> list[str]:
    cards = ["win", "win", "joker"]
    random.shuffle(cards)
    return cards


# ---------------------------------------------------------------------------
# Вспомогательные
# ---------------------------------------------------------------------------

def _noop(label: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data="joker:noop")


def _history_rows(history: list[dict]) -> list[list[InlineKeyboardButton]]:
    rows = []
    for h in history:
        r      = h["round"]
        cards  = h["cards"]
        picked = h["picked"]
        result = h["result"]
        mult   = ROUND_MULTIPLIERS[r - 1]

        icons = []
        for i, card in enumerate(cards):
            if i == picked:
                icons.append(CARD_WIN if result == "win" else CARD_JOKER)
            else:
                icons.append(CARD_JOKER if card == "joker" else CARD_SAFE)

        status = f"x{mult} OK" if result == "win" else "JOKER!"
        row = [_noop(icon) for icon in icons]
        row.append(_noop(status))
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Клавиатуры
# ---------------------------------------------------------------------------

def _keyboard_bet(current: int, balance: int) -> InlineKeyboardMarkup:
    rows = []
    quick_row = []
    for q in QUICK_BETS:
        if current + q <= balance:
            quick_row.append(InlineKeyboardButton(
                text=f"+{q}", callback_data=f"joker:amount:{current + q}",
            ))
        if len(quick_row) == 5:
            rows.append(quick_row)
            quick_row = []
    if quick_row:
        rows.append(quick_row)

    halves = []
    if balance > 0:
        halves.append(InlineKeyboardButton(
            text=f"1/2 ({balance // 2})", callback_data=f"joker:amount:{balance // 2}",
        ))
        halves.append(InlineKeyboardButton(
            text=f"All in ({balance})", callback_data=f"joker:amount:{balance}",
        ))
    if halves:
        rows.append(halves)

    if current > 0:
        rows.append([InlineKeyboardButton(
            text=f"Reset (now: {current})", callback_data="joker:amount:0",
        )])

    if current >= 10:
        rows.append([InlineKeyboardButton(
            text=f"Start! Bet: {current} Ecoins",
            callback_data=f"joker:start:{current}",
        )])

    rows.append([InlineKeyboardButton(text="Casino", callback_data="profile:casino")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _keyboard_round_active(round_num: int, history: list[dict]) -> InlineKeyboardMarkup:
    rows = _history_rows(history)
    rows.append([
        InlineKeyboardButton(text=CARD_BACK, callback_data=f"joker:pick:{round_num}:0"),
        InlineKeyboardButton(text=CARD_BACK, callback_data=f"joker:pick:{round_num}:1"),
        InlineKeyboardButton(text=CARD_BACK, callback_data=f"joker:pick:{round_num}:2"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _keyboard_with_cashout(completed_round: int, next_round: int, bet: int, history: list[dict]) -> InlineKeyboardMarkup:
    """История + карты следующего раунда + кнопка Забрать снизу."""
    rows = _history_rows(history)
    # Карты следующего раунда (кликабельные)
    rows.append([
        InlineKeyboardButton(text=CARD_BACK, callback_data=f"joker:pick:{next_round}:0"),
        InlineKeyboardButton(text=CARD_BACK, callback_data=f"joker:pick:{next_round}:1"),
        InlineKeyboardButton(text=CARD_BACK, callback_data=f"joker:pick:{next_round}:2"),
    ])
    mult   = ROUND_MULTIPLIERS[completed_round - 1]
    payout = int(bet * mult)
    rows.append([InlineKeyboardButton(
        text=f"Take {payout} Ecoins (x{mult})",
        callback_data="joker:cashout",
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _keyboard_final_win(bet: int, history: list[dict]) -> InlineKeyboardMarkup:
    """После прохождения всех раундов."""
    rows = _history_rows(history)
    rows.append([InlineKeyboardButton(
        text=f"Play again ({bet} Ecoins)", callback_data=f"joker:restart:{bet}",
    )])
    rows.append([InlineKeyboardButton(text="Casino", callback_data="profile:casino")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _keyboard_game_over(bet: int, history: list[dict]) -> InlineKeyboardMarkup:
    rows = _history_rows(history)
    rows.append([InlineKeyboardButton(
        text=f"Play again ({bet} Ecoins)", callback_data=f"joker:restart:{bet}",
    )])
    rows.append([
        InlineKeyboardButton(text="Change bet", callback_data="joker:amount:0"),
        InlineKeyboardButton(text="Casino",     callback_data="profile:casino"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------------------------------------------------------------------------
# Текст сообщения
# ---------------------------------------------------------------------------

def _build_text(
    bet: int,
    history: list[dict],
    current_round: int | None,
    game_over: bool = False,
    won: bool = False,
    cashout: bool = False,
    final_mult: float | None = None,
    balance: int | None = None,
) -> str:
    header = f"Joker — Bet: {bet} Ecoins\n\n"

    if game_over and not cashout and not won:
        round_info = f"JOKER! You lost on round {history[-1]['round']}\n"
        round_info += f"Bet lost: {bet} Ecoins"
    elif cashout or (game_over and won):
        payout = int(bet * final_mult)
        profit = payout - bet
        label = "Cashed out!" if cashout else "MAX WIN!"
        round_info = f"{label}\n"
        round_info += f"Multiplier: x{final_mult}\n"
        round_info += f"Profit: +{profit} Ecoins"
    elif current_round:
        mult      = ROUND_MULTIPLIERS[current_round - 1]
        next_mult = ROUND_MULTIPLIERS[current_round] if current_round < MAX_ROUNDS else mult
        round_info = (
            f"Round {current_round}/{MAX_ROUNDS}\n"
            f"x{mult}  ->  next: x{next_mult}\n\n"
            f"Pick a card — avoid the Joker!"
        )
    else:
        round_info = ""

    bal_line = f"\n\nBalance: {balance} Ecoins" if balance is not None else ""
    return header + round_info + bal_line


# ---------------------------------------------------------------------------
# Открытие
# ---------------------------------------------------------------------------

async def open_joker(
    user_id: str,
    language: str,
    bot: Bot,
    chat_id: int,
    message_id: int | None = None,
) -> None:
    balance = await get_balance(user_id)
    text = (
        f"Joker\n\n"
        f"Balance: {balance} Ecoins\n\n"
        f"5 rounds, 3 cards (2 safe + 1 Joker).\n"
        f"Multiplier grows each round!\n"
        f"x1.5 -> x2.5 -> x4.0 -> x6.5 -> x10.0\n\n"
        f"Min bet: 10 Ecoins"
    )
    kb = _keyboard_bet(0, balance)
    if message_id:
        try:
            await bot.edit_message_text(
                text, chat_id=chat_id, message_id=message_id,
                parse_mode=None, reply_markup=kb,
            )
            return
        except Exception:
            pass
    await bot.send_message(chat_id, text, reply_markup=kb)


async def show_joker_bet_screen(
    user_id: str,
    current: int,
    bot: Bot,
    chat_id: int,
    message_id: int,
) -> None:
    balance = await get_balance(user_id)
    text = (
        f"Joker\n\n"
        f"Balance: {balance} Ecoins\n"
        f"Current bet: {current} Ecoins\n\n"
        f"Min bet: 10 Ecoins"
    )
    kb = _keyboard_bet(current, balance)
    try:
        await bot.edit_message_text(
            text, chat_id=chat_id, message_id=message_id,
            reply_markup=kb,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Старт игры
# ---------------------------------------------------------------------------

async def start_joker_inline(
    user_id: str,
    bet: int,
    language: str,
    bot: Bot,
    chat_id: int,
    message_id: int,
) -> None:
    success, balance = await debit(user_id, bet, "casino_bet")
    if not success:
        await show_joker_bet_screen(user_id, 0, bot, chat_id, message_id)
        return

    cards = _new_round()
    await set_fsm_state(user_id, "casino:joker")
    await set_fsm_data(user_id, {
        "bet":      bet,
        "round":    1,
        "cards":    cards,
        "history":  [],
        "language": language,
    })

    text = _build_text(bet, [], current_round=1)
    kb   = _keyboard_round_active(1, [])
    try:
        await bot.edit_message_text(
            text, chat_id=chat_id, message_id=message_id,
            reply_markup=kb,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Обработка callback
# ---------------------------------------------------------------------------

async def handle_joker_callback(
    user_id: str,
    action: str,
    param: str | None,
    param2: str | None,
    bot: Bot,
    chat_id: int,
    message_id: int,
) -> None:

    if action == "noop":
        return

    if action == "amount":
        current = int(param) if param and param.isdigit() else 0
        await show_joker_bet_screen(user_id, current, bot, chat_id, message_id)
        return

    if action == "start":
        bet = int(param) if param and param.isdigit() else 0
        if bet < 10:
            await show_joker_bet_screen(user_id, 0, bot, chat_id, message_id)
            return
        await start_joker_inline(user_id, bet, "ru", bot, chat_id, message_id)
        return

    if action == "restart":
        bet = int(param) if param and param.isdigit() else 0
        await clear_fsm_state(user_id)
        await clear_fsm_data(user_id)
        if bet >= 10:
            await start_joker_inline(user_id, bet, "ru", bot, chat_id, message_id)
        else:
            await open_joker(user_id, "ru", bot, chat_id, message_id)
        return

    if action == "cashout":
        data = await get_fsm_data(user_id)
        if not data:
            await open_joker(user_id, "ru", bot, chat_id, message_id)
            return
        bet     = data["bet"]
        history = data.get("history", [])
        r       = data["round"]

        # r уже указывает на следующий раунд (карты загружены), берём последний из истории
        if not history:
            return
        completed = history[-1]["round"]
        mult   = ROUND_MULTIPLIERS[completed - 1]
        payout = int(bet * mult)

        await credit(user_id, payout, "game_win")
        await clear_fsm_state(user_id)
        await clear_fsm_data(user_id)

        balance = await get_balance(user_id)

        try:
            get_supabase_admin().table("casino_rounds").insert({
                "id": str(uuid.uuid4()), "user_id": user_id, "game_type": "joker",
                "amount": bet, "payout": payout, "house_fee": 0, "outcome": "win",
                "result": {"rounds_survived": completed, "multiplier": mult, "history": history},
            }).execute()
        except Exception:
            pass

        text = _build_text(bet, history, None, game_over=True, won=True,
                           cashout=True, final_mult=mult, balance=balance)
        kb   = _keyboard_game_over(bet, history)
        try:
            await bot.edit_message_text(
                text, chat_id=chat_id, message_id=message_id,
                reply_markup=kb,
            )
        except Exception:
            pass
        return

    if action == "pick":
        data = await get_fsm_data(user_id)
        if not data:
            await open_joker(user_id, "ru", bot, chat_id, message_id)
            return

        bet     = data["bet"]
        round_n = data["round"]
        cards   = data["cards"]
        history = data.get("history", [])

        try:
            cb_round = int(param)
            card_idx = int(param2)
        except (TypeError, ValueError):
            return
        if cb_round != round_n:
            return

        result = cards[card_idx]

        history_entry = {
            "round":  round_n,
            "cards":  cards,
            "picked": card_idx,
            "result": result,
        }
        history.append(history_entry)
        data["history"] = history

        if result == "joker":
            await clear_fsm_state(user_id)
            await clear_fsm_data(user_id)

            balance = await get_balance(user_id)

            try:
                get_supabase_admin().table("casino_rounds").insert({
                    "id": str(uuid.uuid4()), "user_id": user_id, "game_type": "joker",
                    "amount": bet, "payout": 0, "house_fee": 0, "outcome": "loss",
                    "result": {"round": round_n, "history": history},
                }).execute()
            except Exception:
                pass

            text = _build_text(bet, history, None, game_over=True, won=False, balance=balance)
            kb   = _keyboard_game_over(bet, history)
            try:
                await bot.edit_message_text(
                    text, chat_id=chat_id, message_id=message_id,
                    reply_markup=kb,
                )
            except Exception:
                pass
            return

        mult = ROUND_MULTIPLIERS[round_n - 1]

        if round_n >= MAX_ROUNDS:
            payout = int(bet * ROUND_MULTIPLIERS[-1])
            await credit(user_id, payout, "game_win")
            await clear_fsm_state(user_id)
            await clear_fsm_data(user_id)

            balance = await get_balance(user_id)

            try:
                get_supabase_admin().table("casino_rounds").insert({
                    "id": str(uuid.uuid4()), "user_id": user_id, "game_type": "joker",
                    "amount": bet, "payout": payout, "house_fee": 0, "outcome": "win",
                    "result": {"rounds_survived": MAX_ROUNDS, "multiplier": ROUND_MULTIPLIERS[-1], "history": history},
                }).execute()
            except Exception:
                pass

            text = _build_text(bet, history, None, game_over=True, won=True,
                               final_mult=ROUND_MULTIPLIERS[-1], balance=balance)
            kb   = _keyboard_final_win(bet, history)
            try:
                await bot.edit_message_text(
                    text, chat_id=chat_id, message_id=message_id,
                    reply_markup=kb,
                )
            except Exception:
                pass
            return

        next_round = round_n + 1
        new_cards  = _new_round()
        data["round"] = next_round
        data["cards"] = new_cards
        await set_fsm_data(user_id, data)

        mult = ROUND_MULTIPLIERS[round_n - 1]
        text = _build_text(bet, history, current_round=next_round)
        kb   = _keyboard_with_cashout(round_n, next_round, bet, history)
        try:
            await bot.edit_message_text(
                text, chat_id=chat_id, message_id=message_id,
                reply_markup=kb,
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Текстовая версия (обратная совместимость)
# ---------------------------------------------------------------------------

async def start_joker(user_id: str, bet: int, language: str) -> tuple[str, object]:
    success, balance = await debit(user_id, bet, "casino_bet")
    if not success:
        return t(language, "economy.insufficient_funds", balance=balance), None

    cards = _new_round()
    await set_fsm_state(user_id, "casino:joker")
    await set_fsm_data(user_id, {
        "bet": bet, "round": 1, "cards": cards, "history": [], "language": language,
    })

    kb   = _keyboard_round_active(1, [])
    text = _build_text(bet, [], current_round=1)
    return text, kb

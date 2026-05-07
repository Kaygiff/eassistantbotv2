"""casino/games/joker.py — Джокер. 3 карты (2 win + 1 джокер), до 5 раундов.

UX:
  1. Экран выбора суммы ставки (быстрые кнопки + ½ + Всё)
  2. Карты раундов накапливаются снизу в одном сообщении
  3. Кнопка «Забрать» доступна после каждого успешного раунда
  4. После финала/джокера — кнопки «Снова» и «Казино»

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
CARD_BACK    = "🂠"
CARD_WIN     = "✅"
CARD_JOKER   = "🃏"
CARD_UNKNOWN = "⬛"


def _new_round() -> list[str]:
    cards = ["win", "win", "joker"]
    random.shuffle(cards)
    return cards


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
            text=f"½ ({balance // 2})", callback_data=f"joker:amount:{balance // 2}",
        ))
        halves.append(InlineKeyboardButton(
            text=f"Всё ({balance})", callback_data=f"joker:amount:{balance}",
        ))
    if halves:
        rows.append(halves)

    if current > 0:
        rows.append([InlineKeyboardButton(
            text=f"🗑 Сбросить (текущая: {current})", callback_data="joker:amount:0",
        )])

    if current >= 10:
        rows.append([InlineKeyboardButton(
            text=f"🃏 Начать! Ставка: {current} Ecoins",
            callback_data=f"joker:start:{current}",
        )])

    rows.append([InlineKeyboardButton(text="🎰 Казино", callback_data="profile:casino")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _keyboard_round_active(round_num: int) -> InlineKeyboardMarkup:
    """3 закрытые карты для текущего раунда."""
    row = [
        InlineKeyboardButton(text=CARD_BACK, callback_data=f"joker:pick:{round_num}:0"),
        InlineKeyboardButton(text=CARD_BACK, callback_data=f"joker:pick:{round_num}:1"),
        InlineKeyboardButton(text=CARD_BACK, callback_data=f"joker:pick:{round_num}:2"),
    ]
    return InlineKeyboardMarkup(inline_keyboard=[row])


def _keyboard_after_win(round_num: int, bet: int) -> InlineKeyboardMarkup:
    """После успешного раунда — Забрать / Следующий раунд."""
    mult   = ROUND_MULTIPLIERS[round_num - 1]
    payout = int(bet * mult)

    if round_num >= MAX_ROUNDS:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🔄 Снова ({bet} Ecoins)", callback_data=f"joker:restart:{bet}")],
            [InlineKeyboardButton(text="🎰 Казино", callback_data="profile:casino")],
        ])

    next_mult = ROUND_MULTIPLIERS[round_num]
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"💰 Забрать ({payout} Ecoins, ×{mult})",
                callback_data="joker:cashout",
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"▶️ Раунд {round_num + 1} (×{next_mult})",
                callback_data=f"joker:next:{round_num + 1}",
            ),
        ],
    ])


def _keyboard_game_over(bet: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🔄 Снова ({bet} Ecoins)", callback_data=f"joker:restart:{bet}")],
        [
            InlineKeyboardButton(text="💰 Изменить ставку", callback_data="joker:amount:0"),
            InlineKeyboardButton(text="🎰 Казино",          callback_data="profile:casino"),
        ],
    ])


# ---------------------------------------------------------------------------
# Отображение карт раундов
# ---------------------------------------------------------------------------

def _render_history(history: list[dict]) -> str:
    """Рендерит все прошедшие раунды."""
    lines = []
    for h in history:
        r      = h["round"]
        cards  = h["cards"]
        picked = h["picked"]
        result = h["result"]
        mult   = ROUND_MULTIPLIERS[r - 1]

        row_icons = []
        for i, card in enumerate(cards):
            if i == picked:
                icon = CARD_WIN if result == "win" else CARD_JOKER
            elif card == "joker":
                icon = CARD_JOKER
            else:
                icon = CARD_UNKNOWN
            row_icons.append(icon)

        status = f"✅ ×{mult}" if result == "win" else "💥 Джокер!"
        lines.append(f"Раунд {r}: {' '.join(row_icons)}  {status}")
    return "\n".join(lines)


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
    header = f"🃏 *Джокер* — Ставка: *{bet} Ecoins*\n\n"

    hist_block = ""
    if history:
        hist_block = _render_history(history) + "\n\n"

    if game_over and not cashout:
        round_info = f"💥 *Джокер найден на раунде {history[-1]['round']}!*\n"
        round_info += f"Ставка сгорела: *{bet} Ecoins*"
    elif cashout or (game_over and won):
        payout = int(bet * final_mult)
        profit = payout - bet
        round_info = f"💰 *{'Забрал выигрыш' if cashout else 'Максимальный выигрыш!'}!*\n"
        round_info += f"Множитель: ×{final_mult}\n"
        round_info += f"Выигрыш: *+{profit} Ecoins*"
    elif current_round:
        mult      = ROUND_MULTIPLIERS[current_round - 1]
        next_mult = ROUND_MULTIPLIERS[current_round] if current_round < MAX_ROUNDS else mult
        round_info = (
            f"Раунд *{current_round}/{MAX_ROUNDS}*\n"
            f"Текущий множитель: ×{mult}\n"
            f"Следующий: ×{next_mult}\n\n"
            f"_Выбери карту — избегай Джокера!_"
        )
    else:
        round_info = ""

    bal_line = f"\n\n💰 Баланс: *{balance} Ecoins*" if balance is not None else ""
    return header + hist_block + round_info + bal_line


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
        f"🃏 *Джокер*\n\n"
        f"💰 Баланс: *{balance} Ecoins*\n\n"
        f"5 раундов, 3 карты (2 победные + 1 Джокер).\n"
        f"Множитель растёт с каждым раундом!\n"
        f"×1.5 → ×2.5 → ×4.0 → ×6.5 → ×10.0\n\n"
        f"_Минимум: 10 Ecoins_"
    )
    kb = _keyboard_bet(0, balance)
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


async def show_joker_bet_screen(
    user_id: str,
    current: int,
    bot: Bot,
    chat_id: int,
    message_id: int,
) -> None:
    balance = await get_balance(user_id)
    text = (
        f"🃏 *Джокер*\n\n"
        f"💰 Баланс: *{balance} Ecoins*\n"
        f"🎯 Текущая ставка: *{current} Ecoins*\n\n"
        f"_Минимум: 10 Ecoins_"
    )
    kb = _keyboard_bet(current, balance)
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
    kb   = _keyboard_round_active(1)
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

async def handle_joker_callback(
    user_id: str,
    action: str,
    param: str | None,
    param2: str | None,
    bot: Bot,
    chat_id: int,
    message_id: int,
) -> None:
    """param  = первый параметр после action
       param2 = второй (для pick: round_num и card_idx)
    """

    # --- Выбор ставки ---
    if action == "amount":
        current = int(param) if param and param.isdigit() else 0
        await show_joker_bet_screen(user_id, current, bot, chat_id, message_id)
        return

    # --- Старт ---
    if action == "start":
        bet = int(param) if param and param.isdigit() else 0
        if bet < 10:
            await show_joker_bet_screen(user_id, 0, bot, chat_id, message_id)
            return
        await start_joker_inline(user_id, bet, "ru", bot, chat_id, message_id)
        return

    # --- Рестарт ---
    if action == "restart":
        bet = int(param) if param and param.isdigit() else 0
        await clear_fsm_state(user_id)
        await clear_fsm_data(user_id)
        if bet >= 10:
            await start_joker_inline(user_id, bet, "ru", bot, chat_id, message_id)
        else:
            await open_joker(user_id, "ru", bot, chat_id, message_id)
        return

    # --- Следующий раунд (кнопка ▶️) ---
    if action == "next":
        data = await get_fsm_data(user_id)
        if not data:
            await open_joker(user_id, "ru", bot, chat_id, message_id)
            return
        bet     = data["bet"]
        history = data.get("history", [])
        next_r  = int(param) if param and param.isdigit() else data["round"]
        cards   = _new_round()
        data["round"] = next_r
        data["cards"] = cards
        await set_fsm_data(user_id, data)

        text = _build_text(bet, history, current_round=next_r)
        kb   = _keyboard_round_active(next_r)
        try:
            await bot.edit_message_text(
                text, chat_id=chat_id, message_id=message_id,
                parse_mode="Markdown", reply_markup=kb,
            )
        except Exception:
            pass
        return

    # --- Забрать ---
    if action == "cashout":
        data = await get_fsm_data(user_id)
        if not data:
            await open_joker(user_id, "ru", bot, chat_id, message_id)
            return
        bet     = data["bet"]
        history = data.get("history", [])
        r       = data["round"]

        # Множитель за последний пройденный раунд
        completed = r - 1
        if completed < 1:
            return
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
        kb   = _keyboard_game_over(bet)
        try:
            await bot.edit_message_text(
                text, chat_id=chat_id, message_id=message_id,
                parse_mode="Markdown", reply_markup=kb,
            )
        except Exception:
            pass
        return

    # --- Выбор карты ---
    if action == "pick":
        # param  = round_num (str), param2 = card_idx (str)
        data = await get_fsm_data(user_id)
        if not data:
            await open_joker(user_id, "ru", bot, chat_id, message_id)
            return

        bet     = data["bet"]
        round_n = data["round"]
        cards   = data["cards"]
        history = data.get("history", [])

        # Защита: если param != текущий раунд — игнорируем (старые кнопки)
        try:
            cb_round = int(param)
            card_idx  = int(param2)
        except (TypeError, ValueError):
            return
        if cb_round != round_n:
            return

        result = cards[card_idx]

        # Сохраняем в историю
        history_entry = {
            "round":  round_n,
            "cards":  cards,
            "picked": card_idx,
            "result": result,
        }
        history.append(history_entry)
        data["history"] = history

        # --- Джокер ---
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
            kb   = _keyboard_game_over(bet)
            try:
                await bot.edit_message_text(
                    text, chat_id=chat_id, message_id=message_id,
                    parse_mode="Markdown", reply_markup=kb,
                )
            except Exception:
                pass
            return

        # --- Победа в раунде ---
        mult = ROUND_MULTIPLIERS[round_n - 1]

        if round_n >= MAX_ROUNDS:
            # Прошёл все раунды!
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
            kb   = _keyboard_after_win(round_n, bet)
            try:
                await bot.edit_message_text(
                    text, chat_id=chat_id, message_id=message_id,
                    parse_mode="Markdown", reply_markup=kb,
                )
            except Exception:
                pass
            return

        # Переходим к следующему — обновляем данные, показываем кнопку «Забрать/Дальше»
        data["round"] = round_n + 1
        await set_fsm_data(user_id, data)

        text = _build_text(bet, history, current_round=round_n + 1)
        kb   = _keyboard_after_win(round_n + 1, bet)   # round_n + 1 => после прохождения round_n

        # Хитрость: показываем итог раунда + кнопки Забрать/Продолжить.
        # Кнопка "▶️ Раунд N" подгружает новые карты через joker:next
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

async def start_joker(user_id: str, bet: int, language: str) -> tuple[str, object]:
    success, balance = await debit(user_id, bet, "casino_bet")
    if not success:
        return t(language, "economy.insufficient_funds", balance=balance), None

    cards = _new_round()
    await set_fsm_state(user_id, "casino:joker")
    await set_fsm_data(user_id, {
        "bet": bet, "round": 1, "cards": cards, "history": [], "language": language,
    })

    kb   = _keyboard_round_active(1)
    text = _build_text(bet, [], current_round=1)
    return text, kb

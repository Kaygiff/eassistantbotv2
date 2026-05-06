"""casino/games/joker.py — Джокер. 3 карты (2 выигрышные, 1 джокер), множитель растёт."""

from __future__ import annotations
import random
import uuid
from infra.db.supabase import get_supabase_admin
from world.economy.wallet import debit, credit
from api.auth.session import set_fsm_state, set_fsm_data, get_fsm_data, clear_fsm_state, clear_fsm_data
from core.i18n import t

# Множители за каждый успешный раунд
ROUND_MULTIPLIERS = [1.5, 2.5, 4.0, 6.5, 10.0]
MAX_ROUNDS = len(ROUND_MULTIPLIERS)


def _new_round() -> list[str]:
    """Генерирует расположение карт: 2 выигрышные + 1 джокер."""
    cards = ["win", "win", "joker"]
    random.shuffle(cards)
    return cards


async def start_joker(user_id: str, bet: int, language: str) -> tuple[str, object]:
    """Начинает игру."""
    success, balance = await debit(user_id, bet, "casino_bet")
    if not success:
        return t(language, "economy.insufficient_funds", balance=balance), None

    cards = _new_round()
    await set_fsm_state(user_id, "casino:joker")
    await set_fsm_data(user_id, {
        "bet": bet,
        "round": 1,
        "cards": cards,
        "language": language,
    })

    keyboard = _build_keyboard(round_num=1, revealed=None)
    text = (
        f"🃏 *Джокер*\n\n"
        f"Ставка: *{bet} Ecoins*\n"
        f"Раунд: *1/{MAX_ROUNDS}*\n\n"
        f"Выбери карту — избегай Джокера!\n"
        f"Выигрышный множитель: *x{ROUND_MULTIPLIERS[0]}*"
    )
    return text, keyboard


def _build_keyboard(round_num: int, revealed: dict | None):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    if revealed is None:
        buttons = [[
            InlineKeyboardButton(text="🂠", callback_data="joker:pick:0"),
            InlineKeyboardButton(text="🂠", callback_data="joker:pick:1"),
            InlineKeyboardButton(text="🂠", callback_data="joker:pick:2"),
        ]]
    else:
        row = []
        for i in range(3):
            if i == revealed["picked"]:
                text = "✅" if revealed["result"] == "win" else "🃏"
            elif revealed["cards"][i] == "joker":
                text = "🃏"
            else:
                text = "🂠"
            row.append(InlineKeyboardButton(text=text, callback_data=f"joker:pick:{i}"))
        buttons = [row]

    if revealed and revealed["result"] == "win":
        buttons.append([InlineKeyboardButton(
            text="💰 Забрать",
            callback_data="joker:cashout"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def handle_joker_callback(user_id: str, action: str, param: str | None) -> tuple[str, object]:
    data = await get_fsm_data(user_id)
    if not data:
        return "❌ Игра не найдена. Начни заново.", None

    bet = data["bet"]
    round_num = data["round"]
    cards = data["cards"]
    language = data.get("language", "ru")

    if action == "cashout":
        multiplier = ROUND_MULTIPLIERS[round_num - 2]  # уже прошёл round-1 раундов
        payout = int(bet * multiplier)
        await credit(user_id, payout, "game_win")
        await clear_fsm_state(user_id)
        await clear_fsm_data(user_id)

        get_supabase_admin().table("casino_rounds").insert({
            "id": str(uuid.uuid4()), "user_id": user_id, "game_type": "joker",
            "amount": bet, "payout": payout, "house_fee": 0, "outcome": "win",
            "result": {"rounds_survived": round_num - 1, "multiplier": multiplier},
        }).execute()

        return (
            f"💰 *Забрал выигрыш!*\n\n"
            f"Раундов пройдено: {round_num - 1}\n"
            f"Множитель: x{multiplier}\n"
            f"Выигрыш: *+{payout - bet} Ecoins*"
        ), None

    if action == "pick" and param is not None:
        picked = int(param)
        result = cards[picked]
        revealed = {"picked": picked, "cards": cards, "result": result}

        if result == "joker":
            # Проигрыш
            await clear_fsm_state(user_id)
            await clear_fsm_data(user_id)

            get_supabase_admin().table("casino_rounds").insert({
                "id": str(uuid.uuid4()), "user_id": user_id, "game_type": "joker",
                "amount": bet, "payout": 0, "house_fee": 0, "outcome": "loss",
                "result": {"round": round_num, "picked": picked, "cards": cards},
            }).execute()

            keyboard = _build_keyboard(round_num, revealed)
            return (
                f"🃏 *Джокер!*\n\n"
                f"Ты выбрал Джокера на раунде {round_num}!\n"
                f"Ставка сгорела: *{bet} Ecoins*"
            ), keyboard

        # Выиграл раунд
        multiplier = ROUND_MULTIPLIERS[round_num - 1]

        if round_num >= MAX_ROUNDS:
            # Прошёл все раунды — максимальный выигрыш
            payout = int(bet * ROUND_MULTIPLIERS[-1])
            await credit(user_id, payout, "game_win")
            await clear_fsm_state(user_id)
            await clear_fsm_data(user_id)

            get_supabase_admin().table("casino_rounds").insert({
                "id": str(uuid.uuid4()), "user_id": user_id, "game_type": "joker",
                "amount": bet, "payout": payout, "house_fee": 0, "outcome": "win",
                "result": {"rounds_survived": MAX_ROUNDS, "multiplier": ROUND_MULTIPLIERS[-1]},
            }).execute()

            keyboard = _build_keyboard(round_num, revealed)
            return (
                f"🏆 *Легенда!*\n\n"
                f"Ты прошёл все {MAX_ROUNDS} раундов!\n"
                f"Множитель: x{ROUND_MULTIPLIERS[-1]}\n"
                f"Выигрыш: *+{payout - bet} Ecoins*"
            ), keyboard

        # Переходим к следующему раунду
        new_cards = _new_round()
        data["round"] = round_num + 1
        data["cards"] = new_cards
        await set_fsm_data(user_id, data)

        next_multiplier = ROUND_MULTIPLIERS[round_num]
        keyboard = _build_keyboard(round_num + 1, None)
        return (
            f"✅ *Раунд {round_num} пройден!*\n\n"
            f"Раунд: *{round_num + 1}/{MAX_ROUNDS}*\n"
            f"Текущий множитель: *x{multiplier}*\n"
            f"Следующий: *x{next_multiplier}*\n\n"
            f"Выбери карту или забери выигрыш!"
        ), _build_keyboard(round_num + 1, None)

    return "❌ Неизвестное действие.", None

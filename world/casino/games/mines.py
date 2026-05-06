"""casino/games/mines.py — Мины. Сетка 3x3, одна мина, множитель растёт."""

from __future__ import annotations
import random
import uuid
from infra.db.supabase import get_supabase_admin
from world.economy.wallet import debit, credit
from api.auth.session import get_fsm_state, set_fsm_state, set_fsm_data, get_fsm_data, clear_fsm_state, clear_fsm_data
from core.i18n import t

GRID_SIZE = 9       # 3x3
MINE_COUNT = 1
MULTIPLIERS = [1.0, 1.3, 1.7, 2.2, 2.9, 3.8, 5.0, 7.0, 10.0]  # по числу открытых клеток


async def start_mines(user_id: str, bet: int, language: str) -> tuple[str, object]:
    """Начинает игру. Возвращает (текст, клавиатура)."""
    success, balance = await debit(user_id, bet, "casino_bet")
    if not success:
        return t(language, "economy.insufficient_funds", balance=balance), None

    # Расставляем мины
    mine_positions = random.sample(range(GRID_SIZE), MINE_COUNT)

    await set_fsm_state(user_id, "casino:mines")
    await set_fsm_data(user_id, {
        "bet": bet,
        "mines": mine_positions,
        "opened": [],
        "language": language,
    })

    keyboard = _build_keyboard(opened=[], mines_revealed=False)
    text = (
        f"💣 *Мины*\n\n"
        f"Ставка: *{bet} Ecoins*\n"
        f"Открывай клетки — избегай мины!\n"
        f"Множитель растёт с каждой безопасной клеткой.\n\n"
        f"Текущий множитель: *x1.0*"
    )
    return text, keyboard


def _build_keyboard(opened: list[int], mines_revealed: bool, mines: list[int] = None):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = []
    row = []
    for i in range(GRID_SIZE):
        if i in opened:
            text = "✅"
        elif mines_revealed and mines and i in mines:
            text = "💣"
        else:
            text = "⬜"
        row.append(InlineKeyboardButton(text=text, callback_data=f"mines:open:{i}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    # Кнопка забрать
    buttons.append([InlineKeyboardButton(text="💰 Забрать выигрыш", callback_data="mines:cashout")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def handle_mines_callback(user_id: str, action: str, param: str | None) -> tuple[str, object]:
    """Обрабатывает нажатие клетки или кнопку забрать."""
    data = await get_fsm_data(user_id)
    if not data:
        return "❌ Игра не найдена. Начни заново.", None

    bet = data["bet"]
    mines = data["mines"]
    opened = data["opened"]
    language = data.get("language", "ru")

    if action == "cashout":
        multiplier = MULTIPLIERS[len(opened)] if opened else 1.0
        payout = int(bet * multiplier)
        await credit(user_id, payout, "game_win")
        await clear_fsm_state(user_id)
        await clear_fsm_data(user_id)

        get_supabase_admin().table("casino_rounds").insert({
            "id": str(uuid.uuid4()), "user_id": user_id, "game_type": "mines",
            "amount": bet, "payout": payout, "house_fee": 0, "outcome": "win",
            "result": {"opened": opened, "mines": mines, "multiplier": multiplier},
        }).execute()

        profit = payout - bet
        return (
            f"💰 *Забрал выигрыш!*\n\n"
            f"Открыто клеток: {len(opened)}\n"
            f"Множитель: x{multiplier}\n"
            f"Выигрыш: *+{profit} Ecoins*"
        ), None

    if action == "open" and param is not None:
        cell = int(param)
        if cell in opened:
            # Уже открыта
            multiplier = MULTIPLIERS[len(opened)]
            keyboard = _build_keyboard(opened, False)
            return f"💣 *Мины*\n\nОткрыто: {len(opened)} | Множитель: *x{multiplier}*", keyboard

        if cell in mines:
            # Взорвался
            await clear_fsm_state(user_id)
            await clear_fsm_data(user_id)

            get_supabase_admin().table("casino_rounds").insert({
                "id": str(uuid.uuid4()), "user_id": user_id, "game_type": "mines",
                "amount": bet, "payout": 0, "house_fee": 0, "outcome": "loss",
                "result": {"opened": opened, "mines": mines, "exploded_at": cell},
            }).execute()

            keyboard = _build_keyboard(opened, mines_revealed=True, mines=mines)
            return (
                f"💥 *Бум! Ты нашёл мину!*\n\n"
                f"Ставка сгорела: *{bet} Ecoins*\n"
                f"Открыто клеток: {len(opened)}"
            ), keyboard

        # Безопасная клетка
        opened.append(cell)
        data["opened"] = opened
        await set_fsm_data(user_id, data)

        if len(opened) == GRID_SIZE - MINE_COUNT:
            # Открыл все безопасные — максимальный выигрыш
            multiplier = MULTIPLIERS[-1]
            payout = int(bet * multiplier)
            await credit(user_id, payout, "game_win")
            await clear_fsm_state(user_id)
            await clear_fsm_data(user_id)

            get_supabase_admin().table("casino_rounds").insert({
                "id": str(uuid.uuid4()), "user_id": user_id, "game_type": "mines",
                "amount": bet, "payout": payout, "house_fee": 0, "outcome": "win",
                "result": {"opened": opened, "mines": mines, "multiplier": multiplier},
            }).execute()

            return (
                f"🏆 *Всё поле расчищено!*\n\n"
                f"Множитель: x{multiplier}\n"
                f"Выигрыш: *+{payout - bet} Ecoins*"
            ), None

        multiplier = MULTIPLIERS[len(opened)]
        keyboard = _build_keyboard(opened, False)
        return (
            f"💣 *Мины*\n\n"
            f"✅ Безопасно! Открыто: {len(opened)}\n"
            f"Текущий множитель: *x{multiplier}*\n\n"
            f"Продолжай или забирай выигрыш!"
        ), keyboard

    return "❌ Неизвестное действие.", None

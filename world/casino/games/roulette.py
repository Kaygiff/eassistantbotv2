"""casino/games/roulette.py — Рулетка."""

from __future__ import annotations
import random, uuid
from infra.db.supabase import supabase_admin
from world.economy.wallet import debit, credit
from core.i18n import t

REDS = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}


async def play_roulette(user_id: str, bet: int, language: str) -> str:
    success, balance = await debit(user_id, bet, "casino_bet")
    if not success:
        return t(language, "economy.insufficient_funds", balance=balance)

    number = random.randint(0, 36)
    color = "🔴" if number in REDS else ("⚫" if number != 0 else "🟢")

    # Ставка на цвет (красное/чёрное) — упрощённо
    payout = 0
    outcome = "loss"

    # Случайно выбираем что игрок ставил (red/black/number)
    choices = ["red", "black", "even", "odd"]
    player_bet = random.choice(choices)

    won = False
    if player_bet == "red" and number in REDS:
        won = True
    elif player_bet == "black" and number not in REDS and number != 0:
        won = True
    elif player_bet == "even" and number != 0 and number % 2 == 0:
        won = True
    elif player_bet == "odd" and number % 2 == 1:
        won = True

    if won:
        payout = bet * 2
        outcome = "win"
        await credit(user_id, payout, "game_win")
        msg = t(language, "casino.win", amount=payout - bet)
    else:
        msg = t(language, "casino.loss", amount=bet)

    supabase_admin.table("casino_rounds").insert({
        "id": str(uuid.uuid4()), "user_id": user_id, "game_type": "roulette",
        "amount": bet, "payout": payout, "house_fee": 0, "outcome": outcome,
        "result": {"number": number, "color": color},
    }).execute()

    return f"🎡 *Рулетка*\n\n{color} Выпало: *{number}*\n\n{msg}"

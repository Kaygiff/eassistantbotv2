"""casino/games/roulette.py — Рулетка с реальным выбором игрока."""

from __future__ import annotations
import random
import uuid
from infra.db.supabase import get_supabase_admin
from world.economy.wallet import debit, credit
from core.i18n import t

REDS = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}

BET_ALIASES = {
    "к": "red", "красное": "red", "red": "red", "r": "red",
    "ч": "black", "чёрное": "black", "черное": "black", "black": "black", "b": "black",
}


def _parse_bet_type(raw: str) -> str | None:
    """Парсит тип ставки: к/ч/число."""
    raw = raw.strip().lower()
    if raw in BET_ALIASES:
        return BET_ALIASES[raw]
    try:
        n = int(raw)
        if 0 <= n <= 36:
            return f"number:{n}"
    except ValueError:
        pass
    return None


async def play_roulette(user_id: str, bet: int, language: str, bet_type: str = "red") -> str:
    success, balance = await debit(user_id, bet, "casino_bet")
    if not success:
        return t(language, "economy.insufficient_funds", balance=balance)

    number = random.randint(0, 36)
    color = "🔴" if number in REDS else ("⚫" if number != 0 else "🟢")

    won = False
    multiplier = 2

    if bet_type == "red":
        won = number in REDS
        bet_label = "🔴 Красное"
    elif bet_type == "black":
        won = number not in REDS and number != 0
        bet_label = "⚫ Чёрное"
    elif bet_type.startswith("number:"):
        target = int(bet_type.split(":")[1])
        won = number == target
        multiplier = 36
        bet_label = f"🔢 Число {target}"
    else:
        won = number in REDS
        bet_label = "🔴 Красное"

    payout = 0
    if won:
        payout = bet * multiplier
        await credit(user_id, payout, "game_win")
        msg = t(language, "casino.win", amount=payout - bet)
    else:
        msg = t(language, "casino.loss", amount=bet)

    get_supabase_admin().table("casino_rounds").insert({
        "id": str(uuid.uuid4()), "user_id": user_id, "game_type": "roulette",
        "amount": bet, "payout": payout, "house_fee": 0,
        "outcome": "win" if won else "loss",
        "result": {"number": number, "color": color, "bet_type": bet_type},
    }).execute()

    return (
        f"🎡 *Рулетка*\n\n"
        f"Твоя ставка: {bet_label}\n"
        f"Выпало: {color} *{number}*\n\n"
        f"{msg}"
    )

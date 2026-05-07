"""casino/games/coin.py — Монетка. Орёл или решка, x2."""

from __future__ import annotations
import random
import uuid
from infra.db.supabase import get_supabase_admin
from world.economy.wallet import debit, credit
from core.i18n import t

SIDES = {
    "орёл": "орёл", "орел": "орёл", "о": "орёл", "heads": "орёл",
    "решка": "решка", "р": "решка", "tails": "решка",
}


def parse_coin_choice(raw: str) -> str | None:
    return SIDES.get(raw.strip().lower())


async def play_coin(user_id: str, bet: int, language: str, choice: str = "орёл") -> str:
    success, balance = await debit(user_id, bet, "casino_bet")
    if not success:
        return t(language, "economy.insufficient_funds", balance=balance)

    result = random.choice(["орёл", "решка"])
    icon = "🦅" if result == "орёл" else "🪙"

    won = choice == result
    payout = 0

    if won:
        payout = bet * 2
        await credit(user_id, payout, "game_win")
        msg = t(language, "casino.win", amount=payout - bet)
    else:
        msg = t(language, "casino.loss", amount=bet)

    get_supabase_admin().table("casino_rounds").insert({
        "id": str(uuid.uuid4()), "user_id": user_id, "game_type": "coin",
        "amount": bet, "payout": payout, "house_fee": 0,
        "outcome": "win" if won else "loss",
        "result": {"choice": choice, "result": result},
    }).execute()

    return (
        f"🪙 *Монетка*\n\n"
        f"Твой выбор: *{choice}*\n"
        f"{icon} Выпало: *{result}*\n\n"
        f"{msg}"
    )

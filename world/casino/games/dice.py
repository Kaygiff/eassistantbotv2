"""casino/games/dice.py — Кости. Угадай: больше или меньше 7."""

from __future__ import annotations
import random
import uuid
from infra.db.supabase import get_supabase_admin
from world.economy.wallet import debit, credit
from core.i18n import t


async def play_dice(user_id: str, bet: int, language: str) -> str:
    success, balance = await debit(user_id, bet, "casino_bet")
    if not success:
        return t(language, "economy.insufficient_funds", balance=balance)

    die1 = random.randint(1, 6)
    die2 = random.randint(1, 6)
    total = die1 + die2

    # Игрок ставит на "больше 7" или "меньше 7" — рандомно выбирается
    # (в команде можно передавать выбор, но для кнопочного режима — рандом)
    player_choice = random.choice(["больше", "меньше"])

    if total == 7:
        # Ничья — возврат ставки
        await credit(user_id, bet, "casino_bet")
        outcome = "push"
        msg = f"🎲 Ровно 7 — ничья! Ставка возвращена."
        payout = bet
    elif (player_choice == "больше" and total > 7) or (player_choice == "меньше" and total < 7):
        payout = bet * 2
        outcome = "win"
        await credit(user_id, payout, "game_win")
        msg = t(language, "casino.win", amount=payout - bet)
    else:
        payout = 0
        outcome = "loss"
        msg = t(language, "casino.loss", amount=bet)

    get_supabase_admin().table("casino_rounds").insert({
        "id": str(uuid.uuid4()), "user_id": user_id, "game_type": "dice",
        "amount": bet, "payout": payout, "house_fee": 0, "outcome": outcome,
        "result": {"die1": die1, "die2": die2, "total": total, "choice": player_choice},
    }).execute()

    return (
        f"🎲 *Кости*\n\n"
        f"Твой выбор: *{player_choice} 7*\n"
        f"Выпало: [{die1}] + [{die2}] = *{total}*\n\n"
        f"{msg}"
    )

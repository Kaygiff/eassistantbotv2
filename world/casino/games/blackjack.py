"""casino/games/blackjack.py — Блэкджек."""

from __future__ import annotations
import random
import uuid
from infra.db.supabase import supabase_admin
from world.economy.wallet import debit, credit
from core.i18n import t

CARDS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
SUITS = ["♠", "♥", "♦", "♣"]


def _card_value(card: str) -> int:
    if card in ("J", "Q", "K"):
        return 10
    if card == "A":
        return 11
    return int(card)


def _hand_value(hand: list[str]) -> int:
    total = sum(_card_value(c.split()[0]) for c in hand)
    aces = sum(1 for c in hand if c.startswith("A"))
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def _deal() -> str:
    return f"{random.choice(CARDS)} {random.choice(SUITS)}"


async def play_blackjack(user_id: str, bet: int, language: str) -> str:
    success, balance = await debit(user_id, bet, "casino_bet")
    if not success:
        return t(language, "economy.insufficient_funds", balance=balance)

    player = [_deal(), _deal()]
    dealer = [_deal(), _deal()]

    p_val = _hand_value(player)
    d_val = _hand_value(dealer)

    # Упрощённый AI дилера: берёт карты до 17+
    while d_val < 17:
        dealer.append(_deal())
        d_val = _hand_value(dealer)

    p_str = " ".join(player)
    d_str = " ".join(dealer)

    if p_val > 21:
        outcome, payout = "loss", 0
        msg = t(language, "casino.loss", amount=bet)
    elif d_val > 21 or p_val > d_val:
        payout = bet * 2
        outcome = "win"
        await credit(user_id, payout, "game_win")
        msg = t(language, "casino.win", amount=payout - bet)
    elif p_val == d_val:
        payout = bet
        outcome = "push"
        await credit(user_id, bet, "casino_bet")
        msg = t(language, "casino.push")
    else:
        outcome, payout = "loss", 0
        msg = t(language, "casino.loss", amount=bet)

    supabase_admin.table("casino_rounds").insert({
        "id": str(uuid.uuid4()), "user_id": user_id, "game_type": "blackjack",
        "amount": bet, "payout": payout, "house_fee": 0, "outcome": outcome,
        "result": {"player": player, "dealer": dealer, "p_val": p_val, "d_val": d_val},
    }).execute()

    return (
        f"🃏 *Блэкджек*\n\n"
        f"Твои карты: {p_str} *(={p_val})*\n"
        f"Карты дилера: {d_str} *(={d_val})*\n\n"
        f"{msg}"
    )

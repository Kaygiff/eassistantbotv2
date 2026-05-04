"""casino/games/poker.py — Упрощённый покер (видеопокер)."""

from __future__ import annotations
import random, uuid
from infra.db.supabase import get_supabase_admin
from world.economy.wallet import debit, credit
from core.i18n import t

RANKS = ["2","3","4","5","6","7","8","9","10","J","Q","K","A"]
SUITS = ["♠","♥","♦","♣"]


def _deal_hand(n=5) -> list[str]:
    deck = [f"{r}{s}" for r in RANKS for s in SUITS]
    return random.sample(deck, n)


def _rank_hand(hand: list[str]) -> tuple[int, str]:
    ranks = sorted([r[:-1] for r in hand], key=lambda x: RANKS.index(x))
    rank_counts = {r: ranks.count(r) for r in set(ranks)}
    counts = sorted(rank_counts.values(), reverse=True)

    if counts[0] == 4:
        return 7, "Каре"
    if counts[0] == 3 and counts[1] == 2:
        return 6, "Фулл-хаус"
    if counts[0] == 3:
        return 3, "Тройка"
    if counts[0] == 2 and counts[1] == 2:
        return 2, "Две пары"
    if counts[0] == 2:
        return 1, "Пара"
    return 0, "Старшая карта"


MULTIPLIERS = {7: 8, 6: 5, 3: 3, 2: 2, 1: 1, 0: 0}


async def play_poker(user_id: str, bet: int, language: str) -> str:
    success, balance = await debit(user_id, bet, "casino_bet")
    if not success:
        return t(language, "economy.insufficient_funds", balance=balance)

    hand = _deal_hand()
    rank_val, rank_name = _rank_hand(hand)
    multiplier = MULTIPLIERS[rank_val]

    payout = bet * multiplier if multiplier > 0 else 0
    outcome = "win" if payout > 0 else "loss"

    if payout > 0:
        await credit(user_id, payout, "game_win")
        msg = t(language, "casino.win", amount=payout - bet)
    else:
        msg = t(language, "casino.loss", amount=bet)

    get_supabase_admin().table("casino_rounds").insert({
        "id": str(uuid.uuid4()), "user_id": user_id, "game_type": "poker",
        "amount": bet, "payout": payout, "house_fee": 0, "outcome": outcome,
        "result": {"hand": hand, "rank": rank_name, "multiplier": multiplier},
    }).execute()

    return f"♠️ *Покер*\n\n🃏 Карты: {' '.join(hand)}\n🏆 Комбинация: *{rank_name}* (x{multiplier})\n\n{msg}"

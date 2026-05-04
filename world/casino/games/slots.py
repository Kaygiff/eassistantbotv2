"""casino/games/slots.py — Игровые автоматы."""

from __future__ import annotations
import random
import uuid
from infra.db.supabase import supabase_admin
from world.economy.wallet import debit, credit
from core.i18n import t

SYMBOLS = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣", "🌟"]
HOUSE_FEE_PERCENT = 5

PAYOUTS = {
    ("7️⃣", "7️⃣", "7️⃣"): 10,
    ("💎", "💎", "💎"): 7,
    ("🌟", "🌟", "🌟"): 5,
    ("🍇", "🍇", "🍇"): 3,
    ("🍊", "🍊", "🍊"): 2,
    ("🍋", "🍋", "🍋"): 2,
    ("🍒", "🍒", "🍒"): 2,
}


async def play_slots(user_id: str, bet: int, language: str) -> str:
    success, balance = await debit(user_id, bet, "casino_bet")
    if not success:
        return t(language, "economy.insufficient_funds", balance=balance)

    reels = [random.choice(SYMBOLS) for _ in range(3)]
    key = tuple(reels)
    multiplier = PAYOUTS.get(key, 0)

    # Если два одинаковых — небольшой выигрыш
    if multiplier == 0 and len(set(reels)) == 2:
        multiplier = 0.5

    house_fee = int(bet * HOUSE_FEE_PERCENT / 100)
    payout = int(bet * multiplier) - house_fee if multiplier > 0 else 0
    outcome = "win" if payout > 0 else "loss"

    if payout > 0:
        await credit(user_id, payout, "game_win")
        result_text = t(language, "casino.win", amount=payout)
    else:
        result_text = t(language, "casino.loss", amount=bet)

    supabase_admin.table("casino_rounds").insert({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "game_type": "slots",
        "amount": bet,
        "payout": payout,
        "house_fee": house_fee,
        "outcome": outcome,
        "result": {"reels": reels, "multiplier": multiplier},
    }).execute()

    reel_display = " | ".join(reels)
    return f"🎰 *Слоты*\n\n[ {reel_display} ]\n\n{result_text}"

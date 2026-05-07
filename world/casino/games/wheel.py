"""casino/games/wheel.py — Колесо фортуны."""

from __future__ import annotations
import random
import uuid
from infra.db.supabase import get_supabase_admin
from world.economy.wallet import debit, credit
from core.i18n import t

# Сектора: (множитель, вес, эмодзи)
SECTORS = [
    (0,    30, "💀"),   # проигрыш — 30%
    (1.5,  25, "🟡"),   # x1.5 — 25%
    (2.0,  20, "🟠"),   # x2 — 20%
    (3.0,  12, "🔵"),   # x3 — 12%
    (5.0,   8, "🟣"),   # x5 — 8%
    (10.0,  4, "🔴"),   # x10 — 4%
    (25.0,  1, "⭐"),   # x25 — 1%
]


def _spin() -> tuple[float, str]:
    population = [(m, e) for m, w, e in SECTORS for _ in range(w)]
    return random.choice(population)


async def play_wheel(user_id: str, bet: int, language: str) -> str:
    success, balance = await debit(user_id, bet, "casino_bet")
    if not success:
        return t(language, "economy.insufficient_funds", balance=balance)

    multiplier, icon = _spin()
    payout = int(bet * multiplier) if multiplier > 0 else 0
    outcome = "win" if payout > 0 else "loss"

    # Визуализация колеса
    wheel_display = " ".join(e for _, _, e in SECTORS)

    if payout > 0:
        await credit(user_id, payout, "game_win")
        msg = t(language, "casino.win", amount=payout - bet)
    else:
        msg = t(language, "casino.loss", amount=bet)

    get_supabase_admin().table("casino_rounds").insert({
        "id": str(uuid.uuid4()), "user_id": user_id, "game_type": "wheel",
        "amount": bet, "payout": payout, "house_fee": 0, "outcome": outcome,
        "result": {"multiplier": multiplier, "sector": icon},
    }).execute()

    multiplier_text = f"x{multiplier}" if multiplier > 0 else "x0"
    return (
        f"🎠 *Колесо фортуны*\n\n"
        f"{wheel_display}\n"
        f"         ⬆️\n\n"
        f"Выпало: {icon} *{multiplier_text}*\n\n"
        f"{msg}"
    )

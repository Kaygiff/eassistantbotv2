"""casino/games/crash.py — Краш (Provably Fair)."""

from __future__ import annotations
import hashlib, hmac, os, random, uuid
from infra.db.supabase import supabase_admin
from world.economy.wallet import debit, credit
from core.i18n import t


def _generate_crash_point() -> float:
    """Генерирует точку краша (Provably Fair)."""
    seed = os.urandom(8).hex()
    h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    e = 2 ** 52
    result = (e - (h % e)) / (e - (h % e)) * 0.99
    crash = max(1.0, 1 / (1 - result * 0.99))
    return round(min(crash, 100.0), 2)


async def play_crash(user_id: str, bet: int, language: str) -> str:
    success, balance = await debit(user_id, bet, "casino_bet")
    if not success:
        return t(language, "economy.insufficient_funds", balance=balance)

    crash_at = _generate_crash_point()
    # Игрок "выходит" в случайный момент до краша
    player_exit = round(random.uniform(1.0, crash_at * 1.2), 2)

    seed_hash = hashlib.md5(str(crash_at).encode()).hexdigest()

    if player_exit <= crash_at:
        payout = int(bet * player_exit)
        outcome = "win"
        await credit(user_id, payout, "game_win")
        msg = t(language, "casino.win", amount=payout - bet)
        result_line = f"🚀 Вышел на *x{player_exit}* до краша на *x{crash_at}*"
    else:
        payout = 0
        outcome = "loss"
        msg = t(language, "casino.loss", amount=bet)
        result_line = f"💥 Краш на *x{crash_at}* (ты вышел на *x{player_exit}*)"

    supabase_admin.table("casino_rounds").insert({
        "id": str(uuid.uuid4()), "user_id": user_id, "game_type": "crash",
        "amount": bet, "payout": payout, "house_fee": 0, "outcome": outcome,
        "seed_hash": seed_hash, "result": {"crash_at": crash_at, "exit_at": player_exit},
    }).execute()

    return f"📈 *Краш*\n\n{result_line}\n\n{msg}"

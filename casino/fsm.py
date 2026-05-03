"""
casino/fsm.py — FSM для казино. Обрабатывает ввод ставки.
"""

from __future__ import annotations
from brain.context import BrainContext
from auth.session import get_fsm_data, clear_fsm_state, clear_fsm_data


async def handle_casino_fsm(ctx: BrainContext, bot, state: str) -> bool:
    user_id = str(ctx.user.id)

    if state == "casino:awaiting_bet":
        data = await get_fsm_data(user_id)
        game_type = data.get("game_type", "slots")
        try:
            bet = int(ctx.text.strip())
        except ValueError:
            await bot.send_message(ctx.chat_id, "⚠️ Введи число — размер ставки в Ecoins.")
            return True

        await clear_fsm_state(user_id)
        await clear_fsm_data(user_id)

        game_map = {
            "slots": "casino.games.slots.play_slots",
            "roulette": "casino.games.roulette.play_roulette",
            "blackjack": "casino.games.blackjack.play_blackjack",
            "crash": "casino.games.crash.play_crash",
            "poker": "casino.games.poker.play_poker",
        }

        module_path = game_map.get(game_type)
        if not module_path:
            return True

        module_name, fn_name = module_path.rsplit(".", 1)
        import importlib
        module = importlib.import_module(module_name)
        fn = getattr(module, fn_name)

        result = await fn(user_id=user_id, bet=bet, language=ctx.language)
        await bot.send_message(ctx.chat_id, result, parse_mode="Markdown")
        return True

    return False

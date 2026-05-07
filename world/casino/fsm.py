"""
casino/fsm.py — FSM для казино. Обрабатывает ввод ставки.
"""

from __future__ import annotations
from bot.brain.context import BrainContext
from api.auth.session import get_fsm_data, clear_fsm_state, clear_fsm_data


async def handle_casino_fsm(ctx: BrainContext, bot, state: str) -> bool:
    user_id = str(ctx.user.id)

    # --- Рулетка: пользователь вводит свою сумму ставки текстом ---
    if state == "casino:roulette_custom_bet":
        data = await get_fsm_data(user_id)
        bet_type = data.get("bet_type", "red")
        chat_id = data.get("chat_id", ctx.chat_id)
        message_id = data.get("message_id")

        try:
            bet = int(ctx.text.strip())
        except ValueError:
            await bot.send_message(ctx.chat_id, "⚠️ Введи число — размер ставки в Ecoins.")
            return True

        await clear_fsm_state(user_id)
        await clear_fsm_data(user_id)

        from bot.brain.handlers.casino import MIN_BET, MAX_BET
        if bet < MIN_BET:
            await bot.send_message(ctx.chat_id, f"⚠️ Минимальная ставка: *{MIN_BET} Ecoins*", parse_mode="Markdown")
            return True
        if bet > MAX_BET:
            await bot.send_message(ctx.chat_id, f"⚠️ Максимальная ставка: *{MAX_BET} Ecoins*", parse_mode="Markdown")
            return True

        from world.economy.wallet import get_balance
        balance = await get_balance(user_id)
        if balance < bet:
            await bot.send_message(ctx.chat_id, f"💸 Недостаточно средств! Баланс: *{balance} Ecoins*", parse_mode="Markdown")
            return True

        if message_id:
            from world.casino.games.roulette import play_roulette_inline
            await play_roulette_inline(
                user_id=user_id,
                bet=bet,
                language=ctx.language,
                bet_type=bet_type,
                bot=bot,
                chat_id=chat_id,
                message_id=message_id,
            )
        else:
            from world.casino.games.roulette import play_roulette
            result = await play_roulette(user_id=user_id, bet=bet, language=ctx.language, bet_type=bet_type)
            await bot.send_message(ctx.chat_id, result, parse_mode="Markdown")
        return True

    # --- Остальные игры (старый путь) ---
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

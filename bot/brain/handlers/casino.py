"""
brain/handlers/casino.py — Маршрутизация казино.
"""

from bot.brain.router import register
from bot.brain.intent import Intent
from bot.brain.context import BrainContext
from core.i18n import t


@register(Intent.CASINO_OPEN)
async def handle_casino_open(ctx: BrainContext, bot) -> None:
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎰 Слоты", callback_data="casino:slots"),
            InlineKeyboardButton(text="🎡 Рулетка", callback_data="casino:roulette"),
        ],
        [
            InlineKeyboardButton(text="🃏 Блэкджек", callback_data="casino:blackjack"),
            InlineKeyboardButton(text="📈 Краш", callback_data="casino:crash"),
        ],
        [
            InlineKeyboardButton(text="♠️ Покер", callback_data="casino:poker"),
        ],
    ])
    await bot.send_message(
        ctx.chat_id,
        f"🎰 *Казино*\n\n{t(ctx.language, 'casino.warning')}\n\n{t(ctx.language, 'casino.choose_game')}",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


@register(Intent.CASINO_SLOTS)
async def handle_slots(ctx: BrainContext, bot) -> None:
    from world.casino.games.slots import play_slots
    await _run_casino_game(ctx, bot, play_slots)


@register(Intent.CASINO_ROULETTE)
async def handle_roulette(ctx: BrainContext, bot) -> None:
    from world.casino.games.roulette import play_roulette
    await _run_casino_game(ctx, bot, play_roulette)


@register(Intent.CASINO_BLACKJACK)
async def handle_blackjack(ctx: BrainContext, bot) -> None:
    from world.casino.games.blackjack import play_blackjack
    await _run_casino_game(ctx, bot, play_blackjack)


@register(Intent.CASINO_CRASH)
async def handle_crash(ctx: BrainContext, bot) -> None:
    from world.casino.games.crash import play_crash
    await _run_casino_game(ctx, bot, play_crash)


@register(Intent.CASINO_POKER)
async def handle_poker(ctx: BrainContext, bot) -> None:
    from world.casino.games.poker import play_poker
    await _run_casino_game(ctx, bot, play_poker)


async def _run_casino_game(ctx: BrainContext, bot, game_fn) -> None:
    """Общий обработчик: проверка баланса, запуск игры, отправка результата."""
    import re
    from world.economy.wallet import get_balance

    # Извлекаем ставку из текста
    match = re.search(r"\d+", ctx.text)
    bet = int(match.group()) if match else None

    if not bet:
        await bot.send_message(
            ctx.chat_id,
            t(ctx.language, "casino.enter_bet"),
        )
        return

    balance = await get_balance(ctx.user_id)
    if balance < bet:
        await bot.send_message(
            ctx.chat_id,
            t(ctx.language, "economy.insufficient_funds", balance=balance),
            parse_mode="Markdown",
        )
        return

    result = await game_fn(user_id=ctx.user_id, bet=bet, language=ctx.language)
    await bot.send_message(ctx.chat_id, result, parse_mode="Markdown")

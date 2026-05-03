"""
brain/handlers/games.py — Мини-игры.
"""

from brain.router import register
from brain.intent import Intent
from brain.context import BrainContext


@register(Intent.GAME_QUIZ)
async def handle_quiz(ctx: BrainContext, bot) -> None:
    from casino.games.quiz import start_quiz
    await start_quiz(ctx, bot)


@register(Intent.GAME_DICE)
async def handle_dice(ctx: BrainContext, bot) -> None:
    await bot.send_dice(ctx.chat_id)


@register(Intent.GAME_TRUTH_DARE)
async def handle_truth_dare(ctx: BrainContext, bot) -> None:
    from casino.games.truth_dare import get_truth_dare
    text = await get_truth_dare(ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.GAME_WOULD_YOU)
async def handle_would_you(ctx: BrainContext, bot) -> None:
    from casino.games.would_you import get_would_you
    text = await get_would_you(ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.GAME_RIDDLE)
async def handle_riddle(ctx: BrainContext, bot) -> None:
    from casino.games.riddle import get_riddle
    text = await get_riddle(ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")

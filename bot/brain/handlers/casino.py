"""
brain/handlers/casino.py — Обработчики казино.
7 игр: слоты, рулетка, кости, монетка, мины, джокер, колесо.
"""

from __future__ import annotations
import re

from bot.brain.router import register
from bot.brain.intent import Intent
from bot.brain.context import BrainContext
from core.i18n import t
from world.economy.wallet import get_balance


MIN_BET = 10
MAX_BET = 100_000


def _casino_keyboard():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎰 Слоты", callback_data="casino:slots"),
            InlineKeyboardButton(text="🎡 Рулетка", callback_data="casino:roulette"),
        ],
        [
            InlineKeyboardButton(text="🎲 Кости", callback_data="casino:dice"),
            InlineKeyboardButton(text="🪙 Монетка", callback_data="casino:coin"),
        ],
        [
            InlineKeyboardButton(text="💣 Мины", callback_data="casino:mines"),
            InlineKeyboardButton(text="🃏 Джокер", callback_data="casino:joker"),
        ],
        [
            InlineKeyboardButton(text="🎠 Колесо", callback_data="casino:wheel"),
        ],
    ])


@register(Intent.CASINO_OPEN)
async def handle_casino_open(ctx: BrainContext, bot) -> None:
    balance = await get_balance(str(ctx.user.id))
    await bot.send_message(
        ctx.chat_id,
        (
            f"🎰 *Казино*\n\n"
            f"💰 Твой баланс: *{balance} Ecoins*\n\n"
            f"{t(ctx.language, 'casino.warning')}\n\n"
            f"Выбери игру или используй команду:\n"
            f"`/слоты <ставка>`\n"
            f"`/рулетка <к/ч/число> <ставка>`\n"
            f"`/кости <ставка>`\n"
            f"`/монетка <ставка>`\n"
            f"`/мины <ставка>`\n"
            f"`/джокер <ставка>`\n"
            f"`/колесо <ставка>`"
        ),
        parse_mode="Markdown",
        reply_markup=_casino_keyboard(),
    )


def _extract_bet(text: str) -> int | None:
    match = re.search(r"\d+", text)
    return int(match.group()) if match else None


async def _check_bet(ctx: BrainContext, bot, bet: int | None) -> bool:
    if not bet:
        await bot.send_message(ctx.chat_id, "⚠️ Укажи ставку. Например: `/слоты 100`", parse_mode="Markdown")
        return False
    if bet < MIN_BET:
        await bot.send_message(ctx.chat_id, f"⚠️ Минимальная ставка: *{MIN_BET} Ecoins*", parse_mode="Markdown")
        return False
    if bet > MAX_BET:
        await bot.send_message(ctx.chat_id, f"⚠️ Максимальная ставка: *{MAX_BET} Ecoins*", parse_mode="Markdown")
        return False
    balance = await get_balance(str(ctx.user.id))
    if balance < bet:
        await bot.send_message(ctx.chat_id, t(ctx.language, "economy.insufficient_funds", balance=balance), parse_mode="Markdown")
        return False
    return True


@register(Intent.CASINO_SLOTS)
async def handle_slots(ctx: BrainContext, bot) -> None:
    bet = _extract_bet(ctx.text)
    if not await _check_bet(ctx, bot, bet):
        return
    from world.casino.games.slots import play_slots
    sent = await bot.send_message(ctx.chat_id, "🎰 *Слоты*\n\n_Запуск..._", parse_mode="Markdown")
    await play_slots(
        user_id=str(ctx.user.id),
        bet=bet,
        language=ctx.language,
        bot=bot,
        chat_id=ctx.chat_id,
        message_id=sent.message_id,
    )


@register(Intent.CASINO_ROULETTE)
async def handle_roulette(ctx: BrainContext, bot) -> None:
    from world.casino.games.roulette import play_roulette, _parse_bet_type
    parts = ctx.text.strip().split()
    bet_type_raw = None
    bet = None
    for part in parts[1:]:
        if bet is None:
            try:
                bet = int(part)
            except ValueError:
                if bet_type_raw is None:
                    bet_type_raw = part
        else:
            break
    bet_type = _parse_bet_type(bet_type_raw) if bet_type_raw else "red"
    if bet_type is None:
        await bot.send_message(ctx.chat_id, "⚠️ Формат: `/рулетка к 100` / `/рулетка ч 100` / `/рулетка 17 100`", parse_mode="Markdown")
        return
    if not await _check_bet(ctx, bot, bet):
        return
    result = await play_roulette(user_id=str(ctx.user.id), bet=bet, language=ctx.language, bet_type=bet_type)
    await bot.send_message(ctx.chat_id, result, parse_mode="Markdown")


@register(Intent.CASINO_DICE)
async def handle_dice(ctx: BrainContext, bot) -> None:
    bet = _extract_bet(ctx.text)
    if not await _check_bet(ctx, bot, bet):
        return
    from world.casino.games.dice import play_dice
    result = await play_dice(user_id=str(ctx.user.id), bet=bet, language=ctx.language)
    await bot.send_message(ctx.chat_id, result, parse_mode="Markdown")


@register(Intent.CASINO_COIN)
async def handle_coin(ctx: BrainContext, bot) -> None:
    from world.casino.games.coin import play_coin, parse_coin_choice
    parts = ctx.text.strip().split()
    choice = "орёл"
    bet = None
    for part in parts[1:]:
        parsed = parse_coin_choice(part)
        if parsed and choice == "орёл":
            choice = parsed
        else:
            try:
                bet = int(part)
            except ValueError:
                pass
    if not await _check_bet(ctx, bot, bet):
        return
    result = await play_coin(user_id=str(ctx.user.id), bet=bet, language=ctx.language, choice=choice)
    await bot.send_message(ctx.chat_id, result, parse_mode="Markdown")


@register(Intent.CASINO_MINES)
async def handle_mines(ctx: BrainContext, bot) -> None:
    bet = _extract_bet(ctx.text)
    if not await _check_bet(ctx, bot, bet):
        return
    from world.casino.games.mines import start_mines
    text, keyboard = await start_mines(user_id=str(ctx.user.id), bet=bet, language=ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown", reply_markup=keyboard)


@register(Intent.CASINO_JOKER)
async def handle_joker(ctx: BrainContext, bot) -> None:
    bet = _extract_bet(ctx.text)
    if not await _check_bet(ctx, bot, bet):
        return
    from world.casino.games.joker import start_joker
    text, keyboard = await start_joker(user_id=str(ctx.user.id), bet=bet, language=ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown", reply_markup=keyboard)


@register(Intent.CASINO_WHEEL)
async def handle_wheel(ctx: BrainContext, bot) -> None:
    bet = _extract_bet(ctx.text)
    if not await _check_bet(ctx, bot, bet):
        return
    from world.casino.games.wheel import play_wheel
    result = await play_wheel(user_id=str(ctx.user.id), bet=bet, language=ctx.language)
    await bot.send_message(ctx.chat_id, result, parse_mode="Markdown")

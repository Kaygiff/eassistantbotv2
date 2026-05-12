"""
brain/handlers/casino.py — Обработчики казино.
7 игр: слоты, рулетка, кости, монетка, мины, джокер, колесо.

Формат команд:
  слоты 500
  рулетка к|ч|чет|нечет|мало|много|0-36  500
  кости б|м|р  500
  монетка о|р  500
  мины 500
  джокер 500
  колесо 500
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

# Псевдонимы для костей: б/м/р → больше/меньше/ровно
_DICE_ALIASES: dict[str, str] = {
    "б": "больше", "больше": "больше", "big": "больше",
    "м": "меньше", "меньше": "меньше", "small": "меньше",
    "р": "ровно",  "ровно": "ровно",   "seven": "ровно", "7": "ровно",
}


def _casino_keyboard():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎰 Слоты",   callback_data="casino:slots"),
            InlineKeyboardButton(text="🎡 Рулетка", callback_data="casino:roulette"),
        ],
        [
            InlineKeyboardButton(text="🎲 Кости",   callback_data="casino:dice"),
            InlineKeyboardButton(text="🪙 Монетка",  callback_data="casino:coin"),
        ],
        [
            InlineKeyboardButton(text="💣 Мины",    callback_data="casino:mines"),
            InlineKeyboardButton(text="🃏 Джокер",  callback_data="casino:joker"),
        ],
        [
            InlineKeyboardButton(text="🎠 Колесо",  callback_data="casino:wheel"),
        ],
    ])


def _parse_args(text: str) -> tuple[list[str], int | None]:
    """
    Разбирает строку на слова-аргументы и последнее число как ставку.
    Возвращает (слова без первого слова-команды, ставка | None).
    """
    parts = text.strip().split()
    words: list[str] = []
    bet: int | None = None
    for part in parts[1:]:
        try:
            bet = int(part)
        except ValueError:
            words.append(part.lower())
    return words, bet


async def _check_bet(ctx: BrainContext, bot, bet: int | None, hint: str = "100") -> bool:
    if not bet:
        game = ctx.text.strip().split()[0]
        await bot.send_message(
            ctx.chat_id,
            f"⚠️ Укажи ставку. Например: `{game} {hint}`",
            parse_mode="Markdown",
        )
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


# ---------------------------------------------------------------------------
# Меню казино
# ---------------------------------------------------------------------------

@register(Intent.CASINO_OPEN)
async def handle_casino_open(ctx: BrainContext, bot) -> None:
    balance = await get_balance(str(ctx.user.id))
    await bot.send_message(
        ctx.chat_id,
        (
            f"🎰 *Казино*\n\n"
            f"💰 Твой баланс: *{balance} Ecoins*\n\n"
            f"{t(ctx.language, 'casino.warning')}\n\n"
            f"{t(ctx.language, 'casino.choose_game')}"
        ),
        parse_mode="Markdown",
        reply_markup=_casino_keyboard(),
    )


# ---------------------------------------------------------------------------
# Слоты  →  слоты 500
# ---------------------------------------------------------------------------

@register(Intent.CASINO_SLOTS)
async def handle_slots(ctx: BrainContext, bot) -> None:
    _, bet = _parse_args(ctx.text)
    if not await _check_bet(ctx, bot, bet, "500"):
        return
    from world.casino.games.slots import play_slots
    await play_slots(user_id=str(ctx.user.id), bet=bet, language=ctx.language, bot=bot, chat_id=ctx.chat_id)


# ---------------------------------------------------------------------------
# Рулетка  →  рулетка к|ч|чет|нечет|мало|много|0-36  500
# ---------------------------------------------------------------------------

@register(Intent.CASINO_ROULETTE)
async def handle_roulette(ctx: BrainContext, bot) -> None:
    from world.casino.games.roulette import play_roulette, _parse_bet_type, open_roulette

    words, bet = _parse_args(ctx.text)

    # нет ставки или нет типа → открываем inline
    if not bet or not words:
        await open_roulette(user_id=str(ctx.user.id), language=ctx.language, bot=bot, chat_id=ctx.chat_id)
        return

    bet_type = _parse_bet_type(words[0])
    if bet_type is None:
        await open_roulette(user_id=str(ctx.user.id), language=ctx.language, bot=bot, chat_id=ctx.chat_id)
        return

    if not await _check_bet(ctx, bot, bet, "к 500"):
        return
    result = await play_roulette(user_id=str(ctx.user.id), bet=bet, language=ctx.language, bet_type=bet_type)
    await bot.send_message(ctx.chat_id, result, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# Кости  →  кости б|м|р 500
# ---------------------------------------------------------------------------

@register(Intent.CASINO_DICE)
async def handle_dice(ctx: BrainContext, bot) -> None:
    from world.casino.games.dice import play_dice, open_dice

    words, bet = _parse_args(ctx.text)
    choice = _DICE_ALIASES.get(words[0]) if words else None

    # нет ставки → открываем inline
    if not bet:
        await open_dice(user_id=str(ctx.user.id), language=ctx.language, bot=bot, chat_id=ctx.chat_id)
        return

    if not await _check_bet(ctx, bot, bet, "б 500"):
        return
    result = await play_dice(user_id=str(ctx.user.id), bet=bet, language=ctx.language, choice=choice)
    await bot.send_message(ctx.chat_id, result, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# Монетка  →  монетка о|р 500
# ---------------------------------------------------------------------------

@register(Intent.CASINO_COIN)
async def handle_coin(ctx: BrainContext, bot) -> None:
    from world.casino.games.coin import play_coin, parse_coin_choice, open_coin

    words, bet = _parse_args(ctx.text)
    choice = parse_coin_choice(words[0]) if words else None

    # нет ставки → открываем inline
    if not bet:
        await open_coin(user_id=str(ctx.user.id), language=ctx.language, bot=bot, chat_id=ctx.chat_id)
        return

    if not await _check_bet(ctx, bot, bet, "о 500"):
        return
    result = await play_coin(
        user_id=str(ctx.user.id), bet=bet, language=ctx.language,
        choice=choice or "орёл",
    )
    await bot.send_message(ctx.chat_id, result, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# Мины  →  мины 500  (inline-флоу со ставкой предзаполненной)
# ---------------------------------------------------------------------------

@register(Intent.CASINO_MINES)
async def handle_mines(ctx: BrainContext, bot) -> None:
    from world.casino.games.mines import open_mines, start_mines_inline
    _, bet = _parse_args(ctx.text)
    if bet and await _check_bet(ctx, bot, bet, "500"):
        msg = await bot.send_message(ctx.chat_id, "💣 *Мины* — запускаю...", parse_mode="Markdown")
        await start_mines_inline(
            user_id=str(ctx.user.id), bet=bet, language=ctx.language,
            bot=bot, chat_id=ctx.chat_id, message_id=msg.message_id,
        )
    else:
        await open_mines(
            user_id=str(ctx.user.id), language=ctx.language,
            bot=bot, chat_id=ctx.chat_id, initial_bet=0,
        )


# ---------------------------------------------------------------------------
# Джокер  →  джокер 500  (сразу стартует / без ставки — экран выбора)
# ---------------------------------------------------------------------------

@register(Intent.CASINO_JOKER)
async def handle_joker(ctx: BrainContext, bot) -> None:
    from world.casino.games.joker import open_joker, start_joker_inline
    _, bet = _parse_args(ctx.text)
    if bet and await _check_bet(ctx, bot, bet, "500"):
        msg = await bot.send_message(ctx.chat_id, "🃏 *Джокер* — запускаю...", parse_mode="Markdown")
        await start_joker_inline(
            user_id=str(ctx.user.id), bet=bet, language=ctx.language,
            bot=bot, chat_id=ctx.chat_id, message_id=msg.message_id,
        )
    else:
        await open_joker(
            user_id=str(ctx.user.id), language=ctx.language,
            bot=bot, chat_id=ctx.chat_id, initial_bet=0,
        )


# ---------------------------------------------------------------------------
# Колесо  →  колесо 500  (сразу результат / без ставки — экран выбора)
# ---------------------------------------------------------------------------

@register(Intent.CASINO_WHEEL)
async def handle_wheel(ctx: BrainContext, bot) -> None:
    from world.casino.games.wheel import open_wheel, play_wheel
    _, bet = _parse_args(ctx.text)
    if bet and await _check_bet(ctx, bot, bet, "500"):
        result = await play_wheel(user_id=str(ctx.user.id), bet=bet, language=ctx.language)
        await bot.send_message(ctx.chat_id, result, parse_mode="Markdown")
    else:
        await open_wheel(
            user_id=str(ctx.user.id), language=ctx.language,
            bot=bot, chat_id=ctx.chat_id, initial_bet=0,
        )

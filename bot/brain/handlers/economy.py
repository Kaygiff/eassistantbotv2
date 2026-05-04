"""
brain/handlers/economy.py — Баланс, ежедневный бонус, переводы, рефералы.
"""

from bot.brain.router import register
from bot.brain.intent import Intent
from bot.brain.context import BrainContext
from core.i18n import t


@register(Intent.BALANCE)
async def handle_balance(ctx: BrainContext, bot) -> None:
    from world.economy.wallet import get_balance
    balance = await get_balance(ctx.user_id)
    await bot.send_message(
        ctx.chat_id,
        t(ctx.language, "economy.balance", balance=balance),
        parse_mode="Markdown",
    )


@register(Intent.DAILY_BONUS)
async def handle_daily_bonus(ctx: BrainContext, bot) -> None:
    from world.economy.daily import claim_daily_bonus
    result = await claim_daily_bonus(ctx.user_id, ctx.language)
    await bot.send_message(ctx.chat_id, result, parse_mode="Markdown")


@register(Intent.TRANSFER)
async def handle_transfer(ctx: BrainContext, bot) -> None:
    # Парсим: /transfer @username 100
    import re
    match = re.search(r"@(\w+)\s+(\d+)", ctx.text)
    if not match:
        await bot.send_message(
            ctx.chat_id,
            "💸 Формат: `/transfer @username количество`",
            parse_mode="Markdown",
        )
        return

    target_username, amount_str = match.group(1), match.group(2)
    amount = int(amount_str)

    from world.economy.wallet import transfer_ecoins
    result = await transfer_ecoins(
        from_user_id=ctx.user_id,
        to_username=target_username,
        amount=amount,
        language=ctx.language,
    )
    await bot.send_message(ctx.chat_id, result, parse_mode="Markdown")


@register(Intent.REFERRAL)
async def handle_referral(ctx: BrainContext, bot) -> None:
    from world.economy.referral import get_referral_info
    info = await get_referral_info(ctx.user_id, ctx.telegram_id, ctx.language)
    await bot.send_message(ctx.chat_id, info, parse_mode="Markdown")


@register(Intent.BALANCE)  # временно переиспользуем, лучше добавить отдельный интент
async def handle_leaderboard_top(ctx: BrainContext, bot) -> None:
    pass  # уже есть handle_balance выше

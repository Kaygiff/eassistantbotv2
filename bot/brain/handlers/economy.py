"""
brain/handlers/economy.py — Баланс, ежедневный бонус, переводы, рефералы, лидеры.
"""

import re
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
    """Перевод через реплай: 'передать 100' в ответ на сообщение пользователя."""
    if not ctx.is_group:
        return

    # Нужен реплай
    if not ctx.reply_to_user_telegram_id:
        return

    # Парсим сумму из текста
    match = re.search(r"\d+", ctx.text)
    if not match:
        return

    amount = int(match.group())
    if amount <= 0:
        return

    # Нельзя переводить самому себе
    if ctx.reply_to_user_telegram_id == ctx.telegram_id:
        return

    # Находим получателя по telegram_id
    from infra.db.supabase import get_supabase_admin
    res = (
        get_supabase_admin()
        .table("users")
        .select("id, first_name, username")
        .eq("telegram_id", ctx.reply_to_user_telegram_id)
        .maybe_single()
        .execute()
    )
    if not res.data:
        return

    to_user = res.data
    to_user_id = to_user["id"]

    from world.economy.wallet import debit, credit
    success, new_balance = await debit(ctx.user_id, amount, "transfer_out", to_user_id)
    if not success:
        await bot.send_message(
            ctx.chat_id,
            t(ctx.language, "economy.insufficient_funds", balance=new_balance),
            parse_mode="Markdown",
        )
        return

    await credit(to_user_id, amount, "transfer_in", ctx.user_id)

    # Уведомляем получателя
    from_name = ctx.user.first_name or f"@{ctx.user.username}" if ctx.user else "Пользователь"
    from infra.notifications.sender import notify_user
    await notify_user(to_user_id, f"💰 *{from_name}* перевёл тебе *{amount} Ecoins*!")

    to_name = to_user.get("first_name") or f"@{to_user.get('username', '?')}"
    await bot.send_message(
        ctx.chat_id,
        f"✅ Переведено *{amount} Ecoins* → *{to_name}*\n💼 Твой баланс: *{new_balance} Ecoins*",
        parse_mode="Markdown",
    )


@register(Intent.REFERRAL)
async def handle_referral(ctx: BrainContext, bot) -> None:
    from world.economy.referral import get_referral_info
    info = await get_referral_info(ctx.user_id, ctx.telegram_id, ctx.language)
    await bot.send_message(ctx.chat_id, info, parse_mode="Markdown")


@register(Intent.LEADERBOARD)
async def handle_leaderboard(ctx: BrainContext, bot) -> None:
    from world.economy.leaderboard import get_leaderboard_text
    text = await get_leaderboard_text(language=ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")

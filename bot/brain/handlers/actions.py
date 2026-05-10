"""
brain/handlers/actions.py — Действия и чёрный список.
"""

from bot.brain.router import register
from bot.brain.intent import Intent
from bot.brain.context import BrainContext


@register(Intent.ACTION_DO)
async def handle_action(ctx: BrainContext, bot) -> None:
    from world.virtual_world.actions.service import perform_action
    await perform_action(ctx, bot)


@register(Intent.BLACKLIST_ADD)
async def handle_blacklist_add(ctx: BrainContext, bot) -> None:
    # Только через реплай
    if not ctx.reply_to_user_telegram_id:
        await bot.send_message(
            ctx.chat_id,
            "🚫 Ответь на сообщение пользователя которого хочешь заблокировать.",
            reply_to_message_id=ctx.message_id,
        )
        return

    from world.virtual_world.blacklist.service import add_to_blacklist
    text = await add_to_blacklist(
        blocker_id=str(ctx.user.id),
        blocked_telegram_id=ctx.reply_to_user_telegram_id,
        language=ctx.language,
    )
    await bot.send_message(
        ctx.chat_id, text,
        parse_mode="Markdown",
        reply_to_message_id=ctx.message_id,
    )


@register(Intent.BLACKLIST_REMOVE)
async def handle_blacklist_remove(ctx: BrainContext, bot) -> None:
    # Только через реплай
    if not ctx.reply_to_user_telegram_id:
        await bot.send_message(
            ctx.chat_id,
            "✅ Ответь на сообщение пользователя которого хочешь разблокировать.",
            reply_to_message_id=ctx.message_id,
        )
        return

    from world.virtual_world.blacklist.service import remove_from_blacklist_by_telegram_id
    text = await remove_from_blacklist_by_telegram_id(
        blocker_id=str(ctx.user.id),
        blocked_telegram_id=ctx.reply_to_user_telegram_id,
        language=ctx.language,
    )
    await bot.send_message(
        ctx.chat_id, text,
        parse_mode="Markdown",
        reply_to_message_id=ctx.message_id,
    )


@register(Intent.BLACKLIST_VIEW)
async def handle_blacklist_view(ctx: BrainContext, bot) -> None:
    from world.virtual_world.blacklist.service import get_blacklist
    text, keyboard = await get_blacklist(str(ctx.user.id))
    await bot.send_message(
        ctx.chat_id, text,
        parse_mode="Markdown",
        reply_markup=keyboard,
        reply_to_message_id=ctx.message_id,
    )

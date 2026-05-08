"""
brain/handlers/relationships.py — Отношения и браки.

Команды через reply:
  встречаться  → RELATIONSHIP_PROPOSE
  расстаться   → RELATIONSHIP_BREAKUP
  брак         → MARRIAGE_PROPOSE
  развод       → MARRIAGE_DIVORCE

Команды без reply:
  мои отношения / мой брак → RELATIONSHIP_STATUS
"""

from bot.brain.router import register
from bot.brain.intent import Intent
from bot.brain.context import BrainContext


async def _get_reply_target(ctx: BrainContext):
    """Возвращает User из reply. Если reply нет — None."""
    if not ctx.reply_to_user_telegram_id:
        return None
    from api.auth.identity import get_user_by_telegram_id
    return await get_user_by_telegram_id(ctx.reply_to_user_telegram_id)


# ---------------------------------------------------------------------------

@register(Intent.RELATIONSHIP_PROPOSE)
async def handle_propose_dating(ctx: BrainContext, bot) -> None:
    target = await _get_reply_target(ctx)
    if not target:
        await bot.send_message(
            ctx.chat_id,
            "💌 Ответь на сообщение человека командой «встречаться», чтобы предложить отношения.",
        )
        return
    from world.virtual_world.relationships.service import propose_dating
    text = await propose_dating(ctx.user, target, bot)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.RELATIONSHIP_STATUS)
async def handle_relationship_status(ctx: BrainContext, bot) -> None:
    from world.virtual_world.relationships.service import get_relationship_status
    text = await get_relationship_status(ctx.user_id)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.RELATIONSHIP_BREAKUP)
async def handle_breakup(ctx: BrainContext, bot) -> None:
    from world.virtual_world.relationships.service import breakup
    text = await breakup(ctx.user_id)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.MARRIAGE_PROPOSE)
async def handle_propose_marriage(ctx: BrainContext, bot) -> None:
    target = await _get_reply_target(ctx)
    if not target:
        await bot.send_message(
            ctx.chat_id,
            "💍 Ответь на сообщение партнёра командой «брак», чтобы сделать предложение.",
        )
        return
    from world.virtual_world.relationships.service import propose_marriage
    text = await propose_marriage(ctx.user, target, bot)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.MARRIAGE_DIVORCE)
async def handle_divorce(ctx: BrainContext, bot) -> None:
    from world.virtual_world.relationships.service import divorce
    text = await divorce(ctx.user_id)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")

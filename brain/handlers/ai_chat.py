"""
brain/handlers/ai_chat.py — Основной AI-диалог.
"""

from brain.router import register
from brain.intent import Intent
from brain.context import BrainContext
from i18n import t
from safety.content_moderation import moderate_text


@register(Intent.AI_CHAT)
async def handle_ai_chat(ctx: BrainContext, bot) -> None:
    # Показываем "печатает..."
    await bot.send_chat_action(ctx.chat_id, "typing")

    # Модерация входящего текста
    is_safe, reason = await moderate_text(ctx.text)
    if not is_safe:
        await bot.send_message(ctx.chat_id, t(ctx.language, "common.error"))
        return

    from services.ai_chat.chat import get_ai_response
    response = await get_ai_response(
        user_id=ctx.user_id,
        user_message=ctx.text,
        language=ctx.language,
        assistant_name=ctx.assistant_name,
    )

    await bot.send_message(ctx.chat_id, response)

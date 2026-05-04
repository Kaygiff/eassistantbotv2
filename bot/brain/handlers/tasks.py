"""
brain/handlers/tasks.py — Задачи и напоминания.
"""

from bot.brain.router import register
from bot.brain.intent import Intent
from bot.brain.context import BrainContext


@register(Intent.TASK_CREATE)
async def handle_task_create(ctx: BrainContext, bot) -> None:
    from services.tasks.task_service import create_task_from_text
    text = await create_task_from_text(ctx.user_id, ctx.text, ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.TASK_LIST)
async def handle_task_list(ctx: BrainContext, bot) -> None:
    from services.tasks.task_service import get_task_list
    text = await get_task_list(ctx.user_id, ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.TASK_DONE)
async def handle_task_done(ctx: BrainContext, bot) -> None:
    from services.tasks.task_service import mark_task_done
    text = await mark_task_done(ctx.user_id, ctx.text, ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")


@register(Intent.REMINDER_CREATE)
async def handle_reminder_create(ctx: BrainContext, bot) -> None:
    from services.tasks.task_service import create_reminder_from_text
    text = await create_reminder_from_text(ctx.user_id, ctx.text, ctx.language)
    await bot.send_message(ctx.chat_id, text, parse_mode="Markdown")

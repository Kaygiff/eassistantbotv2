"""casino/games/quiz.py — Викторина."""

from __future__ import annotations
import json
from db.supabase import supabase_admin
from brain.context import BrainContext


async def start_quiz(ctx: BrainContext, bot) -> None:
    res = (
        supabase_admin.table("quiz_questions")
        .select("*")
        .eq("language", ctx.language)
        .limit(100)
        .execute()
    )
    import random
    questions = res.data or []
    if not questions:
        await bot.send_message(ctx.chat_id, "📚 Вопросы для викторины ещё загружаются.")
        return

    q = random.choice(questions)
    options = json.loads(q["options"]) if isinstance(q["options"], str) else q["options"]

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=opt, callback_data=f"quiz:{q['id']}:{i}")]
        for i, opt in enumerate(options)
    ])
    await bot.send_message(
        ctx.chat_id,
        f"❓ *Викторина*\n\n{q['question']}",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

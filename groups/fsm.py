"""
groups/fsm.py — FSM состояния для групповых настроек.
"""

from __future__ import annotations
from brain.context import BrainContext
from auth.session import clear_fsm_state
from groups.settings import save_welcome_message


async def handle_group_fsm(ctx: BrainContext, bot, state: str) -> bool:
    user_id = str(ctx.user.id)

    if state == "group:awaiting_welcome":
        if not ctx.group_id:
            await clear_fsm_state(user_id)
            return True
        await save_welcome_message(ctx.group_id, ctx.text)
        await clear_fsm_state(user_id)
        await bot.send_message(ctx.chat_id, "✅ Приветственное сообщение сохранено!")
        return True

    if state == "group:awaiting_warn_reason":
        await clear_fsm_state(user_id)
        return True

    return False

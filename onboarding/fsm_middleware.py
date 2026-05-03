"""
onboarding/fsm_middleware.py — Middleware обработки FSM-состояний.
Перехватывает текстовые сообщения ПЕРЕД передачей в Brain
и обрабатывает их если пользователь находится в каком-либо FSM-диалоге.

Порядок проверки FSM:
  1. Онбординг
  2. Настройки профиля
  3. Питомец (имя нового питомца)
  4. Задачи / напоминания
  5. Перевод монет
  6. Группы (приветствие, причина варна)
  7. События
  8. Семья / отношения
"""

from __future__ import annotations
import logging

from brain.context import BrainContext
from auth.session import get_fsm_state

logger = logging.getLogger(__name__)


async def handle_fsm(ctx: BrainContext, bot) -> bool:
    """
    Проверяет активное FSM-состояние и обрабатывает сообщение.
    Возвращает True если сообщение было обработано FSM (не передавать в Brain).
    Возвращает False если FSM не активен — передавать в Brain.
    """
    if not ctx.user:
        return False

    user_id = str(ctx.user.id)
    state = await get_fsm_state(user_id)

    if not state:
        return False

    # --- Онбординг ---
    if state.startswith("onboarding:"):
        from onboarding.flow import handle_onboarding_text
        return await handle_onboarding_text(ctx, bot)

    # --- Настройки профиля ---
    if state.startswith("settings:"):
        from onboarding.profile_edit import handle_profile_edit_fsm
        return await handle_profile_edit_fsm(ctx, bot, state)

    # --- Питомец: ввод имени ---
    if state == "pet:naming":
        from virtual_world.pets.service import handle_pet_naming
        return await handle_pet_naming(ctx, bot)

    # --- Задачи ---
    if state.startswith("task:") or state.startswith("reminder:"):
        from services.tasks.task_service import handle_task_fsm
        return await handle_task_fsm(ctx, bot, state)

    # --- Перевод монет ---
    if state.startswith("transfer:"):
        from economy.wallet import handle_transfer_fsm
        return await handle_transfer_fsm(ctx, bot, state)

    # --- Казино (ставка) ---
    if state.startswith("casino:"):
        from casino.fsm import handle_casino_fsm
        return await handle_casino_fsm(ctx, bot, state)

    # --- Группа ---
    if state.startswith("group:"):
        from groups.fsm import handle_group_fsm
        return await handle_group_fsm(ctx, bot, state)

    # --- События ---
    if state.startswith("event:"):
        from virtual_world.events.service import handle_event_fsm
        return await handle_event_fsm(ctx, bot, state)

    # --- Отношения ---
    if state.startswith("relationship:"):
        from virtual_world.relationships.service import handle_relationship_fsm
        return await handle_relationship_fsm(ctx, bot, state)

    # --- Семья ---
    if state.startswith("family:"):
        from virtual_world.family.service import handle_family_fsm
        return await handle_family_fsm(ctx, bot, state)

    return False

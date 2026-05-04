"""
virtual_world/pets/decay.py — Логика деградации показателей питомца.
Вызывается из Celery-задачи queue/tasks.py каждые 30 минут.
Отдельный файл для чистоты — бизнес-логика не в таске.
"""

from __future__ import annotations
import logging
from typing import Any

from infra.db.supabase import supabase_admin
from infra.notifications.sender import notify_user

logger = logging.getLogger(__name__)

# Значения деградации за один тик (30 минут)
HUNGER_DECAY = 5
ENERGY_DECAY = 3

# Пороги для уведомлений
NOTIFY_THRESHOLD_LOW = 20   # уведомить хозяина если показатель упал ниже
NOTIFY_THRESHOLD_SICK = 0   # питомец заболевает при 0


async def process_single_pet(pet: dict[str, Any]) -> None:
    """Обрабатывает деградацию одного питомца."""
    if pet.get("is_dead") or pet.get("is_sick"):
        # Больной питомец деградирует быстрее
        hunger_decay = HUNGER_DECAY * 2 if pet.get("is_sick") else HUNGER_DECAY
        energy_decay = ENERGY_DECAY * 2 if pet.get("is_sick") else ENERGY_DECAY
    else:
        hunger_decay = HUNGER_DECAY
        energy_decay = ENERGY_DECAY

    new_hunger = max(0, pet["hunger"] - hunger_decay)
    new_energy = max(0, pet["energy"] - energy_decay)

    updates: dict[str, Any] = {
        "hunger": new_hunger,
        "energy": new_energy,
    }

    # Определяем настроение
    if new_hunger == 0 or new_energy == 0:
        if pet.get("is_sick"):
            # Уже болен и показатели на нуле — умирает
            updates["is_dead"] = True
            updates["mood"] = "sad"
            await _notify_death(pet)
        else:
            updates["is_sick"] = True
            updates["mood"] = "sick"
            await _notify_sick(pet)
    elif new_hunger < 30 or new_energy < 30:
        updates["mood"] = "sad"
        # Уведомляем если только что упало ниже порога
        if pet["hunger"] >= 30 or pet["energy"] >= 30:
            await _notify_low(pet, new_hunger, new_energy)
    elif new_hunger > 70 and new_energy > 70:
        updates["mood"] = "happy"
    else:
        updates["mood"] = "neutral"

    supabase_admin.table("pets").update(updates).eq("id", pet["id"]).execute()


async def process_all_pets() -> int:
    """
    Запускает деградацию для всех живых питомцев.
    Возвращает количество обработанных питомцев.
    Вызывается из queue/tasks.pet_decay_tick.
    """
    res = supabase_admin.table("pets").select("*").eq("is_dead", False).execute()
    pets = res.data or []

    for pet in pets:
        try:
            await process_single_pet(pet)
        except Exception as e:
            logger.error(f"[PetDecay] Error processing pet {pet['id']}: {e}")

    logger.info(f"[PetDecay] Processed {len(pets)} pets")
    return len(pets)


async def _notify_sick(pet: dict) -> None:
    """Уведомляет хозяина что питомец заболел."""
    try:
        await notify_user(
            pet["user_id"],
            f"🤒 Твой питомец *{pet['name']}* заболел!\n\n"
            f"Вылечи его командой /pet → Вылечить (стоит 50 Ecoins)",
        )
    except Exception:
        pass


async def _notify_death(pet: dict) -> None:
    """Уведомляет хозяина о смерти питомца."""
    try:
        await notify_user(
            pet["user_id"],
            f"💀 Твой питомец *{pet['name']}* умер...\n\n"
            f"Ты можешь завести нового питомца командой /pet",
        )
    except Exception:
        pass


async def _notify_low(pet: dict, hunger: int, energy: int) -> None:
    """Уведомляет хозяина о низких показателях."""
    try:
        issues = []
        if hunger < 30:
            issues.append(f"🍖 Сытость: {hunger}%")
        if energy < 30:
            issues.append(f"⚡ Энергия: {energy}%")

        if issues:
            await notify_user(
                pet["user_id"],
                f"⚠️ Твой питомец *{pet['name']}* нуждается в помощи!\n\n"
                + "\n".join(issues)
                + "\n\nИспользуй /pet чтобы покормить или поиграть с ним.",
            )
    except Exception:
        pass

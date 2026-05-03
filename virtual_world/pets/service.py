"""
virtual_world/pets/service.py — Все операции с питомцами-тамагочи.
"""

from __future__ import annotations
import uuid
import logging

from db.supabase import supabase_admin
from brain.context import BrainContext
from auth.session import get_fsm_data, clear_fsm_state, clear_fsm_data
from i18n import t

logger = logging.getLogger(__name__)

HEAL_COST = 50  # Ecoins


async def _get_pet(user_id: str) -> dict | None:
    res = supabase_admin.table("pets").select("*").eq("user_id", user_id).maybe_single().execute()
    return res.data


async def get_pet_status(user_id: str, language: str) -> str:
    pet = await _get_pet(user_id)
    if not pet:
        return f"🐾 У тебя нет питомца.\n\nНапиши *завести питомца* чтобы завести!"
    if pet["is_dead"]:
        return f"💀 Твой питомец *{pet['name']}* умер...\n\nНапиши *завести питомца* чтобы завести нового."

    species_icons = {"cat": "🐱", "dog": "🐶", "rabbit": "🐰", "hamster": "🐹", "fox": "🦊", "dragon": "🐉"}
    icon = species_icons.get(pet["species"], "🐾")
    mood_icons = {"happy": "😊", "neutral": "😐", "sad": "😢", "sick": "🤒"}

    return t(language, "pets.status",
        name=pet["name"],
        species=f"{icon} {pet['species']}",
        mood=mood_icons.get(pet["mood"], "😐"),
        hunger=pet["hunger"],
        energy=pet["energy"],
        level=pet["level"],
    )


async def feed_pet(user_id: str, language: str) -> str:
    pet = await _get_pet(user_id)
    if not pet:
        return "🐾 У тебя нет питомца."
    if pet["is_dead"]:
        return "💀 Питомец умер."

    new_hunger = min(100, pet["hunger"] + 20)
    supabase_admin.table("pets").update({"hunger": new_hunger}).eq("id", pet["id"]).execute()
    return t(language, "pets.fed", name=pet["name"])


async def play_with_pet(user_id: str, language: str) -> str:
    pet = await _get_pet(user_id)
    if not pet:
        return "🐾 У тебя нет питомца."
    if pet["is_dead"]:
        return "💀 Питомец умер."

    new_energy = min(100, pet["energy"] + 15)
    supabase_admin.table("pets").update({"energy": new_energy}).eq("id", pet["id"]).execute()
    return t(language, "pets.played", name=pet["name"])


async def heal_pet(user_id: str, language: str) -> str:
    pet = await _get_pet(user_id)
    if not pet:
        return "🐾 У тебя нет питомца."
    if not pet["is_sick"]:
        return f"💚 *{pet['name']}* здоров!"

    from economy.wallet import debit
    success, balance = await debit(user_id, HEAL_COST, "pet_heal")
    if not success:
        return t(language, "economy.insufficient_funds", balance=balance)

    supabase_admin.table("pets").update({
        "is_sick": False,
        "mood": "happy",
        "hunger": 50,
        "energy": 50,
    }).eq("id", pet["id"]).execute()

    return t(language, "pets.healed", name=pet["name"])


async def handle_pet_naming(ctx: BrainContext, bot) -> bool:
    """FSM: пользователь вводит имя нового питомца."""
    user_id = str(ctx.user.id)
    name = ctx.text.strip()

    if not name or len(name) > 30:
        await bot.send_message(ctx.chat_id, "⚠️ Имя должно быть от 1 до 30 символов.")
        return True

    data = await get_fsm_data(user_id)
    species = data.get("species", "cat")

    # Удаляем старого питомца если есть
    supabase_admin.table("pets").delete().eq("user_id", user_id).execute()

    # Создаём нового
    supabase_admin.table("pets").insert({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "name": name,
        "species": species,
        "level": 1,
        "mood": "happy",
        "hunger": 100,
        "energy": 100,
    }).execute()

    await clear_fsm_state(user_id)
    await clear_fsm_data(user_id)

    species_icons = {"cat": "🐱", "dog": "🐶", "rabbit": "🐰", "hamster": "🐹", "fox": "🦊", "dragon": "🐉"}
    icon = species_icons.get(species, "🐾")
    await bot.send_message(
        ctx.chat_id,
        f"{icon} Познакомься с твоим новым питомцем — *{name}*!\n\n"
        f"Корми его, играй с ним и следи за его здоровьем 🥰",
        parse_mode="Markdown",
    )
    return True

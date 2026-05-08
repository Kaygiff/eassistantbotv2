"""
virtual_world/pets/service.py — Все операции с питомцами.
30 видов: 20 обычных + 10 фэнтези.
Уровни 1–10, XP за действия, настроение влияет на XP x1.5.
"""

from __future__ import annotations
import uuid
import logging

from infra.db.supabase import get_supabase_admin
from bot.brain.context import BrainContext
from api.auth.session import get_fsm_data, set_fsm_state, set_fsm_data, clear_fsm_state, clear_fsm_data
from core.i18n import t

logger = logging.getLogger(__name__)

HEAL_COST = 50

SPECIES_NORMAL: dict[str, str] = {
    "cat":      "🐱 Кот",
    "dog":      "🐶 Пёс",
    "rabbit":   "🐰 Кролик",
    "hamster":  "🐹 Хомяк",
    "fox":      "🦊 Лиса",
    "wolf":     "🐺 Волк",
    "bear":     "🐻 Медведь",
    "raccoon":  "🦝 Енот",
    "deer":     "🦌 Олень",
    "turtle":   "🐢 Черепаха",
    "parrot":   "🦜 Попугай",
    "owl":      "🦉 Сова",
    "penguin":  "🐧 Пингвин",
    "frog":     "🐸 Лягушка",
    "snake":    "🐍 Змея",
    "squirrel": "🐿 Белка",
    "hedgehog": "🦔 Ёж",
    "duck":     "🦆 Утка",
    "panda":    "🐼 Панда",
    "capybara": "🦫 Капибара",
}

SPECIES_FANTASY: dict[str, str] = {
    "dragon":   "🐉 Дракон",
    "phoenix":  "🔥 Феникс",
    "unicorn":  "🦄 Единорог",
    "griffin":  "🦅 Грифон",
    "mermaid":  "🧜 Русалка",
    "basilisk": "🐍✨ Василиск",
    "kitsune":  "🦊✨ Кицунэ",
    "slime":    "🫧 Слаймик",
    "ghost":    "👻 Призрак",
    "chimera":  "🦁 Химера",
}

ALL_SPECIES: dict[str, str] = {**SPECIES_NORMAL, **SPECIES_FANTASY}

XP_PER_FEED  = 5
XP_PER_PLAY  = 8
XP_PER_HEAL  = 10
XP_MOOD_MULT = 1.5

XP_FOR_LEVEL = {1:0,2:50,3:130,4:250,5:420,6:650,7:950,8:1350,9:1900,10:9999}

LEVEL_ICONS = {
    1:"⭐",2:"⭐⭐",3:"🌟",4:"🌟🌟",5:"💫",
    6:"💫💫",7:"✨",8:"✨✨",9:"🔥",10:"👑",
}


def _calc_level(xp: int) -> int:
    level = 1
    for lvl, required in XP_FOR_LEVEL.items():
        if xp >= required:
            level = lvl
    return min(level, 10)


def _xp_gain(base: int, mood: str) -> int:
    return int(base * (XP_MOOD_MULT if mood == "happy" else 1.0))


async def _get_pet(user_id: str) -> dict | None:
    res = get_supabase_admin().table("pets").select("*").eq("user_id", user_id).maybe_single().execute()
    return res.data


def _species_icon(species: str) -> str:
    label = ALL_SPECIES.get(species, "🐾 Питомец")
    return label.split()[0]


def _pet_summary(pet: dict) -> str:
    icon = _species_icon(pet["species"])
    level_icon = LEVEL_ICONS.get(pet["level"], "⭐")
    return f"{icon} {pet['name']} | ур.{pet['level']} {level_icon}"


def _pet_text(pet: dict) -> str:
    icon = _species_icon(pet["species"])
    level_icon = LEVEL_ICONS.get(pet["level"], "⭐")
    mood_icons = {"happy": "😊", "neutral": "😐", "sad": "😢", "sick": "🤒"}
    xp = pet.get("xp", 0)
    next_lvl = pet["level"] + 1
    xp_next = XP_FOR_LEVEL.get(next_lvl, 9999) if pet["level"] < 10 else None
    return (
        f"{icon} *{pet['name']}* {level_icon}\n\n"
        f"🐾 Вид: {ALL_SPECIES.get(pet['species'], pet['species'])}\n"
        f"💛 Настроение: {mood_icons.get(pet['mood'], '😐')}\n"
        f"🍖 Сытость: {pet['hunger']}%\n"
        f"⚡ Энергия: {pet['energy']}%\n"
        f"🏅 Уровень: {pet['level']}"
        + (f" | XP: {xp}/{xp_next}" if xp_next else " | MAX")
        + ("\n\n⚠️ Питомец болен!" if pet.get("is_sick") else "")
    )


async def _add_xp(pet: dict, xp_base: int) -> dict:
    gained = _xp_gain(xp_base, pet["mood"])
    new_xp = pet.get("xp", 0) + gained
    new_level = _calc_level(new_xp)
    leveled_up = new_level > pet["level"]
    get_supabase_admin().table("pets").update({"xp": new_xp, "level": new_level}).eq("id", pet["id"]).execute()
    return {"gained": gained, "leveled_up": leveled_up, "new_level": new_level}


# ---------------------------------------------------------------------------
# Главное меню
# ---------------------------------------------------------------------------

async def open_pet_menu(user_id: str, language: str, bot, chat_id: int) -> None:
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    pet = await _get_pet(user_id)

    if not pet or pet["is_dead"]:
        text = (
            "🐾 *Питомец*\n\n"
            + ("💀 Твой питомец умер...\n\nЗаведи нового!" if pet and pet["is_dead"]
               else "У тебя ещё нет питомца!")
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🥚 Создать питомца", callback_data="pet:new")],
        ])
        await bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=kb)
        return

    rows = [
        [
            InlineKeyboardButton(text="🍖 Покормить", callback_data="pet:feed"),
            InlineKeyboardButton(text="🎾 Поиграть",  callback_data="pet:play"),
        ],
    ]
    if pet.get("is_sick"):
        rows.append([InlineKeyboardButton(text=f"💊 Вылечить ({HEAL_COST} Ecoins)", callback_data="pet:heal")])
    rows.append([InlineKeyboardButton(text="✏️ Сменить имя", callback_data="pet:rename")])

    await bot.send_message(
        chat_id,
        _pet_text(pet),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


# ---------------------------------------------------------------------------
# Статус (текстовый ответ)
# ---------------------------------------------------------------------------

async def get_pet_status(user_id: str, language: str) -> str:
    pet = await _get_pet(user_id)
    if not pet:
        return "🐾 У тебя нет питомца.\n\nНапиши *создать питомца* чтобы завести!"
    if pet["is_dead"]:
        return f"💀 Твой питомец *{pet['name']}* умер...\n\nНапиши *создать питомца* чтобы завести нового."
    return _pet_text(pet)


# ---------------------------------------------------------------------------
# Действия
# ---------------------------------------------------------------------------

async def feed_pet(user_id: str, language: str) -> str:
    pet = await _get_pet(user_id)
    if not pet: return "🐾 У тебя нет питомца."
    if pet["is_dead"]: return "💀 Питомец умер."
    get_supabase_admin().table("pets").update({"hunger": min(100, pet["hunger"] + 25)}).eq("id", pet["id"]).execute()
    xp = await _add_xp(pet, XP_PER_FEED)
    msg = f"{_species_icon(pet['species'])} *{pet['name']}* сытно поел! 🍖\n+{xp['gained']} XP"
    if xp["leveled_up"]:
        msg += f"\n\n🎉 *Уровень {xp['new_level']}!* {LEVEL_ICONS.get(xp['new_level'], '')}"
    return msg


async def play_with_pet(user_id: str, language: str) -> str:
    pet = await _get_pet(user_id)
    if not pet: return "🐾 У тебя нет питомца."
    if pet["is_dead"]: return "💀 Питомец умер."
    get_supabase_admin().table("pets").update({"energy": min(100, pet["energy"] + 20)}).eq("id", pet["id"]).execute()
    xp = await _add_xp(pet, XP_PER_PLAY)
    msg = f"{_species_icon(pet['species'])} *{pet['name']}* весело поиграл! 🎾\n+{xp['gained']} XP"
    if xp["leveled_up"]:
        msg += f"\n\n🎉 *Уровень {xp['new_level']}!* {LEVEL_ICONS.get(xp['new_level'], '')}"
    return msg


async def heal_pet(user_id: str, language: str) -> str:
    pet = await _get_pet(user_id)
    if not pet: return "🐾 У тебя нет питомца."
    if pet["is_dead"]: return "💀 Питомец умер."
    if not pet["is_sick"]: return f"💚 *{pet['name']}* здоров!"
    from world.economy.wallet import debit
    success, balance = await debit(user_id, HEAL_COST, "pet_heal")
    if not success:
        return t(language, "economy.insufficient_funds", balance=balance)
    get_supabase_admin().table("pets").update({
        "is_sick": False, "mood": "happy", "hunger": 60, "energy": 60,
    }).eq("id", pet["id"]).execute()
    xp = await _add_xp(pet, XP_PER_HEAL)
    msg = f"{_species_icon(pet['species'])} *{pet['name']}* вылечен! 💊\n+{xp['gained']} XP"
    if xp["leveled_up"]:
        msg += f"\n\n🎉 *Уровень {xp['new_level']}!* {LEVEL_ICONS.get(xp['new_level'], '')}"
    return msg


# ---------------------------------------------------------------------------
# Создание — выбор вида
# ---------------------------------------------------------------------------

async def open_pet_creation(user_id: str, bot, chat_id: int) -> None:
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    rows = []
    items = list(SPECIES_NORMAL.items())
    for i in range(0, len(items), 2):
        rows.append([
            InlineKeyboardButton(text=label, callback_data=f"pet:create:{key}")
            for key, label in items[i:i+2]
        ])
    rows.append([InlineKeyboardButton(text="─── ✨ Фэнтези ───", callback_data="pet:noop")])
    items = list(SPECIES_FANTASY.items())
    for i in range(0, len(items), 2):
        rows.append([
            InlineKeyboardButton(text=label, callback_data=f"pet:create:{key}")
            for key, label in items[i:i+2]
        ])
    await bot.send_message(
        chat_id,
        "🥚 *Выбери вид питомца:*\n\nЭто навсегда — выбирай с умом! 😊",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


# ---------------------------------------------------------------------------
# FSM: ввод имени (создание)
# ---------------------------------------------------------------------------

async def handle_pet_naming(ctx: BrainContext, bot) -> bool:
    user_id = str(ctx.user.id)
    name = ctx.text.strip()
    if not name or len(name) > 30:
        await bot.send_message(ctx.chat_id, "⚠️ Имя должно быть от 1 до 30 символов.")
        return True
    data = await get_fsm_data(user_id)
    species = data.get("species", "cat")
    get_supabase_admin().table("pets").delete().eq("user_id", user_id).execute()
    get_supabase_admin().table("pets").insert({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "name": name,
        "species": species,
        "level": 1,
        "xp": 0,
        "mood": "happy",
        "hunger": 100,
        "energy": 100,
        "is_sick": False,
        "is_dead": False,
    }).execute()
    await clear_fsm_state(user_id)
    await clear_fsm_data(user_id)
    icon = _species_icon(species)
    await bot.send_message(
        ctx.chat_id,
        f"{icon} Познакомься — *{name}*!\n\nКорми, играй, следи за здоровьем 🥰\n_питомец — главное меню_",
        parse_mode="Markdown",
    )
    return True


# ---------------------------------------------------------------------------
# FSM: переименование
# ---------------------------------------------------------------------------

async def start_pet_rename(user_id: str, bot, chat_id: int) -> None:
    pet = await _get_pet(user_id)
    if not pet or pet["is_dead"]:
        await bot.send_message(chat_id, "🐾 У тебя нет живого питомца.")
        return
    await set_fsm_state(user_id, "pet:rename")
    icon = _species_icon(pet["species"])
    await bot.send_message(
        chat_id,
        f"{icon} Сейчас: *{pet['name']}*\n\nВведи новое имя:",
        parse_mode="Markdown",
    )


async def handle_pet_rename(ctx: BrainContext, bot) -> bool:
    user_id = str(ctx.user.id)
    name = ctx.text.strip()
    if not name or len(name) > 30:
        await bot.send_message(ctx.chat_id, "⚠️ Имя должно быть от 1 до 30 символов.")
        return True
    pet = await _get_pet(user_id)
    if not pet or pet["is_dead"]:
        await clear_fsm_state(user_id)
        return True
    get_supabase_admin().table("pets").update({"name": name}).eq("id", pet["id"]).execute()
    await clear_fsm_state(user_id)
    await bot.send_message(
        ctx.chat_id,
        f"{_species_icon(pet['species'])} Питомец теперь *{name}*! ✅",
        parse_mode="Markdown",
    )
    return True


# ---------------------------------------------------------------------------
# Для профиля
# ---------------------------------------------------------------------------

async def get_pet_profile_line(user_id: str) -> str | None:
    pet = await _get_pet(user_id)
    if not pet or pet["is_dead"]:
        return None
    return _pet_summary(pet)

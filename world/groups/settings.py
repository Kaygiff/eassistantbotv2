"""
groups/settings.py — Настройки и сообщения групп.
"""

from __future__ import annotations
from infra.db.supabase import get_supabase_admin
from bot.brain.context import BrainContext
from api.auth.session import set_fsm_state


# ---------------------------------------------------------------------------
# Главное меню настроек
# ---------------------------------------------------------------------------

async def get_group_settings_menu(group_id: str, language: str) -> tuple[str, object]:
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    res = get_supabase_admin().table("groups").select("*").eq("id", group_id).maybe_single().execute()
    group = res.data or {}

    warn_action_labels = {"ban": "🔨 Бан", "kick": "👟 Кик", "mute": "🔇 Мут"}
    warn_action = group.get("warn_action", "ban")

    text = (
        f"⚙️ *Настройки группы*\n\n"
        f"🌐 Язык: *{group.get('language', 'ru').upper()}*\n"
        f"⚠️ Порог варнов: *{group.get('warn_threshold', 3)}*\n"
        f"🔨 Действие при варнах: *{warn_action_labels.get(warn_action, warn_action)}*\n"
        f"👋 Приветствие: {'✅' if group.get('welcome_message') else '❌'}\n"
        f"👋 Прощание: {'✅' if group.get('farewell_message') else '❌'}\n"
        f"📋 Правила: {'✅' if group.get('rules_text') else '❌'}"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👋 Приветствие", callback_data="groupset:welcome")],
        [InlineKeyboardButton(text="🚪 Прощание", callback_data="groupset:farewell")],
        [InlineKeyboardButton(text="📋 Правила группы", callback_data="groupset:rules")],
        [InlineKeyboardButton(text="⚠️ Варны", callback_data="groupset:warns_menu")],
        [InlineKeyboardButton(text="🌐 Язык группы", callback_data="groupset:language")],
    ])
    return text, keyboard


# ---------------------------------------------------------------------------
# Подменю варнов
# ---------------------------------------------------------------------------

async def get_warns_menu(group_id: str) -> tuple[str, object]:
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    res = get_supabase_admin().table("groups").select(
        "warn_threshold, warn_action, warn_mute_hours"
    ).eq("id", group_id).maybe_single().execute()
    group = res.data or {}

    threshold = group.get("warn_threshold", 3)
    action = group.get("warn_action", "ban")
    mute_hours = group.get("warn_mute_hours", 24)

    action_labels = {"ban": "🔨 Бан", "kick": "👟 Кик", "mute": "🔇 Мут"}
    action_label = action_labels.get(action, action)

    mute_line = f"\n🔇 Длительность мута: *{mute_hours}ч*" if action == "mute" else ""

    text = (
        f"⚠️ *Настройки варнов*\n\n"
        f"Порог: *{threshold}* предупреждений\n"
        f"Действие: *{action_label}*"
        f"{mute_line}"
    )

    rows = [
        [InlineKeyboardButton(text=f"⚠️ Порог варнов (сейчас: {threshold})", callback_data="groupset:warn_threshold")],
        [
            InlineKeyboardButton(text="🔨 Бан", callback_data="groupset:warn_action:ban"),
            InlineKeyboardButton(text="👟 Кик", callback_data="groupset:warn_action:kick"),
            InlineKeyboardButton(text="🔇 Мут", callback_data="groupset:warn_action:mute"),
        ],
    ]
    if action == "mute":
        rows.append([InlineKeyboardButton(
            text=f"⏱ Часы мута (сейчас: {mute_hours}ч)", callback_data="groupset:warn_mute_hours"
        )])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="groupset:back")])

    return text, InlineKeyboardMarkup(inline_keyboard=rows)


# ---------------------------------------------------------------------------
# FSM-запросы ввода текста
# ---------------------------------------------------------------------------

async def prompt_welcome(ctx: BrainContext) -> str:
    await set_fsm_state(str(ctx.user.id), "group:awaiting_welcome")
    return "👋 Введи текст приветственного сообщения.\n\nДоступные переменные: `{name}` — имя пользователя."


async def prompt_farewell(ctx: BrainContext) -> str:
    await set_fsm_state(str(ctx.user.id), "group:awaiting_farewell")
    return "🚪 Введи текст прощального сообщения.\n\nДоступные переменные: `{name}` — имя пользователя."


async def prompt_rules(ctx: BrainContext) -> str:
    await set_fsm_state(str(ctx.user.id), "group:awaiting_rules")
    return "📋 Введи текст правил группы.\n\nПоддерживается Markdown. Правила будут отправляться при вступлении и по команде."


async def prompt_warn_threshold(ctx: BrainContext) -> str:
    await set_fsm_state(str(ctx.user.id), "group:awaiting_warn_threshold")
    return "⚠️ Введи количество варнов до наказания (число от 1 до 10):"


async def prompt_warn_mute_hours(ctx: BrainContext) -> str:
    await set_fsm_state(str(ctx.user.id), "group:awaiting_warn_mute_hours")
    return "⏱ Введи длительность мута в часах (число от 1 до 720):"


# ---------------------------------------------------------------------------
# Сохранение значений
# ---------------------------------------------------------------------------

async def save_welcome_message(group_id: str, text: str) -> None:
    get_supabase_admin().table("groups").update({"welcome_message": text}).eq("id", group_id).execute()


async def save_farewell_message(group_id: str, text: str) -> None:
    get_supabase_admin().table("groups").update({"farewell_message": text}).eq("id", group_id).execute()


async def save_rules_text(group_id: str, text: str) -> None:
    get_supabase_admin().table("groups").update({"rules_text": text}).eq("id", group_id).execute()


async def save_warn_threshold(group_id: str, value: int) -> None:
    get_supabase_admin().table("groups").update({"warn_threshold": value}).eq("id", group_id).execute()


async def save_warn_action(group_id: str, action: str) -> None:
    get_supabase_admin().table("groups").update({"warn_action": action}).eq("id", group_id).execute()


async def save_warn_mute_hours(group_id: str, hours: int) -> None:
    get_supabase_admin().table("groups").update({"warn_mute_hours": hours}).eq("id", group_id).execute()


# ---------------------------------------------------------------------------
# Получение данных для событий
# ---------------------------------------------------------------------------

async def get_group_by_chat_id(chat_id: int) -> dict:
    res = (
        get_supabase_admin()
        .table("groups")
        .select("id, welcome_message, farewell_message, rules_text, warn_action, warn_mute_hours, warn_threshold")
        .eq("chat_id", chat_id)
        .maybe_single()
        .execute()
    )
    return res.data or {}

"""
groups/fsm.py — FSM состояния для групповых настроек.
"""

from __future__ import annotations
from bot.brain.context import BrainContext
from api.auth.session import clear_fsm_state, get_fsm_data
from world.groups.settings import (
    save_welcome_message,
    save_farewell_message,
    save_rules_text,
    save_warn_threshold,
    save_warn_mute_hours,
    get_group_settings_menu,
    get_warns_menu,
)


async def _resolve_group_id(ctx: BrainContext, user_id: str) -> str | None:
    """
    Возвращает group_id: сначала из ctx, затем из FSM-data (для случая
    когда настройки открывались из группы, а бот отвечает в личку).
    """
    if ctx.group_id:
        return ctx.group_id
    fsm_data = await get_fsm_data(user_id) or {}
    return fsm_data.get("group_id")


async def handle_group_fsm(ctx: BrainContext, bot, state: str) -> bool:
    user_id = str(ctx.user.id)

    # --- Приветствие ---
    if state == "group:awaiting_welcome":
        group_id = await _resolve_group_id(ctx, user_id)
        await clear_fsm_state(user_id)
        if not group_id:
            return True
        await save_welcome_message(group_id, ctx.text)
        text, keyboard = await get_group_settings_menu(group_id, ctx.language)
        await bot.send_message(ctx.chat_id, "✅ Приветственное сообщение сохранено!\n\n" + text,
                               parse_mode="Markdown", reply_markup=keyboard)
        return True

    # --- Прощание ---
    if state == "group:awaiting_farewell":
        group_id = await _resolve_group_id(ctx, user_id)
        await clear_fsm_state(user_id)
        if not group_id:
            return True
        await save_farewell_message(group_id, ctx.text)
        text, keyboard = await get_group_settings_menu(group_id, ctx.language)
        await bot.send_message(ctx.chat_id, "✅ Прощальное сообщение сохранено!\n\n" + text,
                               parse_mode="Markdown", reply_markup=keyboard)
        return True

    # --- Правила ---
    if state == "group:awaiting_rules":
        group_id = await _resolve_group_id(ctx, user_id)
        await clear_fsm_state(user_id)
        if not group_id:
            return True
        await save_rules_text(group_id, ctx.text)
        text, keyboard = await get_group_settings_menu(group_id, ctx.language)
        await bot.send_message(ctx.chat_id, "✅ Правила группы сохранены!\n\n" + text,
                               parse_mode="Markdown", reply_markup=keyboard)
        return True

    # --- Порог варнов ---
    if state == "group:awaiting_warn_threshold":
        group_id = await _resolve_group_id(ctx, user_id)
        await clear_fsm_state(user_id)
        if not group_id:
            return True
        try:
            value = int(ctx.text.strip())
            if not 1 <= value <= 10:
                raise ValueError
        except ValueError:
            await bot.send_message(ctx.chat_id, "❌ Введи число от 1 до 10.")
            return True
        await save_warn_threshold(group_id, value)
        text, keyboard = await get_warns_menu(group_id)
        await bot.send_message(ctx.chat_id, f"✅ Порог варнов установлен: *{value}*\n\n" + text,
                               parse_mode="Markdown", reply_markup=keyboard)
        return True

    # --- Часы мута при варнах ---
    if state == "group:awaiting_warn_mute_hours":
        group_id = await _resolve_group_id(ctx, user_id)
        await clear_fsm_state(user_id)
        if not group_id:
            return True
        try:
            hours = int(ctx.text.strip())
            if not 1 <= hours <= 720:
                raise ValueError
        except ValueError:
            await bot.send_message(ctx.chat_id, "❌ Введи число от 1 до 720.")
            return True
        await save_warn_mute_hours(group_id, hours)
        text, keyboard = await get_warns_menu(group_id)
        await bot.send_message(ctx.chat_id, f"✅ Длительность мута установлена: *{hours}ч*\n\n" + text,
                               parse_mode="Markdown", reply_markup=keyboard)
        return True

    # --- Устаревшее состояние ---
    if state == "group:awaiting_warn_reason":
        await clear_fsm_state(user_id)
        return True

    return False

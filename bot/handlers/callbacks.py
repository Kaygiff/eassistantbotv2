"""
bot/handlers/callbacks.py — Обработка всех inline callback кнопок.
Централизованная точка для callback_data.
Формат callback_data: "namespace:action:param"
"""

from __future__ import annotations
import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery

logger = logging.getLogger(__name__)

callback_router = Router()


async def _get_ctx_and_user(callback: CallbackQuery):
    """Получает пользователя для callback."""
    from api.auth.identity import get_user_by_telegram_id
    from bot.brain.context import BrainContext

    user = await get_user_by_telegram_id(callback.from_user.id)
    lang = user.language if user else "ru"

    ctx = BrainContext(
        telegram_id=callback.from_user.id,
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        text="",
        is_group=callback.message.chat.type in ("group", "supergroup"),
    )
    ctx.user = user
    ctx.language = lang
    return ctx


# --- Язык ---
@callback_router.callback_query(F.data.startswith("lang:"))
async def cb_language(callback: CallbackQuery) -> None:
    lang = callback.data.split(":")[1]
    from api.auth.identity import get_user_by_telegram_id, update_user_field
    user = await get_user_by_telegram_id(callback.from_user.id)
    if user:
        await update_user_field(str(user.id), language=lang)
    await callback.answer(f"✅ Язык изменён")
    await callback.message.edit_text(f"🌐 Язык установлен: *{lang.upper()}*", parse_mode="Markdown")


# --- Онбординг ---
@callback_router.callback_query(F.data.startswith("onboarding:"))
async def cb_onboarding(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    action = parts[1]
    ctx = await _get_ctx_and_user(callback)

    from bot.onboarding.flow import handle_onboarding_callback
    await handle_onboarding_callback(ctx, callback, action, parts[2] if len(parts) > 2 else None)


# --- Профиль ---
@callback_router.callback_query(F.data.startswith("profile:"))
async def cb_profile(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    action = parts[1]
    ctx = await _get_ctx_and_user(callback)

    if action == "edit":
        # Если есть третья часть — это выбор конкретного поля
        if len(parts) > 2:
            field = parts[2]
            from api.auth.session import set_fsm_state
            prompts = {
                "nickname": "✏️ Введи новый никнейм (максимум 50 символов):",
                "bio": "📝 Напиши что-нибудь о себе (максимум 300 символов):",
                "birthday": "🎂 Введи дату рождения в формате ДД.ММ.ГГГГ\nНапример: 15.03.1995",
                "language": None,  # отдельная логика
                "assistant_name": "🤖 Введи новое имя ассистента (максимум 50 символов):",
            }
            if field == "language":
                from core.i18n.loader import get_language_keyboard
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                buttons = get_language_keyboard()
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text=b["text"], callback_data=b["callback_data"])]
                                     for b in buttons]
                )
                await callback.message.edit_text("🌐 Выбери язык:", reply_markup=keyboard)
            elif field in prompts and prompts[field]:
                await set_fsm_state(str(ctx.user.id), f"settings:{field}")
                await callback.message.edit_text(prompts[field])
            else:
                logger.warning("Unknown profile edit field: %s", field)
        else:
            # Показываем меню редактирования, редактируя текущее сообщение
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✏️ Никнейм", callback_data="profile:edit:nickname")],
                [InlineKeyboardButton(text="📝 О себе", callback_data="profile:edit:bio")],
                [InlineKeyboardButton(text="🎂 День рождения", callback_data="profile:edit:birthday")],
                [InlineKeyboardButton(text="🌐 Язык", callback_data="profile:edit:language")],
                [InlineKeyboardButton(text="🤖 Имя ассистента", callback_data="profile:edit:assistant_name")],
            ])
            await callback.message.edit_text(
                "✏️ *Редактирование профиля*\n\nЧто хочешь изменить?",
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
    await callback.answer()


# --- Питомец ---
@callback_router.callback_query(F.data.startswith("pet:"))
async def cb_pet(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    action = parts[1]
    ctx = await _get_ctx_and_user(callback)

    if action == "new" and len(parts) > 2:
        species = parts[2]
        from api.auth.session import set_fsm_state, set_fsm_data
        await set_fsm_state(str(ctx.user.id), "pet:naming")
        await set_fsm_data(str(ctx.user.id), {"species": species})
        from core.i18n.loader import t
        await callback.message.edit_text(t(ctx.language, "pets.name_pet"))
    elif action == "feed":
        from bot.brain.handlers.pet import handle_pet_feed
        await handle_pet_feed(ctx, callback.message.bot)
    elif action == "play":
        from bot.brain.handlers.pet import handle_pet_play
        await handle_pet_play(ctx, callback.message.bot)
    elif action == "heal":
        from bot.brain.handlers.pet import handle_pet_heal
        await handle_pet_heal(ctx, callback.message.bot)

    await callback.answer()


# --- Казино ---
@callback_router.callback_query(F.data.startswith("casino:"))
async def cb_casino(callback: CallbackQuery) -> None:
    game = callback.data.split(":")[1]
    ctx = await _get_ctx_and_user(callback)
    ctx.text = f"/{game}"

    from bot.brain.intent import Intent
    intent_map = {
        "slots": Intent.CASINO_SLOTS,
        "roulette": Intent.CASINO_ROULETTE,
        "blackjack": Intent.CASINO_BLACKJACK,
        "crash": Intent.CASINO_CRASH,
        "poker": Intent.CASINO_POKER,
    }
    ctx.set_intent(intent_map.get(game, Intent.CASINO_OPEN))

    from core.i18n.loader import t
    await callback.message.edit_text(t(ctx.language, "casino.enter_bet"))
    await callback.answer()


# --- Настройки ---
@callback_router.callback_query(F.data.startswith("settings:"))
async def cb_settings(callback: CallbackQuery) -> None:
    action = callback.data.split(":")[1]
    ctx = await _get_ctx_and_user(callback)

    if action == "language":
        from core.i18n.loader import get_language_keyboard
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = get_language_keyboard()
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=b["text"], callback_data=b["callback_data"])]
                             for b in buttons]
        )
        await callback.message.edit_text("🌐 Выбери язык:", reply_markup=keyboard)

    elif action == "assistant_name":
        from api.auth.session import set_fsm_state
        await set_fsm_state(str(ctx.user.id), "settings:assistant_name")
        await callback.message.edit_text("✏️ Введи новое имя ассистента:")

    elif action == "profile":
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👤 Никнейм", callback_data="settings:nickname")],
            [InlineKeyboardButton(text="📝 О себе (bio)", callback_data="settings:bio")],
            [InlineKeyboardButton(text="🎂 День рождения", callback_data="settings:birthday")],
            [InlineKeyboardButton(text="🎭 Характер бота", callback_data="settings:personality")],
        ])
        await callback.message.edit_text(
            "👤 *Редактирование профиля*\n\nЧто хочешь изменить?",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

    elif action == "nickname":
        from api.auth.session import set_fsm_state
        await set_fsm_state(str(ctx.user.id), "settings:nickname")
        await callback.message.edit_text("👤 Введи новый никнейм (максимум 32 символа):")

    elif action == "bio":
        from api.auth.session import set_fsm_state
        await set_fsm_state(str(ctx.user.id), "settings:bio")
        await callback.message.edit_text("📝 Напиши что-нибудь о себе (максимум 300 символов):")

    elif action == "birthday":
        from api.auth.session import set_fsm_state
        await set_fsm_state(str(ctx.user.id), "settings:birthday")
        await callback.message.edit_text("🎂 Введи дату рождения в формате ДД.ММ.ГГГГ\nНапример: 15.03.1995")

    elif action == "personality":
        parts = callback.data.split(":")
        if len(parts) > 2:
            param = parts[2]
            from api.auth.identity import update_user_field
            await update_user_field(str(ctx.user.id), assistant_personality=param)
            labels = {"kind": "😊 Добрый", "evil": "😈 Злой", "neutral": "😐 Нейтральный"}
            await callback.message.edit_text(f"✅ Характер бота изменён: {labels.get(param, param)}")
        else:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="😊 Добрый", callback_data="settings:personality:kind")],
                [InlineKeyboardButton(text="😈 Злой", callback_data="settings:personality:evil")],
                [InlineKeyboardButton(text="😐 Нейтральный", callback_data="settings:personality:neutral")],
            ])
            await callback.message.edit_text("🎭 Выбери характер бота:", reply_markup=keyboard)

    await callback.answer()


# --- Настройки группы ---
@callback_router.callback_query(F.data.startswith("groupset:"))
async def cb_groupset(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    action = parts[1]
    ctx = await _get_ctx_and_user(callback)

    from infra.safety.group_moderation import can_moderate, get_group_member_role
    from world.groups.settings import (
        get_group_settings_menu, get_warns_menu,
        prompt_welcome, prompt_farewell, prompt_rules,
        prompt_warn_threshold, prompt_warn_mute_hours,
        save_warn_action,
    )
    from api.auth.session import set_fsm_data

    # Определяем group_id по chat_id
    from infra.db.supabase import get_supabase_admin
    res = (
        get_supabase_admin()
        .table("groups")
        .select("id")
        .eq("chat_id", callback.message.chat.id)
        .maybe_single()
        .execute()
    )
    group_id = res.data["id"] if res.data else None

    if not group_id or not await can_moderate(group_id, str(ctx.user.id)):
        await callback.answer("❌ Нет прав.", show_alert=True)
        return

    # Сохраняем group_id в FSM-data чтобы потом знать в какую группу писать
    await set_fsm_data(str(ctx.user.id), {"group_id": group_id, "chat_id": callback.message.chat.id})

    if action == "back":
        text, keyboard = await get_group_settings_menu(group_id, ctx.language)
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)

    elif action == "welcome":
        text = await prompt_welcome(ctx)
        await callback.message.edit_text(text, parse_mode="Markdown")

    elif action == "farewell":
        text = await prompt_farewell(ctx)
        await callback.message.edit_text(text, parse_mode="Markdown")

    elif action == "rules":
        text = await prompt_rules(ctx)
        await callback.message.edit_text(text, parse_mode="Markdown")

    elif action == "warns_menu":
        text, keyboard = await get_warns_menu(group_id)
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)

    elif action == "warn_threshold":
        text = await prompt_warn_threshold(ctx)
        await callback.message.edit_text(text)

    elif action == "warn_mute_hours":
        text = await prompt_warn_mute_hours(ctx)
        await callback.message.edit_text(text)

    elif action == "warn_action" and len(parts) > 2:
        new_action = parts[2]
        if new_action in ("ban", "kick", "mute"):
            await save_warn_action(group_id, new_action)
            text, keyboard = await get_warns_menu(group_id)
            await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)

    elif action == "language":
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        langs = [
            ("🇷🇺 Русский", "ru"), ("🇺🇸 English", "en"), ("🇺🇿 O'zbek", "uz"),
            ("🇰🇿 Қазақ", "kz"), ("🇰🇬 Кыргыз", "kg"), ("🇹🇯 Тоҷик", "tj"),
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"groupset:set_lang:{code}")]
            for label, code in langs
        ] + [[InlineKeyboardButton(text="◀️ Назад", callback_data="groupset:back")]])
        await callback.message.edit_text("🌐 Выбери язык группы:", reply_markup=keyboard)

    elif action == "set_lang" and len(parts) > 2:
        lang = parts[2]
        get_supabase_admin().table("groups").update({"language": lang}).eq("id", group_id).execute()
        text, keyboard = await get_group_settings_menu(group_id, lang)
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)

    await callback.answer()


# --- Отношения ---
@callback_router.callback_query(F.data.startswith("relationship:"))
async def cb_relationship(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    action = parts[1]
    ctx = await _get_ctx_and_user(callback)

    from world.virtual_world.relationships.service import handle_relationship_callback
    text = await handle_relationship_callback(ctx, action, parts[2] if len(parts) > 2 else None)
    if text:
        await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()

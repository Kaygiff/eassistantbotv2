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

    if action == "casino":
        from bot.brain.handlers.casino import _casino_keyboard
        from world.economy.wallet import get_balance
        balance = await get_balance(str(ctx.user.id))
        from core.i18n.loader import t
        await callback.message.edit_text(
            (
                f"🎰 *Казино*\n\n"
                f"💰 Твой баланс: *{balance} Ecoins*\n\n"
                f"{t(ctx.language, 'casino.warning')}\n\n"
                f"Выбери игру:"
            ),
            parse_mode="Markdown",
            reply_markup=_casino_keyboard(),
        )
        await callback.answer()
        return

    if action == "edit":
        if len(parts) > 2:
            field = parts[2]
            from api.auth.session import set_fsm_state
            prompts = {
                "nickname": "✏️ Введи новый никнейм (максимум 50 символов):",
                "bio": "📝 Напиши что-нибудь о себе (максимум 300 символов):",
                "birthday": "🎂 Введи дату рождения в формате ДД.ММ.ГГГГ\nНапример: 15.03.1995",
                "language": None,
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
    action = parts[1] if len(parts) > 1 else ""
    ctx = await _get_ctx_and_user(callback)
    user_id = str(ctx.user.id)
    bot = callback.bot
    chat_id = callback.message.chat.id

    if action == "noop":
        await callback.answer()
        return

    if action == "menu":
        from world.virtual_world.pets.service import open_pet_menu
        await open_pet_menu(user_id, ctx.language, bot, chat_id)

    elif action == "new" and len(parts) == 2:
        from world.virtual_world.pets.service import open_pet_creation
        await open_pet_creation(user_id, bot, chat_id)

    elif action == "create" and len(parts) > 2:
        species = parts[2]
        from api.auth.session import set_fsm_state, set_fsm_data
        await set_fsm_state(user_id, "pet:naming")
        await set_fsm_data(user_id, {"species": species})
        from world.virtual_world.pets.service import ALL_SPECIES, _species_icon
        label = ALL_SPECIES.get(species, species)
        icon = _species_icon(species)
        await callback.message.edit_text(
            f"{icon} *{label}*!

Как назовёшь питомца?",
            parse_mode="Markdown",
        )

    elif action == "feed":
        from world.virtual_world.pets.service import feed_pet
        text = await feed_pet(user_id, ctx.language)
        await bot.send_message(chat_id, text, parse_mode="Markdown")

    elif action == "play":
        from world.virtual_world.pets.service import play_with_pet
        text = await play_with_pet(user_id, ctx.language)
        await bot.send_message(chat_id, text, parse_mode="Markdown")

    elif action == "heal":
        from world.virtual_world.pets.service import heal_pet
        text = await heal_pet(user_id, ctx.language)
        await bot.send_message(chat_id, text, parse_mode="Markdown")

    elif action == "rename":
        from world.virtual_world.pets.service import start_pet_rename
        await start_pet_rename(user_id, bot, chat_id)

    await callback.answer()



# ===========================================================================
# КАЗИНО
# ===========================================================================

# --- Монетка ---
@callback_router.callback_query(F.data.startswith("coin:"))
async def cb_coin(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    action = parts[1]
    ctx = await _get_ctx_and_user(callback)
    await callback.answer()

    user_id    = str(ctx.user.id)
    chat_id    = callback.message.chat.id
    message_id = callback.message.message_id
    bot        = callback.bot

    from world.casino.games.coin import (
        open_coin, show_coin_bet_screen, play_coin_inline,
    )

    if action == "back":
        # back:sides — вернуться к выбору стороны
        await open_coin(user_id, ctx.language, bot, chat_id, message_id)
        return

    if action == "side":
        # side:орёл / side:решка — выбрана сторона, показать экран ставки
        side = parts[2]
        await show_coin_bet_screen(user_id, side, 0, bot, chat_id, message_id)
        return

    if action == "amount":
        # amount:орёл:500 — накопление ставки
        side    = parts[2]
        current = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
        await show_coin_bet_screen(user_id, side, current, bot, chat_id, message_id)
        return

    if action == "flip":
        # flip:орёл:500 — бросить
        side = parts[2]
        try:
            bet = int(parts[3])
        except (IndexError, ValueError):
            return
        from bot.brain.handlers.casino import MIN_BET, MAX_BET
        if not (MIN_BET <= bet <= MAX_BET):
            return
        await play_coin_inline(user_id, bet, ctx.language, side, bot, chat_id, message_id)
        return


# --- Кости ---
@callback_router.callback_query(F.data.startswith("dice:"))
async def cb_dice(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    action = parts[1]
    ctx = await _get_ctx_and_user(callback)
    await callback.answer()

    user_id    = str(ctx.user.id)
    chat_id    = callback.message.chat.id
    message_id = callback.message.message_id
    bot        = callback.bot

    from world.casino.games.dice import (
        open_dice, show_dice_bet_screen, play_dice_inline,
    )

    if action == "back":
        # back:types — вернуться к выбору типа ставки
        await open_dice(user_id, ctx.language, bot, chat_id, message_id)
        return

    if action == "type":
        # type:больше / type:меньше / type:ровно
        choice = parts[2]
        await show_dice_bet_screen(user_id, choice, 0, bot, chat_id, message_id)
        return

    if action == "amount":
        # amount:больше:500
        choice  = parts[2]
        current = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
        await show_dice_bet_screen(user_id, choice, current, bot, chat_id, message_id)
        return

    if action == "roll":
        # roll:больше:500
        choice = parts[2]
        try:
            bet = int(parts[3])
        except (IndexError, ValueError):
            return
        from bot.brain.handlers.casino import MIN_BET, MAX_BET
        if not (MIN_BET <= bet <= MAX_BET):
            return
        await play_dice_inline(user_id, bet, ctx.language, choice, bot, chat_id, message_id)
        return


# --- Колесо ---
@callback_router.callback_query(F.data.startswith("wheel:"))
async def cb_wheel(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    action = parts[1]
    ctx = await _get_ctx_and_user(callback)
    await callback.answer()

    user_id    = str(ctx.user.id)
    chat_id    = callback.message.chat.id
    message_id = callback.message.message_id
    bot        = callback.bot

    from world.casino.games.wheel import (
        open_wheel, show_wheel_bet_screen, play_wheel_inline,
    )

    if action == "back":
        param = parts[2] if len(parts) > 2 else "bet"
        if param == "bet":
            await open_wheel(user_id, ctx.language, bot, chat_id, message_id)
        else:
            # back:500 — вернуться к ставке с текущей суммой
            try:
                current = int(param)
            except ValueError:
                current = 0
            await show_wheel_bet_screen(user_id, current, bot, chat_id, message_id)
        return

    if action == "amount":
        current = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
        await show_wheel_bet_screen(user_id, current, bot, chat_id, message_id)
        return

    if action == "paytable":
        from world.casino.games.wheel import _paytable_text, _keyboard_paytable
        try:
            await bot.edit_message_text(
                _paytable_text(),
                chat_id=chat_id, message_id=message_id,
                parse_mode="Markdown",
                reply_markup=_keyboard_paytable(0),
            )
        except Exception:
            pass
        return

    if action == "spin":
        try:
            bet = int(parts[2])
        except (IndexError, ValueError):
            return
        from bot.brain.handlers.casino import MIN_BET, MAX_BET
        if not (MIN_BET <= bet <= MAX_BET):
            return
        from world.economy.wallet import get_balance
        if await get_balance(user_id) < bet:
            await callback.answer("💸 Недостаточно средств!", show_alert=True)
            return
        await play_wheel_inline(user_id, bet, ctx.language, bot, chat_id, message_id)
        return


# --- Мины ---
@callback_router.callback_query(F.data.startswith("mines:"))
async def cb_mines(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    action = parts[1]
    param  = parts[2] if len(parts) > 2 else None
    ctx = await _get_ctx_and_user(callback)
    await callback.answer()

    user_id    = str(ctx.user.id)
    chat_id    = callback.message.chat.id
    message_id = callback.message.message_id
    bot        = callback.bot

    from world.casino.games.mines import handle_mines_callback
    await handle_mines_callback(user_id, action, param, bot, chat_id, message_id)


# --- Джокер ---
@callback_router.callback_query(F.data.startswith("joker:"))
async def cb_joker(callback: CallbackQuery) -> None:
    parts  = callback.data.split(":")
    action = parts[1]
    param  = parts[2] if len(parts) > 2 else None
    param2 = parts[3] if len(parts) > 3 else None
    ctx = await _get_ctx_and_user(callback)
    await callback.answer()

    user_id    = str(ctx.user.id)
    chat_id    = callback.message.chat.id
    message_id = callback.message.message_id
    bot        = callback.bot

    from world.casino.games.joker import handle_joker_callback
    await handle_joker_callback(user_id, action, param, param2, bot, chat_id, message_id)


# --- Слоты ---
@callback_router.callback_query(F.data.startswith("slots:"))
async def cb_slots(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    action = parts[1]
    ctx = await _get_ctx_and_user(callback)
    await callback.answer()

    if action == "spin":
        try:
            bet = int(parts[2])
        except (IndexError, ValueError):
            return
        from bot.brain.handlers.casino import MIN_BET, MAX_BET
        from world.economy.wallet import get_balance
        if bet < MIN_BET or bet > MAX_BET:
            return
        balance = await get_balance(str(ctx.user.id))
        if balance < bet:
            await callback.message.answer("💸 Недостаточно средств!", parse_mode="Markdown")
            return
        from world.casino.games.slots import play_slots
        await play_slots(
            user_id=str(ctx.user.id),
            bet=bet,
            language=ctx.language,
            bot=callback.bot,
            chat_id=callback.message.chat.id,
        )

    elif action == "freespin":
        try:
            bet       = int(parts[2])
            freespins = int(parts[3])
        except (IndexError, ValueError):
            return
        from world.casino.games.slots import play_slots
        await play_slots(
            user_id=str(ctx.user.id),
            bet=bet,
            language=ctx.language,
            bot=callback.bot,
            chat_id=callback.message.chat.id,
            is_freespin=True,
            freespins_left=freespins,
        )

    elif action == "paytable":
        from world.casino.games.slots import paytable_text
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        bet_part = parts[2] if len(parts) > 2 else "100"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"slots:back:{bet_part}")]
        ])
        try:
            await callback.message.edit_text(paytable_text(), parse_mode="Markdown", reply_markup=keyboard)
        except Exception:
            pass

    elif action == "back":
        try:
            bet = int(parts[2])
        except (IndexError, ValueError):
            bet = 100
        from world.economy.wallet import get_balance
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        balance = await get_balance(str(ctx.user.id))
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🔄 Крутить ({bet} Ecoins)", callback_data=f"slots:spin:{bet}")],
            [
                InlineKeyboardButton(text="📊 Выплаты", callback_data=f"slots:paytable:{bet}"),
                InlineKeyboardButton(text="🎰 Казино",  callback_data="profile:casino"),
            ],
        ])
        try:
            await callback.message.edit_text(
                f"🎰 *Слоты*\n\n💰 Баланс: *{balance} Ecoins*\n\n_Нажми «Крутить» чтобы начать!_",
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
        except Exception:
            pass


# --- casino: (общий вход в игры с кнопок меню) ---
@callback_router.callback_query(F.data.startswith("casino:"))
async def cb_casino(callback: CallbackQuery) -> None:
    parts  = callback.data.split(":")
    action = parts[1]
    ctx    = await _get_ctx_and_user(callback)

    user_id    = str(ctx.user.id)
    chat_id    = callback.message.chat.id
    message_id = callback.message.message_id
    bot        = callback.bot

    # Рулетка
    if action == "roulette":
        from world.casino.games.roulette import open_roulette
        await open_roulette(
            user_id=user_id, language=ctx.language,
            bot=bot, chat_id=chat_id, message_id=message_id,
        )
        await callback.answer()
        return

    # Монетка
    if action == "coin":
        from world.casino.games.coin import open_coin
        await open_coin(user_id, ctx.language, bot, chat_id, message_id)
        await callback.answer()
        return

    # Кости
    if action == "dice":
        from world.casino.games.dice import open_dice
        await open_dice(user_id, ctx.language, bot, chat_id, message_id)
        await callback.answer()
        return

    # Колесо
    if action == "wheel":
        from world.casino.games.wheel import open_wheel
        await open_wheel(user_id, ctx.language, bot, chat_id, message_id)
        await callback.answer()
        return

    # Мины
    if action == "mines":
        from world.casino.games.mines import open_mines
        await open_mines(user_id, ctx.language, bot, chat_id, message_id)
        await callback.answer()
        return

    # Джокер
    if action == "joker":
        from world.casino.games.joker import open_joker
        await open_joker(user_id, ctx.language, bot, chat_id, message_id)
        await callback.answer()
        return

    await callback.answer()


# --- Рулетка (inline) ---
@callback_router.callback_query(F.data.startswith("rlt:"))
async def cb_roulette(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    action = parts[1]
    ctx = await _get_ctx_and_user(callback)
    await callback.answer()

    user_id    = str(ctx.user.id)
    msg        = callback.message
    chat_id    = msg.chat.id
    message_id = msg.message_id

    from world.casino.games.roulette import (
        open_roulette, show_bet_amount_screen, play_roulette_inline,
        _keyboard_number_row, _text_choose_type, _keyboard_bet_type,
    )
    from world.economy.wallet import get_balance

    if action == "back" and parts[2] == "types":
        await open_roulette(
            user_id=user_id, language=ctx.language,
            bot=callback.bot, chat_id=chat_id, message_id=message_id,
        )
        return

    if action == "type":
        bet_type = parts[2]
        if bet_type == "number":
            kb = _keyboard_number_row(0)
            try:
                await callback.bot.edit_message_text(
                    "🎡 *Рулетка* — Выбери число (0–36)\n\n🟢 = 0  🔴 = красное  ⚫ = чёрное",
                    chat_id=chat_id, message_id=message_id,
                    parse_mode="Markdown", reply_markup=kb,
                )
            except Exception:
                pass
        else:
            await show_bet_amount_screen(
                user_id=user_id, bet_type=bet_type, current_amount=0,
                bot=callback.bot, chat_id=chat_id, message_id=message_id,
            )
        return

    if action == "numpage":
        row = int(parts[2])
        kb = _keyboard_number_row(row)
        try:
            await callback.bot.edit_message_reply_markup(
                chat_id=chat_id, message_id=message_id, reply_markup=kb,
            )
        except Exception:
            pass
        return

    if action == "noop":
        return

    if action == "num":
        number   = int(parts[2])
        bet_type = f"number:{number}"
        await show_bet_amount_screen(
            user_id=user_id, bet_type=bet_type, current_amount=0,
            bot=callback.bot, chat_id=chat_id, message_id=message_id,
        )
        return

    if action == "amount":
        bet_type = parts[2]
        amount   = int(parts[3])
        await show_bet_amount_screen(
            user_id=user_id, bet_type=bet_type, current_amount=amount,
            bot=callback.bot, chat_id=chat_id, message_id=message_id,
        )
        return

    if action == "custom":
        bet_type = parts[2]
        from api.auth.session import set_fsm_state, set_fsm_data
        await set_fsm_state(user_id, "casino:roulette_custom_bet")
        await set_fsm_data(user_id, {
            "bet_type": bet_type, "chat_id": chat_id, "message_id": message_id,
        })
        try:
            from world.casino.games.roulette import _bet_label, _get_multiplier
            label = _bet_label(bet_type)
            mult  = _get_multiplier(bet_type)
            await callback.bot.edit_message_text(
                f"🎡 *Рулетка* — {label} (×{mult})\n\n✏️ Введи сумму ставки числом:",
                chat_id=chat_id, message_id=message_id,
                parse_mode="Markdown",
            )
        except Exception:
            pass
        return

    if action == "spin":
        bet_type = parts[2]
        bet      = int(parts[3])
        from bot.brain.handlers.casino import MIN_BET, MAX_BET
        if bet < MIN_BET or bet > MAX_BET:
            return
        balance = await get_balance(user_id)
        if balance < bet:
            await callback.answer("💸 Недостаточно средств!", show_alert=True)
            return
        await play_roulette_inline(
            user_id=user_id, bet=bet, language=ctx.language,
            bet_type=bet_type, bot=callback.bot,
            chat_id=chat_id, message_id=message_id,
        )
        return


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
            [InlineKeyboardButton(text="👤 Никнейм",        callback_data="settings:nickname")],
            [InlineKeyboardButton(text="📝 О себе (bio)",   callback_data="settings:bio")],
            [InlineKeyboardButton(text="🎂 День рождения",  callback_data="settings:birthday")],
            [InlineKeyboardButton(text="🎭 Характер бота",  callback_data="settings:personality")],
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
                [InlineKeyboardButton(text="😊 Добрый",     callback_data="settings:personality:kind")],
                [InlineKeyboardButton(text="😈 Злой",       callback_data="settings:personality:evil")],
                [InlineKeyboardButton(text="😐 Нейтральный",callback_data="settings:personality:neutral")],
            ])
            await callback.message.edit_text("🎭 Выбери характер бота:", reply_markup=keyboard)

    await callback.answer()


# --- Ecoins ---
@callback_router.callback_query(F.data.startswith("ecoins:"))
async def cb_ecoins(callback: CallbackQuery) -> None:
    parts  = callback.data.split(":")
    action = parts[1]
    ctx    = await _get_ctx_and_user(callback)

    if action == "menu":
        from world.economy.wallet import get_balance
        balance = await get_balance(str(ctx.user.id))
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Бонус",              callback_data="ecoins:bonus")],
            [InlineKeyboardButton(text="🔗 Реферальная ссылка", callback_data="ecoins:referral")],
            [InlineKeyboardButton(text="🏆 Лидеры",             callback_data="ecoins:leaders")],
            [InlineKeyboardButton(text="◀️ Назад",              callback_data="ecoins:back")],
        ])
        await callback.message.edit_text(
            f"💰 *Ecoins*\n\nТвой баланс: *{balance} Ecoins*",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

    elif action == "bonus":
        from world.economy.daily import claim_daily_bonus
        result = await claim_daily_bonus(str(ctx.user.id), ctx.language)
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="ecoins:menu")],
        ])
        await callback.message.edit_text(result, parse_mode="Markdown", reply_markup=keyboard)

    elif action == "referral":
        from world.economy.referral import get_referral_info
        info = await get_referral_info(str(ctx.user.id), ctx.user.telegram_id, ctx.language)
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="ecoins:menu")],
        ])
        await callback.message.edit_text(info, parse_mode="Markdown", reply_markup=keyboard)

    elif action == "leaders":
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🌍 Глобальные",    callback_data="ecoins:top_global"),
                InlineKeyboardButton(text="👥 В этой группе", callback_data="ecoins:top_group"),
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="ecoins:menu")],
        ])
        await callback.message.edit_text(
            "🏆 *Таблица лидеров*\n\nВыбери тип:",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

    elif action == "top_global":
        from world.economy.leaderboard import get_leaderboard_text
        text = await get_leaderboard_text(language=ctx.language)
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="ecoins:leaders")],
        ])
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)

    elif action == "top_group":
        if callback.message.chat.type not in ("group", "supergroup"):
            await callback.answer("Доступно только в группе.", show_alert=True)
            return
        from world.economy.leaderboard import get_group_leaderboard_text
        text = await get_group_leaderboard_text(chat_id=callback.message.chat.id, language=ctx.language)
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="ecoins:leaders")],
        ])
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)

    elif action == "back":
        from world.economy.wallet import get_balance
        user    = ctx.user
        balance = await get_balance(str(user.id))
        lines   = [f"👤 *Профиль*\n", f"🏷 Имя ассистента: *{user.assistant_name}*"]
        if user.nickname:
            lines.append(f"✏️ Никнейм: *{user.nickname}*")
        if user.bio:
            lines.append(f"📝 О себе: {user.bio}")
        if user.birthday:
            lines.append(f"🎂 День рождения: {user.birthday.strftime('%d.%m.%Y')}")
        lines.append(f"🌐 Язык: {user.language.upper()}")
        lines.append(f"💰 Баланс: *{balance} Ecoins*")
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Редактировать", callback_data="profile:edit"),
                InlineKeyboardButton(text="💰 Ecoins",        callback_data="ecoins:menu"),
            ],
        ])
        await callback.message.edit_text("\n".join(lines), parse_mode="Markdown", reply_markup=keyboard)

    await callback.answer()


# --- Отношения ---
@callback_router.callback_query(F.data.startswith("relationship:"))
async def cb_relationship(callback: CallbackQuery) -> None:
    parts  = callback.data.split(":")
    action = parts[1]
    ctx    = await _get_ctx_and_user(callback)

    from world.virtual_world.relationships.service import handle_relationship_callback
    text = await handle_relationship_callback(ctx, action, parts[2] if len(parts) > 2 else None)
    if text:
        await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()

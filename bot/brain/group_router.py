"""
brain/group_router.py — Роутер для групповых чатов.
Отличается от приватного роутера:
- Проверяет регистрацию пользователя (не онбордит в группе)
- Логика двух режимов:
    * МИКРОСЕРВИСЫ (музыка, погода, перевод и т.д.) — только если сообщение
      начинается с имени ассистента пользователя (assistant_name).
      Пример: "Альфа, найди музыку Coldplay"
    * WORLD-функции (игры, отношения, модерация и т.д.) — без обращения по имени
- Логирует вступление новых участников
- Отправляет приветственное сообщение
"""

from __future__ import annotations
import logging
import re

from bot.brain.intent import Intent, GROUP_ALLOWED_INTENTS, GROUP_WORLD_INTENTS, MICROSERVICE_INTENTS
from bot.brain.classifier import classify
from bot.brain.context import BrainContext
from bot.brain.router import process as private_process, _handlers
from api.auth.identity import get_or_create_user
from infra.safety import check_user_access
from infra.safety.group_moderation import ensure_group_exists
from core.i18n import t

logger = logging.getLogger(__name__)


def _extract_assistant_address(text: str, assistant_name: str) -> tuple[bool, str]:
    """
    Проверяет, начинается ли сообщение с имени ассистента.
    Возвращает (addressed, clean_text) где:
      - addressed=True если обращение найдено
      - clean_text — текст без имени и знаков препинания после него

    Примеры:
      "Альфа, найди музыку" → (True, "найди музыку")
      "Альфа найди музыку"  → (True, "найди музыку")
      "альфа: переведи это" → (True, "переведи это")
      "просто текст"        → (False, "просто текст")
    """
    if not assistant_name or assistant_name == "Ассистент":
        return False, text

    # Паттерн: имя в начале строки + опциональный разделитель (, : - или пробел)
    pattern = re.compile(
        r"^" + re.escape(assistant_name) + r"\s*[,:\-]?\s*",
        re.IGNORECASE | re.UNICODE,
    )
    match = pattern.match(text.strip())
    if match:
        clean = text.strip()[match.end():].strip()
        return True, clean

    return False, text


async def process_group_message(ctx: BrainContext, bot) -> None:
    """
    Pipeline для группового чата.
    Вызывается из bot/handlers/group.py для каждого сообщения в группе.
    """

    # 1. Всегда загружаем group_id — ctx.group_id никогда не заполняется снаружи
    try:
        is_new_group = False
        from infra.db.supabase import get_supabase_admin
        res = get_supabase_admin().table("groups").select("id").eq("chat_id", ctx.chat_id).limit(1).execute()
        if res and res.data:
            ctx.group_id = res.data[0]["id"]
        else:
            group_id = await ensure_group_exists(
                chat_id=ctx.chat_id,
                title=ctx.extra.get("chat_title", "Unknown Group"),
                owner_id=None,
            )
            ctx.group_id = group_id
            is_new_group = True
        if is_new_group:
            from infra.safety.group_moderation import sync_group_owner
            await sync_group_owner(ctx.group_id, bot, ctx.chat_id)
    except Exception as e:
        logger.error(f"[GroupRouter] Failed to resolve group_id for chat {ctx.chat_id}: {e}")
        return

    # 2. Загружаем пользователя
    user, is_new = await get_or_create_user(
        telegram_id=ctx.telegram_id,
        username=ctx.tg_username,
        first_name=ctx.tg_first_name,
        last_name=ctx.tg_last_name,
        is_premium=ctx.tg_is_premium,
        locale=ctx.tg_locale,
    )
    ctx.user = user
    ctx.is_new_user = is_new
    ctx.language = user.language

    # 3. Новый участник группы — не онбордим, просим зарегистрироваться в боте
    if is_new:
        logger.info(f"[GroupRouter] New user {ctx.telegram_id} in group {ctx.chat_id}")
        # Реагируем только если сообщение явно адресовано боту (команда или /слэш)
        text_lower = ctx.text.strip().lower()
        is_command = text_lower.startswith("/")
        # Проверяем обращение по любому возможному имени — пока имени нет, смотрим на команды
        if is_command or any(
            text_lower.startswith(kw) for kw in [
                "слоты", "рулетка", "кости", "монетка", "мины", "джокер", "колесо",
                "казино", "баланс", "питомец", "профил",
            ]
        ):
            bot_info = await bot.get_me()
            bot_link = f"https://t.me/{bot_info.username}"
            await bot.send_message(
                ctx.chat_id,
                f"👋 Привет! Чтобы пользоваться ботом, сначала пройди регистрацию в личке:\n{bot_link}",
                reply_to_message_id=ctx.message_id,
            )
        return

    # 4. Safety check
    allowed, reason = await check_user_access(user)
    if not allowed:
        if reason == "banned":
            await bot.send_message(ctx.chat_id, t(ctx.language, "common.banned"))
        return

    # 5. FSM middleware — перехватываем если пользователь ожидает ввода текста
    from bot.onboarding.fsm_middleware import handle_fsm
    if await handle_fsm(ctx, bot):
        return

    # 5а. Голосовые сообщения — транскрибируем всегда, дальше по той же логике
    if ctx.is_voice and ctx.voice_file_id:
        from services.voice.stt import transcribe_voice
        transcribed = await transcribe_voice(ctx.voice_file_id, ctx.language, bot)
        if not transcribed:
            return  # не удалось распознать — молча выходим
        # Whisper добавляет кавычки и пунктуацию — чистим чтобы "Бишкек." не ломало запросы
        transcribed = re.sub(r'[«»""„"\']+', '', transcribed)  # убираем кавычки
        transcribed = transcribed.rstrip('.,!?;: ')               # убираем пунктуацию в конце
        transcribed = transcribed.strip()
        ctx.text = transcribed
        await bot.send_message(
            ctx.chat_id,
            f"🎤 _«{transcribed}»_",
            parse_mode="Markdown",
            reply_to_message_id=ctx.message_id,
        )
        # После транскрипции падаём в общую логику ниже (голос = текст)

    # 6. Определяем режим: обращение по имени или нет
    addressed, clean_text = _extract_assistant_address(ctx.text, user.assistant_name)

    if addressed:
        # Режим МИКРОСЕРВИСОВ + AI: пользователь явно обратился к боту
        ctx.extra["addressed_by_name"] = True
        ctx.text = clean_text  # классифицируем без имени бота

        # Если после имени ничего нет — бот откликается
        if not clean_text:
            import random
            responses = [
                "👋 Я здесь!",
                "⚡️ Работаю!",
                "✅ На месте, слушаю!",
                "😊 Да, это я!",
                "🎯 Здесь, чем помочь?",
            ]
            await bot.send_message(
                ctx.chat_id,
                random.choice(responses),
                reply_to_message_id=ctx.message_id,
            )
            return

        intent = await classify(ctx.text, ctx.language)
        ctx.set_intent(intent)

        # Не понял запрос — просим уточнить
        if ctx.intent == Intent.CLARIFICATION:
            from bot.brain.classifier import build_clarification_message
            clarification = await build_clarification_message(ctx.text, ctx.language)
            await bot.send_message(
                ctx.chat_id,
                clarification,
                reply_to_message_id=ctx.message_id,
            )
            return

        # Интент есть, но недоступен в группах (например, PROFILE_EDIT, SETTINGS)
        if ctx.intent not in GROUP_ALLOWED_INTENTS:
            await bot.send_message(
                ctx.chat_id,
                t(ctx.language, "common.only_private"),
                reply_to_message_id=ctx.message_id,
            )
            return

    else:
        # Режим WORLD: работают только world-интенты без обращения по имени.
        # Используем СТРОГИЙ классификатор — только паттерны с ^ или /команда.
        # Brain AI здесь не вызывается: он слишком широко интерпретирует
        # обычный разговор и порождает ложные срабатывания.
        from bot.brain.classifier import classify_by_patterns_strict
        intent = classify_by_patterns_strict(ctx.text)
        if intent is None or intent not in GROUP_WORLD_INTENTS:
            logger.debug(
                f"[GroupRouter] No strict world match for group {ctx.chat_id} — ignoring"
            )
            return
        ctx.set_intent(intent)

    logger.info(f"[GroupRouter] {ctx} addressed={addressed}")

    # 7. Маршрутизация — используем тот же реестр хэндлеров
    handler = _handlers.get(ctx.intent)
    if handler is None:
        handler = _handlers.get(Intent.AI_CHAT)

    if handler:
        try:
            await handler(ctx, bot)
        except Exception as e:
            logger.exception(f"[GroupRouter] Handler error: {e}")
            from infra.monitoring.metrics import capture_exception
            capture_exception(e, context={"intent": ctx.intent.value, "group": ctx.chat_id})
            await bot.send_message(ctx.chat_id, t(ctx.language, "common.error"))


async def handle_new_chat_member(ctx: BrainContext, bot, new_member_telegram_id: int) -> None:
    """
    Обрабатывает вступление нового участника в группу.
    При первом появлении синхронизирует owner через Telegram API.
    Отправляет приветственное сообщение если оно настроено.
    """
    if not ctx.group_id:
        return

    # Синхронизируем владельца группы через Telegram API
    from infra.safety.group_moderation import sync_group_owner
    await sync_group_owner(ctx.group_id, bot, ctx.chat_id)

    from infra.db.supabase import get_supabase_admin
    res = (
        get_supabase_admin()
        .table("groups")
        .select("welcome_message, language")
        .eq("id", ctx.group_id)
        .maybe_single()
        .execute()
    )
    if not res.data:
        return

    welcome_msg = res.data.get("welcome_message")
    lang = res.data.get("language", "ru")

    if welcome_msg:
        # Подставляем имя пользователя
        from api.auth.identity import get_user_by_telegram_id
        new_user = await get_user_by_telegram_id(new_member_telegram_id)
        name = new_user.first_name or f"@{new_user.username}" if new_user else "Новый участник"
        msg = welcome_msg.replace("{name}", name).replace("{username}", f"@{new_user.username}" if new_user and new_user.username else name)
        await bot.send_message(ctx.chat_id, msg, parse_mode="Markdown")


async def handle_member_left(ctx: BrainContext, bot) -> None:
    """Обрабатывает выход участника из группы."""
    logger.info(f"[GroupRouter] Member left group {ctx.chat_id}")

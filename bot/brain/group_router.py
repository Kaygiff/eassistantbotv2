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

    # 1. Убеждаемся что группа зарегистрирована в БД
    if ctx.group_id is None:
        group_id = await ensure_group_exists(
            chat_id=ctx.chat_id,
            title=ctx.extra.get("chat_title", "Unknown Group"),
            owner_id=None,
        )
        ctx.group_id = group_id

    # 2. Загружаем пользователя
    user, is_new = await get_or_create_user(telegram_id=ctx.telegram_id)
    ctx.user = user
    ctx.is_new_user = is_new
    ctx.language = user.language

    # 3. Новый участник группы — не онбордим, просто логируем
    if is_new:
        logger.info(f"[GroupRouter] New user {ctx.telegram_id} in group {ctx.chat_id}")
        # Онбординг — только в личке
        return

    # 4. Safety check
    allowed, reason = await check_user_access(user)
    if not allowed:
        if reason == "banned":
            await bot.send_message(ctx.chat_id, t(ctx.language, "common.banned"))
        return

    # 5. Голосовое/видео → STT
    # Транскрибируем всегда — чтобы люди могли прочитать вместо прослушивания.
    # Если в тексте есть имя бота или world-команда — дополнительно обрабатываем.
    if ctx.is_voice and ctx.voice_file_id:
        from services.voice.stt import transcribe_voice
        transcribed = await transcribe_voice(ctx.voice_file_id, ctx.language, bot)
        if not transcribed:
            return  # не удалось распознать — молча выходим
        ctx.text = transcribed
        await bot.send_message(
            ctx.chat_id,
            f"🎤 _«{transcribed}»_",
            parse_mode="Markdown",
            reply_to_message_id=ctx.message_id,
        )
        # Проверяем: есть ли обращение по имени или world-команда
        addressed, clean_text = _extract_assistant_address(ctx.text, user.assistant_name)
        if addressed:
            ctx.text = clean_text
            intent = await classify(ctx.text, ctx.language)
            ctx.set_intent(intent)
        else:
            # Нет имени — проверяем world-команды (/ban, /warn и т.д.)
            intent = await classify(ctx.text, ctx.language)
            ctx.set_intent(intent)
            if ctx.intent not in GROUP_WORLD_INTENTS:
                return  # просто транскрипция, дальше не идём
        if ctx.intent not in GROUP_ALLOWED_INTENTS:
            return
        handler = _handlers.get(ctx.intent) or _handlers.get(Intent.AI_CHAT)
        if handler:
            try:
                await handler(ctx, bot)
            except Exception as e:
                logger.exception(f"[GroupRouter] Voice handler error: {e}")
                await bot.send_message(ctx.chat_id, t(ctx.language, "common.error"))
        return  # голосовое полностью обработано

    # 6. Определяем режим: обращение по имени или нет
    addressed, clean_text = _extract_assistant_address(ctx.text, user.assistant_name)

    if addressed:
        # Режим МИКРОСЕРВИСОВ: классифицируем очищенный текст (без имени)
        ctx.extra["addressed_by_name"] = True
        original_text = ctx.text
        ctx.text = clean_text  # классифицируем без имени бота

        if ctx.intent == Intent.UNKNOWN:
            intent = await classify(ctx.text, ctx.language)
            ctx.set_intent(intent)

        # Если классификатор вернул world-интент при обращении по имени —
        # всё равно пропускаем (пользователь явно обратился к боту)
        if ctx.intent not in GROUP_ALLOWED_INTENTS:
            ctx.text = original_text
            await bot.send_message(ctx.chat_id, t(ctx.language, "common.only_private"))
            return

    else:
        # Режим WORLD: классифицируем полный текст, но микросервисы НЕ вызываем
        if ctx.intent == Intent.UNKNOWN:
            intent = await classify(ctx.text, ctx.language)
            ctx.set_intent(intent)

        # Микросервисы без обращения по имени — игнорируем молча
        if ctx.intent in MICROSERVICE_INTENTS:
            logger.debug(
                f"[GroupRouter] Microservice intent={ctx.intent.value} ignored "
                f"(no assistant name address) in group {ctx.chat_id}"
            )
            return

        # Остальные world-интенты проверяем по общему списку
        if ctx.intent not in GROUP_WORLD_INTENTS:
            await bot.send_message(ctx.chat_id, t(ctx.language, "common.only_private"))
            return

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
    Отправляет приветственное сообщение если оно настроено.
    """
    if not ctx.group_id:
        return

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

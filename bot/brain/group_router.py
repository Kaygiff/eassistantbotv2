"""
brain/group_router.py — Роутер для групповых чатов.
Отличается от приватного роутера:
- Проверяет регистрацию пользователя (не онбордит в группе)
- Ограничивает доступные интенты
- Логирует вступление новых участников
- Отправляет приветственное сообщение
"""

from __future__ import annotations
import logging

from bot.brain.intent import Intent, GROUP_ALLOWED_INTENTS
from bot.brain.classifier import classify
from bot.brain.context import BrainContext
from bot.brain.router import process as private_process, _handlers
from api.auth.identity import get_or_create_user
from infra.safety import check_user_access
from infra.safety.group_moderation import ensure_group_exists
from core.i18n import t

logger = logging.getLogger(__name__)


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

    # 5. Голосовое → STT
    if ctx.is_voice and ctx.voice_file_id:
        from services.voice.stt import transcribe_voice
        transcribed = await transcribe_voice(ctx.voice_file_id, ctx.language, bot)
        if transcribed:
            ctx.text = transcribed
        else:
            return

    # 6. Классификация интента
    if ctx.intent == Intent.UNKNOWN:
        intent = await classify(ctx.text, ctx.language)
        ctx.set_intent(intent)

    # 7. Проверка: разрешён ли интент в группе
    if ctx.intent not in GROUP_ALLOWED_INTENTS:
        await bot.send_message(ctx.chat_id, t(ctx.language, "common.only_private"))
        return

    logger.info(f"[GroupRouter] {ctx}")

    # 8. Маршрутизация — используем тот же реестр хэндлеров
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
        supabase_admin
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

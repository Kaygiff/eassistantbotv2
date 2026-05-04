"""
brain/router.py — Центральный NLP-роутер.
Точка входа для ВСЕХ входящих сообщений (личные + группы).

Pipeline:
  Telegram message
    → Safety check (бан + rate limit)
    → Auth (get_or_create_user)
    → Onboarding check
    → Intent classification
    → Route to handler
    → Response
"""

from __future__ import annotations
import logging
from typing import Callable, Awaitable, Any

from bot.brain.intent import Intent, PRIVATE_ONLY_INTENTS, GROUP_ALLOWED_INTENTS
from bot.brain.classifier import classify
from bot.brain.context import BrainContext
from api.auth.identity import get_or_create_user
from infra.safety import check_user_access
from core.i18n import t

logger = logging.getLogger(__name__)

# Тип хэндлера
Handler = Callable[[BrainContext, Any], Awaitable[None]]

# Реестр хэндлеров: intent → callable
_handlers: dict[Intent, Handler] = {}


def register(intent: Intent):
    """Декоратор для регистрации хэндлеров в роутере."""
    def decorator(fn: Handler) -> Handler:
        _handlers[intent] = fn
        return fn
    return decorator


async def process(ctx: BrainContext, bot: Any) -> None:
    """
    Главная функция обработки запроса.
    Вызывается из bot/handlers/ для каждого входящего сообщения.
    """

    # 1. Загружаем пользователя
    user, is_new = await get_or_create_user(
        telegram_id=ctx.telegram_id,
        username=None,
        first_name=None,
    )
    ctx.user = user
    ctx.is_new_user = is_new
    ctx.language = user.language

    # 2. Safety check
    allowed, reason = await check_user_access(user)
    if not allowed:
        if reason == "banned":
            await bot.send_message(ctx.chat_id, t(ctx.language, "common.banned"))
        elif reason == "rate_limit":
            await bot.send_message(ctx.chat_id, t(ctx.language, "common.rate_limit"))
        return

    # 3. FSM middleware — перехватывает если пользователь в диалоге
    from bot.onboarding.fsm_middleware import handle_fsm
    if await handle_fsm(ctx, bot):
        return

    # 4. Онбординг — новый пользователь или ещё не прошёл онбординг
    if is_new or user.assistant_name == "Ассистент":
        from bot.onboarding.flow import start_onboarding
        await start_onboarding(ctx, bot)
        return

    # 4. Проверка: личный vs. групповой чат
    if ctx.is_group and ctx.intent in PRIVATE_ONLY_INTENTS:
        await bot.send_message(ctx.chat_id, t(ctx.language, "common.only_private"))
        return

    # 5. Голосовое → STT → текст
    if ctx.is_voice and ctx.voice_file_id:
        from services.voice.stt import transcribe_voice
        transcribed = await transcribe_voice(ctx.voice_file_id, ctx.language, bot)
        if transcribed:
            ctx.text = transcribed
        else:
            await bot.send_message(ctx.chat_id, "🎤 Не удалось распознать голосовое сообщение. Попробуй ещё раз или напиши текстом.")
            return

    # 6. Классификация intent
    if ctx.intent == Intent.UNKNOWN:
        intent = await classify(ctx.text, ctx.language)
        ctx.set_intent(intent, confidence="keyword" if intent != Intent.CLARIFICATION else "clarification")

    logger.info(f"[Brain] {ctx}")

    # 7. Уточнение — Brain AI не смог определить сервис
    if ctx.intent == Intent.CLARIFICATION:
        from bot.brain.classifier import build_clarification_message
        clarification = await build_clarification_message(ctx.text, ctx.language)
        await bot.send_message(ctx.chat_id, clarification)
        return

    # 8. Маршрутизация к хэндлеру
    handler = _handlers.get(ctx.intent)

    if handler is None:
        # Хэндлер не найден — не падаем в AI_CHAT, сообщаем об ошибке
        logger.warning(f"[Brain] No handler for intent={ctx.intent.value}")
        await bot.send_message(ctx.chat_id, t(ctx.language, "common.error"))
        return

    if handler:
        try:
            await handler(ctx, bot)
        except Exception as e:
            logger.exception(f"Handler error for intent={ctx.intent}: {e}")
            from infra.monitoring.metrics import capture_exception
            capture_exception(e, context={"intent": ctx.intent.value, "user_id": ctx.user_id})
            await bot.send_message(ctx.chat_id, t(ctx.language, "common.error"))


def get_registered_intents() -> list[str]:
    """Возвращает список зарегистрированных интентов (для Brain Editor в EAdmin)."""
    return [i.value for i in _handlers.keys()]

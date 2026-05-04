"""
brain/classifier.py — Классификатор интентов.

Pipeline:
  1. Ключевые слова → мгновенно, без AI
  2. Brain AI (Hub, лёгкая модель) → пытается определить сервис
     — если нашёл → возвращает Intent
     — если не нашёл → возвращает NEEDS_CLARIFICATION
  3. Уточнение → бот помогает пользователю сформулировать запрос
  4. AI_CHAT → только если пользователь явно хочет поговорить

Brain AI и AI Chat — разные сущности:
  - Brain AI: классификатор, знает только список интентов, не ведёт диалог
  - AI Chat: полноценный разговорный агент с историей (services/ai_chat/chat.py)
"""

from __future__ import annotations
import logging
from typing import Optional

from bot.brain.intent import Intent

logger = logging.getLogger(__name__)

# Sentinel — означает что Brain AI не смог определить сервис
NEEDS_CLARIFICATION = "__needs_clarification__"

# ---------------------------------------------------------------------------
# Карта ключевых слов → интент
# ---------------------------------------------------------------------------
KEYWORD_MAP: list[tuple[list[str], Intent]] = [
    # Системные
    (["/start", "начать", "старт"], Intent.START),
    (["/help", "помощь", "помоги мне", "что умеешь", "команды"], Intent.HELP),
    (["/settings", "настройки", "настройка"], Intent.SETTINGS),

    # Профиль
    (["/profile", "мой профиль", "профиль", "моя анкета"], Intent.PROFILE_VIEW),
    (["изменить профиль", "редактировать профиль", "поменять имя", "сменить имя ассистента"], Intent.PROFILE_EDIT),

    # Экономика
    (["/balance", "баланс", "мои монеты", "сколько монет", "ecoins", "экоины"], Intent.BALANCE),
    (["/daily", "ежедневный бонус", "бонус дня", "получить бонус", "дейли"], Intent.DAILY_BONUS),
    (["перевести монеты", "отправить монеты", "перевод экоинов", "/transfer"], Intent.TRANSFER),
    (["/referral", "реферальная", "пригласить друга", "моя ссылка", "реф"], Intent.REFERRAL),

    # Питомец
    (["/pet", "мой питомец", "питомец", "тамагочи"], Intent.PET_STATUS),
    (["покормить питомца", "покорми", "дай поесть питомцу"], Intent.PET_FEED),
    (["поиграть с питомцем", "поиграй с питомцем", "игра с питомцем"], Intent.PET_PLAY),
    (["вылечить питомца", "лечи питомца", "питомец болен"], Intent.PET_HEAL),
    (["завести питомца", "новый питомец", "хочу питомца"], Intent.PET_NEW),

    # Отношения
    (["предложить встречаться", "давай встречаться", "будь моей", "будь моим"], Intent.RELATIONSHIP_PROPOSE),
    (["мои отношения", "статус отношений", "с кем я встречаюсь"], Intent.RELATIONSHIP_STATUS),
    (["расстаться", "разорвать отношения", "хватит встречаться"], Intent.RELATIONSHIP_BREAKUP),
    (["предложение руки", "выйти замуж", "жениться", "замуж за меня", "женись на мне"], Intent.MARRIAGE_PROPOSE),
    (["развод", "развестись", "хочу развода"], Intent.MARRIAGE_DIVORCE),
    (["добавить в семью", "стать братом", "стать сестрой", "стать отцом", "усыновить"], Intent.FAMILY_ADD),
    (["моя семья", "семейное дерево", "список семьи"], Intent.FAMILY_VIEW),

    # Действия
    (["обнять", "поцеловать", "погладить", "ударить", "подарить", "укусить",
      "погладь", "обними", "поцелуй", "ударь"], Intent.ACTION_DO),

    # Чёрный список
    (["заблокировать пользователя", "добавить в чс", "чёрный список добавить"], Intent.BLACKLIST_ADD),
    (["разблокировать", "убрать из чс", "чёрный список убрать"], Intent.BLACKLIST_REMOVE),

    # События
    (["создать событие", "новое событие", "/event create", "организовать встречу"], Intent.EVENT_CREATE),
    (["список событий", "ближайшие события", "/events"], Intent.EVENT_LIST),
    (["участвовать в событии", "присоединиться к событию"], Intent.EVENT_JOIN),

    # Казино
    (["/casino", "казино", "открыть казино"], Intent.CASINO_OPEN),
    (["слоты", "крутить слоты", "однорукий бандит", "/slots"], Intent.CASINO_SLOTS),
    (["рулетка", "крутить рулетку", "/roulette"], Intent.CASINO_ROULETTE),
    (["блэкджек", "blackjack", "двадцать одно", "/blackjack"], Intent.CASINO_BLACKJACK),
    (["краш", "crash", "/crash"], Intent.CASINO_CRASH),
    (["покер", "poker", "/poker"], Intent.CASINO_POKER),

    # Мини-игры
    (["викторина", "quiz", "/quiz", "вопрос"], Intent.GAME_QUIZ),
    (["кубик", "бросить кубик", "/dice", "dice"], Intent.GAME_DICE),
    (["правда или действие", "/truth", "/dare"], Intent.GAME_TRUTH_DARE),
    (["что бы ты выбрал", "что лучше", "/wouldyou"], Intent.GAME_WOULD_YOU),
    (["загадка", "загадай загадку", "/riddle"], Intent.GAME_RIDDLE),

    # Медиасервисы
    (["найди музыку", "скачай музыку", "включи", "поставь песню", "музыка",
      "трек", "скачать песню"], Intent.MUSIC_SEARCH),
    (["погода", "прогноз погоды", "какая погода", "температура", "/weather"], Intent.WEATHER),
    (["переведи", "перевод", "translate", "как сказать по"], Intent.TRANSLATE),
    (["генерировать изображение", "нарисуй", "создай картинку", "сгенерируй"], Intent.IMAGE_GEN),
    (["что такое", "расскажи о", "кто такой", "кто такая", "энциклопедия", "wikipedia"], Intent.ENCYCLOPEDIA),
    (["найди книгу", "рекомендуй книгу", "книги", "/book"], Intent.BOOK_SEARCH),
    (["найди аниме", "аниме", "anime", "/anime"], Intent.ANIME_SEARCH),

    # Задачи
    (["создать задачу", "добавить задачу", "новая задача", "/todo"], Intent.TASK_CREATE),
    (["мои задачи", "список задач", "/tasks"], Intent.TASK_LIST),
    (["задача выполнена", "отметить задачу", "сделано"], Intent.TASK_DONE),
    (["напомни", "установи напоминание", "напоминание", "/remind"], Intent.REMINDER_CREATE),

    # AI чат — только явный запрос на разговор
    (["/ai", "/chat", "поговори со мной", "давай поговорим", "пообщайся"], Intent.AI_CHAT),

    # Модерация групп
    (["/warn", "выдать варн", "предупреждение"], Intent.GROUP_WARN),
    (["/ban", "забанить", "бан пользователя"], Intent.GROUP_BAN),
    (["/mute", "заглушить", "мут"], Intent.GROUP_MUTE),
    (["/kick", "кикнуть", "выгнать"], Intent.GROUP_KICK),
    (["/groupsettings", "настройки группы"], Intent.GROUP_SETTINGS),
    (["/stats", "статистика группы"], Intent.GROUP_STATS),
    (["/setwelcome", "приветствие группы", "настроить приветствие"], Intent.GROUP_WELCOME),
]

# ---------------------------------------------------------------------------
# Подсказки сервисов — для уточняющего сообщения
# ---------------------------------------------------------------------------
SERVICE_HINTS = """🌤 Погода — «погода Москва»
🎵 Музыка — «найди музыку [название]»
🌐 Перевод — «переведи [текст] на английский»
🖼 Картинка — «нарисуй [описание]»
📚 Энциклопедия — «что такое [слово]»
📖 Книги — «найди книгу [название]»
🎌 Аниме — «найди аниме [название]»
📝 Задача — «создать задачу [название]»
⏰ Напоминание — «напомни [о чём] [дата время]»
🎰 Казино — «казино» или /casino
💰 Баланс — «баланс» или /balance
🐾 Питомец — «питомец» или /pet
💬 Просто поговорить — /ai"""


def classify_by_keywords(text: str) -> Optional[Intent]:
    """Быстрая классификация по ключевым словам без AI."""
    text_lower = text.lower().strip()
    for keywords, intent in KEYWORD_MAP:
        for kw in keywords:
            if kw in text_lower:
                return intent
    return None


async def classify_by_brain_ai(text: str, language: str = "ru") -> "Intent | str":
    """
    Brain AI — определяет к какому СЕРВИСУ относится запрос.
    Использует Hub (первую доступную модель).

    Возвращает Intent если нашёл, или NEEDS_CLARIFICATION если нет.
    НЕ является AI-чатом — только классификатор.
    """
    from services.ai_provider.hub import get_hub

    service_intents = [
        i.value for i in Intent
        if i not in (Intent.UNKNOWN, Intent.AI_CHAT, Intent.CLARIFICATION)
    ]
    intent_list = ", ".join(service_intents)

    system_prompt = (
        f"You are a service router for a Telegram bot. "
        f"Your ONLY job is to map user messages to exactly one service name.\n\n"
        f"Available services: {intent_list}\n\n"
        f"Rules:\n"
        f"- Return ONLY the service name (e.g. 'weather'), nothing else\n"
        f"- If the message is casual conversation, greeting, joke, or question not matching any service → return 'needs_clarification'\n"
        f"- If unsure → return 'needs_clarification'\n"
        f"- User language: {language}"
    )

    hub = get_hub()
    try:
        response_text, provider = await hub.chat(
            messages=[{"role": "user", "content": text}],
            system=system_prompt,
            max_tokens=15,
            temperature=0,
        )
        result = response_text.strip().lower().replace("-", "_")
        logger.debug(f"[BrainAI] '{text}' → '{result}' via {provider}")

        if result == "needs_clarification":
            return NEEDS_CLARIFICATION

        try:
            return Intent(result)
        except ValueError:
            return NEEDS_CLARIFICATION

    except Exception as e:
        logger.warning(f"[BrainAI] Failed: {e}")
        return NEEDS_CLARIFICATION


async def build_clarification_message(text: str, language: str = "ru") -> str:
    """
    Генерирует короткую подсказку когда Brain AI не смог определить сервис.
    Помогает пользователю переформулировать запрос.
    Это служебное сообщение — НЕ AI_CHAT диалог.
    """
    from services.ai_provider.hub import get_hub

    system_prompt = (
        f"Ты помощник Telegram-бота. Пользователь написал запрос, который ты не смог распознать.\n"
        f"Напиши КОРОТКИЙ ответ (2-3 строки):\n"
        f"1. Скажи что не понял запрос (одна фраза)\n"
        f"2. Предложи 1-2 конкретных варианта что он мог иметь в виду, используя примеры:\n"
        f"{SERVICE_HINTS}\n\n"
        f"Отвечай на языке: {language}\n"
        f"Без markdown, дружелюбно и коротко."
    )

    hub = get_hub()
    try:
        response_text, _ = await hub.chat(
            messages=[{"role": "user", "content": f"Запрос пользователя: {text}"}],
            system=system_prompt,
            max_tokens=120,
            temperature=0.4,
        )
        return response_text.strip()
    except Exception as e:
        logger.warning(f"[BrainAI] Clarification generation failed: {e}")
        return (
            "🤔 Не совсем понял запрос.\n\n"
            "Напиши /help чтобы увидеть всё что я умею,\n"
            "или /ai чтобы просто поговорить."
        )


async def classify(text: str, language: str = "ru") -> Intent:
    """
    Главная функция классификации.

    1. Ключевые слова → Intent (без AI)
    2. Brain AI → Intent (если распознал сервис)
    3. Не распознал → Intent.CLARIFICATION
       (router.py отправит уточняющее сообщение через build_clarification_message)

    AI_CHAT включается ТОЛЬКО когда:
    - пользователь явно написал /ai или "поговори со мной" (ключевые слова)
    - ни один сервис не подошёл после повторного запроса с уточнением
    """
    if not text or not text.strip():
        return Intent.UNKNOWN

    # 1. Ключевые слова
    intent = classify_by_keywords(text)
    if intent:
        logger.debug(f"[Classifier] keyword → {intent.value}")
        return intent

    # 2. Brain AI
    result = await classify_by_brain_ai(text, language)
    if result != NEEDS_CLARIFICATION:
        logger.debug(f"[Classifier] brain_ai → {result.value}")
        return result

    # 3. Нужно уточнение
    logger.debug(f"[Classifier] clarification needed for: '{text}'")
    return Intent.CLARIFICATION

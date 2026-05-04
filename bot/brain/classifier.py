"""
brain/classifier.py — Классификатор интентов.
Определяет intent по тексту пользователя.

Стратегия:
1. Быстрая проверка по ключевым словам (без AI, мгновенно)
2. Если не определён — GPT-4o mini для точной классификации
3. Fallback → Intent.AI_CHAT (не Unknown, чтобы не терять запрос)
"""

from __future__ import annotations
import re
import json
import logging
from typing import Optional

from bot.brain.intent import Intent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Карта ключевых слов → интент
# Порядок важен: более специфичные правила — выше
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

    # Модерация групп
    (["/warn", "выдать варн", "предупреждение"], Intent.GROUP_WARN),
    (["/ban", "забанить", "бан пользователя"], Intent.GROUP_BAN),
    (["/mute", "заглушить", "мут"], Intent.GROUP_MUTE),
    (["/kick", "кикнуть", "выгнать"], Intent.GROUP_KICK),
    (["/groupsettings", "настройки группы"], Intent.GROUP_SETTINGS),
    (["/stats", "статистика группы"], Intent.GROUP_STATS),
    (["/setwelcome", "приветствие группы", "настроить приветствие"], Intent.GROUP_WELCOME),
]


def classify_by_keywords(text: str) -> Optional[Intent]:
    """
    Быстрая классификация по ключевым словам.
    Работает без AI — O(n) по размеру карты.
    """
    text_lower = text.lower().strip()
    for keywords, intent in KEYWORD_MAP:
        for kw in keywords:
            if kw in text_lower:
                return intent
    return None


async def classify_by_ai(text: str, language: str = "ru") -> Intent:
    """
    Классификация через GPT-4o mini.
    Используется только когда ключевые слова не помогли.
    Возвращает Intent или Intent.AI_CHAT как fallback.
    """
    import os
    import openai

    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    intent_values = [i.value for i in Intent if i not in (Intent.UNKNOWN,)]
    intent_list = ", ".join(intent_values)

    system_prompt = f"""You are an intent classifier for a Telegram bot assistant.
Classify the user's message into exactly one intent from this list:
{intent_list}

Rules:
- If the message is a general question or conversation → ai_chat
- If unsure → ai_chat
- Return ONLY the intent string, nothing else.
- Language of user: {language}"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            max_tokens=20,
            temperature=0,
        )
        result = response.choices[0].message.content.strip().lower()
        # Валидируем что вернули допустимый Intent
        try:
            return Intent(result)
        except ValueError:
            return Intent.AI_CHAT
    except Exception as e:
        logger.warning(f"AI classification failed: {e}")
        return Intent.AI_CHAT


async def classify(text: str, language: str = "ru") -> Intent:
    """
    Главная функция классификации.
    1. Ключевые слова (быстро)
    2. AI (точно, но медленнее)
    3. Fallback → AI_CHAT
    """
    if not text or not text.strip():
        return Intent.AI_CHAT

    # Команды Telegram начинаются с /
    if text.startswith("/"):
        intent = classify_by_keywords(text)
        if intent:
            return intent

    # Сначала быстрая проверка
    intent = classify_by_keywords(text)
    if intent:
        return intent

    # Если не определили — спрашиваем AI
    return await classify_by_ai(text, language)

"""
brain/classifier.py — Классификатор интентов.

Pipeline:
  1. Regex-паттерны (быстро, гибко — ловит глаголы, вопросы, падежи)
  2. Redis-кэш (п.4) — если Brain AI уже отвечал на похожий текст
  3. Brain AI (Hub) → определяет сервис ИЛИ решает что это AI_CHAT
     └─ Fallback chain (п.6): основной → запасной провайдер → TF-IDF эвристика
  4. CLARIFICATION → только если все уровни не дали ответа

Brain AI и AI Chat — разные сущности:
  - Brain AI: классификатор, не ведёт диалог, только маршрутизирует
  - AI Chat: разговорный агент с историей (services/ai_chat/chat.py)

Изменения:
  п.3 — PATTERN_MAP получил 3-й элемент strict: bool (вместо хрупкого split)
  п.4 — get_cached_intent / set_cached_intent обёртывают вызов Brain AI
  п.6 — fallback chain: Brain AI → keyword эвристика → CLARIFICATION
"""

from __future__ import annotations
import re
import logging
from typing import Optional

from bot.brain.intent import Intent

logger = logging.getLogger(__name__)

NEEDS_CLARIFICATION = "__needs_clarification__"

# ---------------------------------------------------------------------------
# ПАТТЕРНЫ → интент
# Формат: (regex_pattern, Intent, strict)
#   strict=True  → паттерн используется в classify_by_patterns_strict()
#                  (группы без обращения к боту) — должен начинаться с ^ или /
#   strict=False → используется всегда
#
# Порядок важен: специфичные — выше
# ---------------------------------------------------------------------------
PATTERN_MAP: list[tuple[str, Intent, bool]] = [

    # --- Системные ---
    (r"^/start\b|^старт$|^начать$", Intent.START, True),
    (r"^/help\b|помог|что умеешь|список команд|что ты умеешь|команды", Intent.HELP, True),
    (r"кто тебя создал|кто твой создатель|кто тебя сделал|кто разработчик|кто твой разработчик|кто твой автор|кто написал тебя|кто тебя написал|кто твой владелец", Intent.WHO_MADE_YOU, False),
    (r"^/settings\b|настройк|настроить бота", Intent.SETTINGS, True),

    # --- Профиль ---
    (r"^/profile\b|мой профил|моя анкет|посмотреть профил", Intent.PROFILE_VIEW, True),
    (r"(измени|редактир|поменя|сменить|обнови).*(профил|имя|никнейм|ассистент)", Intent.PROFILE_EDIT, False),

    # --- Экономика ---
    (r"^/balance\b|^баланс$|^мой баланс$|^мои монеты$|сколько.*(монет|экоин|ecoins)|покажи баланс", Intent.BALANCE, True),
    (r"^/daily\b|^бонус$|ежедневн|бонус дня|дейли", Intent.DAILY_BONUS, True),
    (r"^(передать|дать|отдать|скинуть)\s+\d+|^/transfer\b", Intent.TRANSFER, True),
    (r"^/referral\b|^рефералы$|^реф$|^рефер$|реферальная ссылка|моя реф", Intent.REFERRAL, True),
    (r"^/top\b|^лидеры$|^топ$|таблица лидеров|лучшие по монетам", Intent.LEADERBOARD, True),

    # --- Питомец ---
    (r"^/pet\b|^питомец$|^мой питомец$|меню питомца|главное меню питомца", Intent.PET_MENU, True),
    (r"состояние питомца|как питомец|питомец жив|статус питомца", Intent.PET_STATUS, False),
    (r"^покорми питомца$|^накорми питомца$|покорм.{0,10}питомц|питомец голод", Intent.PET_FEED, True),
    (r"^поиграй с питомцем$|^поиграть с питомцем$|поигра.{0,10}питомц|питомец скуча", Intent.PET_PLAY, True),
    (r"^лечить питомца$|^вылечить питомца$|^лечи питомца$|вылеч.{0,10}питомц|питомец бол", Intent.PET_HEAL, True),
    (r"^создать питомца$|^завести питомца$|^новый питомец$|хочу питомц|купить питомц", Intent.PET_NEW, True),
    (r"^сменить имя питомцу$|^переименовать питомца$|^новое имя питомцу$", Intent.PET_RENAME, True),

    # --- Отношения ---
    (r"^встречаться$|^встречайся$", Intent.RELATIONSHIP_PROPOSE, True),
    (r"^мои отношения$|^мой брак$|^мои отнош$|статус отношений|статус брака", Intent.RELATIONSHIP_STATUS, True),
    (r"^расстаться$|^расстанемся$", Intent.RELATIONSHIP_BREAKUP, True),
    (r"^брак$|^пожениться$", Intent.MARRIAGE_PROPOSE, True),
    (r"^развод$|^развестись$", Intent.MARRIAGE_DIVORCE, True),
    (r"(добав|стать|хочу быть).*(брат|сестр|отц|мать|усынов|семь)", Intent.FAMILY_ADD, False),
    (r"моя семья|семейное дерево|список семьи|семья", Intent.FAMILY_VIEW, False),

    # --- Действия (реплай на пользователя в группе) ---
    # ^ чтобы строгий классификатор группового чата их видел
    (r"^(обним|обнять|поцелу|поцеловать|погладь|погладить|ударь|ударить|подари|подарить|укуси|укусить|станцу|станцевать|потанцевать|подмигн|подмигнуть|прижм|прижать|похлопа|похлопать|дать пять|дай пять|подбодр|подбодрить|угости|угостить|поаплодир|поаплодировать)", Intent.ACTION_DO, True),

    # --- Чёрный список ---
    (r"^(заблокир|заблокируй|заблокировать|блок|блокировать|в чс|добавить в чс|добавь в чс|чс)$|^(заблокир|добав).*(пользовател|чс|чёрн)|чёрный список", Intent.BLACKLIST_ADD, True),
    (r"^(разблокир|разблокируй|разблокировать|разблок|убрать из чс|убери из чс|из чс)$|^(разблокир|убра).*(пользовател|чс|чёрн)", Intent.BLACKLIST_REMOVE, True),
    (r"^/blacklist\b|^чс$|^мой чс$|^чёрный список$|покажи чс|покажи чёрный список|список заблокированных|мои заблокированные", Intent.BLACKLIST_VIEW, True),

    # --- События ---
    (r"(создай|создать|новое|организ).*(событи|встреч|меропри)|^/event\b", Intent.EVENT_CREATE, True),
    (r"(список|ближайш|покажи).*(событи|встреч)|^/events\b", Intent.EVENT_LIST, True),
    (r"(участвовать|участвую|присоединить|хочу на).*(событи|встреч)", Intent.EVENT_JOIN, False),

    # --- Казино ---
    # казино — только без аргументов
    (r"^/casino\b|^казино$", Intent.CASINO_OPEN, True),
    # слоты [ставка]
    (r"^/slots\b|^/слоты\b|^слоты(\s+\d+)?$", Intent.CASINO_SLOTS, True),
    # рулетка [тип] [ставка]  — тип: к/ч/чет/нечет/мало/много/0-36
    (r"^/roulette\b|^/рулетка\b|^рулетка(\s+\S+)?(\s+\d+)?$", Intent.CASINO_ROULETTE, True),
    # кости [число 1-6] [ставка]
    (r"^/dice\b|^/кости\b|^кости(\s+\d+)?(\s+\d+)?$", Intent.CASINO_DICE, True),
    # монетка [о/р] [ставка]
    (r"^/coin\b|^/монетка\b|^монетка(\s+\S+)?(\s+\d+)?$", Intent.CASINO_COIN, True),
    # мины [ставка]
    (r"^/mines\b|^/мины\b|^мины(\s+\d+)?$", Intent.CASINO_MINES, True),
    # джокер [ставка]
    (r"^/joker\b|^/джокер\b|^джокер(\s+\d+)?$", Intent.CASINO_JOKER, True),
    # колесо [ставка]
    (r"^/wheel\b|^/колесо\b|^колесо(\s+\d+)?$", Intent.CASINO_WHEEL, True),

    # --- Мини-игры ---
    (r"^/quiz\b|викторина|quiz|задай вопрос|тест на знания", Intent.GAME_QUIZ, True),
    (r"кубик|брось кубик|кинь кубик", Intent.GAME_DICE, False),  # /dice убран — занят CASINO_DICE
    (r"правда или действие|^/truth\b|^/dare\b|truth or dare", Intent.GAME_TRUTH_DARE, True),
    (r"что бы ты выбрал|что лучше|^/wouldyou\b|выбор между", Intent.GAME_WOULD_YOU, True),
    (r"загадк|загадай|^/riddle\b|задай загадку", Intent.GAME_RIDDLE, True),

    # --- Медиасервисы ---
    (r"(найди|скачай|включи|поставь|хочу послушать|поищи|сыграй).*(музык|трек|песн|song|music)|хочу послушать|музыкальн|включи.*(рок|джаз|поп|рэп|хип.хоп)", Intent.MUSIC_SEARCH, False),
    (r"(какая|какой|узнай|скажи|покажи|будет).*(погода|погоду|температур|осадки|дождь|снег|ветер)|(какой|какая).*(прогноз|погода)|прогноз на (завтра|неделю|сегодня)|прогноз погоды|погода в|^/weather\b", Intent.WEATHER, True),
    (r"(как сказать|как будет|как переводится|переведи|перевод|переводи).*(на |по )|как по-(русски|английски|немецки|французски|испански|китайски|японски)|как сказать .* по|translate|^/translate\b", Intent.TRANSLATE, True),
    (r"нарисуй|сгенерируй|создай картинк|сделай картинк|изобрази|генерировать изображение", Intent.IMAGE_GEN, False),
    (r"(что такое|кто такой|кто такая|расскажи о|объясни|что значит|значение слова|wiki|энциклопедия)", Intent.ENCYCLOPEDIA, False),
    (r"(найди|рекоменд|посоветуй|хочу читать|ищу).*(книг|автор|роман|повест)|^/book\b", Intent.BOOK_SEARCH, True),
    (r"(найди|рекоменд|посоветуй|хочу смотреть|ищу).*(аниме|anime)|^/anime\b", Intent.ANIME_SEARCH, True),

    # --- Задачи ---
    (r"(создай|добавь|новая|запиши|поставь).*(задач|todo|дело|цель)|^/todo\b", Intent.TASK_CREATE, True),
    (r"(мои|список|покажи|все).*(задач|todo|дела)|^/tasks\b", Intent.TASK_LIST, True),
    (r"(выполнил|сделал|готово|закрой|отметь).*(задач|дело|пункт)|задача выполнена", Intent.TASK_DONE, False),
    (r"(напомни|напоминание|установи напоминание|не забудь|remind)|^/remind\b", Intent.REMINDER_CREATE, True),

    # --- AI чат — явный запрос на разговор ---
    (r"^/ai\b|^/chat\b|поговори со мной|давай поговорим|пообщайся|поболтай", Intent.AI_CHAT, True),

    # --- Модерация групп ---
    # Снять варн / варны — ВЫШЕ варна, чтобы не перехватывался
    (r"^/unwarn\b|снять варн|убрать варн|удалить варн|\-варн|\bunwarn\b", Intent.GROUP_UNWARN, True),
    (r"^/warns\b|\bварны\b|сколько варнов|проверить варны", Intent.GROUP_WARNS, True),
    (r"^/clearwarns\b|очистить варны|сбросить варны|снять варны|убрать варны", Intent.GROUP_CLEARWARNS, True),
    # Варн
    (r"^/warn\b|\bварн\b|варнить|предупредить|предупреждение\b|\bwarn\b", Intent.GROUP_WARN, True),
    # Разбан — ВЫШЕ бана
    (r"^/unban\b|\bразбан\b|разбанить|разблокировать\b|\bunban\b", Intent.GROUP_UNBAN, True),
    # Бан
    (r"^/ban\b|\bбан\b|забанить|\bban\b", Intent.GROUP_BAN, True),
    # Размут — ВЫШЕ мута
    (r"^/unmute\b|\bразмут\b|размутить|разглушить|говори снова|\bunmute\b", Intent.GROUP_UNMUTE, True),
    # Мут
    (r"^/mute\b|\bмут\b|замутить|заглушить|помолчи|заткнись|молчать|замолчи|\bsilence\b|\bmute\b", Intent.GROUP_MUTE, True),
    # Кик
    # Повышение / понижение
    (r"^/promote\b|\bповысить\b|повышение\b|продвинуть\b|\bpromote\b|назначить\b", Intent.GROUP_PROMOTE, True),
    (r"^/demote\b|\bпонизить\b|понижение\b|разжаловать\b|\bdemote\b|снять роль", Intent.GROUP_DEMOTE, True),
    # Настройки / статистика / приветствие
    (r"^/groupsettings\b|настройки группы", Intent.GROUP_SETTINGS, True),
    (r"^/stats\b|\bстатистика\b|активность группы", Intent.GROUP_STATS, True),
    (r"^/setwelcome\b|приветствие группы|настроить приветствие", Intent.GROUP_WELCOME, True),
    # Роль / администраторы — ВЫШЕ профиля чтобы не перехватывался
    (r"^/role\b|моя роль|какая моя роль|кто я в группе|мой статус в группе|мои права в группе", Intent.GROUP_ROLE, True),
    (r"^/admins\b|список админов|кто админ|администраторы группы|модераторы группы|кто модератор|кто управляет", Intent.GROUP_ADMINS, True),
]

# Компилируем паттерны один раз при загрузке модуля
_COMPILED: list[tuple[re.Pattern, Intent, bool]] = [
    (re.compile(pattern, re.IGNORECASE | re.UNICODE), intent, strict)
    for pattern, intent, strict in PATTERN_MAP
]

# ---------------------------------------------------------------------------
# Подсказки сервисов
# ---------------------------------------------------------------------------
SERVICE_HINTS = """🌤 Погода — «какая погода в Москве»
🎵 Музыка — «найди музыку [название]»
🌐 Перевод — «переведи [текст] на английский»
🖼 Картинка — «нарисуй [описание]»
📚 Энциклопедия — «что такое [слово]»
📖 Книги — «найди книгу [название]»
🎌 Аниме — «найди аниме [название]»
📝 Задача — «создай задачу [название]»
⏰ Напоминание — «напомни [о чём] [дата время]»
🎰 Казино — «казино» или /casino
💰 Баланс — «баланс» или /balance
🐾 Питомец — «питомец» или /pet
🚫 Чёрный список — «мой чс» или /blacklist
👤 Моя роль — «моя роль» или /role
👥 Администраторы — «список админов» или /admins
💬 Просто поговорить — /ai"""


def classify_by_patterns(text: str) -> Optional[Intent]:
    """
    Классификация через regex-паттерны.
    Гибче ключевых слов — ловит глаголы, вопросительные формы, падежи.
    """
    for pattern, intent, _strict in _COMPILED:
        if pattern.search(text):
            return intent
    return None


def classify_by_patterns_strict(text: str) -> Optional[Intent]:
    """
    Строгая классификация для группового чата БЕЗ обращения по имени бота.
    Срабатывает только на паттерны с флагом strict=True в PATTERN_MAP.
    Исключает случайные срабатывания на обычный разговор.

    п.3: теперь использует явный флаг strict вместо хрупкого split/parse.
    """
    for pattern, intent, strict in _COMPILED:
        if not strict:
            continue
        if pattern.search(text):
            return intent
    return None


def _keyword_fallback(text: str) -> "Intent | str":
    """
    п.6: Последний уровень fallback — простая keyword-эвристика.
    Используется если Brain AI полностью недоступен.
    Покрывает самые частые команды без AI-вызова.
    """
    t = text.lower()
    if any(w in t for w in ("погода", "weather", "температур", "дождь", "снег")):
        return Intent.WEATHER
    if any(w in t for w in ("перевед", "перевод", "translate", "как сказать")):
        return Intent.TRANSLATE
    if any(w in t for w in ("музык", "трек", "песн", "music", "song")):
        return Intent.MUSIC_SEARCH
    if any(w in t for w in ("баланс", "монет", "balance", "wallet")):
        return Intent.BALANCE
    if any(w in t for w in ("питомец", "pet", "покорм", "поиграй с")):
        return Intent.PET_MENU
    if any(w in t for w in ("задач", "todo", "напомни", "remind")):
        return Intent.TASK_CREATE
    if any(w in t for w in ("привет", "hello", "hi", "как дела", "что делаешь")):
        return Intent.AI_CHAT
    return NEEDS_CLARIFICATION


async def classify_by_brain_ai(text: str, language: str = "ru") -> "Intent | str":
    """
    Brain AI — определяет к какому СЕРВИСУ относится запрос,
    или решает что это разговорный AI_CHAT.

    Возвращает Intent или NEEDS_CLARIFICATION.
    НЕ является AI-чатом — только маршрутизатор.

    п.4: результат кэшируется в Redis (TTL 5 мин).
    п.6: при полном падении Hub → keyword-эвристика (_keyword_fallback).
    """
    from services.ai_provider.hub import get_hub
    from bot.brain.cache import get_cached_intent, set_cached_intent
    from bot.brain.telemetry import record_intent, record_provider, record_latency_ms
    import time

    # п.4: проверяем кэш
    cached = await get_cached_intent(text)
    if cached is not None:
        await record_intent(cached, source="cache")
        return cached

    service_intents = [
        i.value for i in Intent
        if i not in (Intent.UNKNOWN, Intent.CLARIFICATION)
    ]
    intent_list = ", ".join(service_intents)

    system_prompt = (
        f"You are a request router for a Telegram bot. "
        f"Your ONLY job: map the user message to one service name.\n\n"
        f"Available services: {intent_list}\n\n"
        f"Rules:\n"
        f"- Return ONLY the service name, nothing else (e.g. 'weather')\n"
        f"- Casual conversation, greetings, math questions, general knowledge, jokes, emotions → return 'ai_chat'\n"
        f"- Message clearly matches a service → return that service name\n"
        f"- Completely unclear, unrelated to any service AND not conversational → return 'needs_clarification'\n"
        f"- User language: {language}"
    )

    hub = get_hub()
    t0 = time.monotonic()
    try:
        response_text, provider = await hub.chat(
            messages=[{"role": "user", "content": text}],
            system=system_prompt,
            max_tokens=15,
            temperature=0,
        )
        elapsed_ms = (time.monotonic() - t0) * 1000

        # п.7: телеметрия
        await record_latency_ms(elapsed_ms)
        await record_provider(provider)

        result = response_text.strip().lower().replace("-", "_")
        logger.debug(f"[BrainAI] '{text[:40]}' → '{result}' via {provider} ({elapsed_ms:.0f}ms)")

        if result == "needs_clarification":
            return NEEDS_CLARIFICATION

        try:
            intent = Intent(result)
            # п.4: кладём в кэш
            await set_cached_intent(text, intent)
            await record_intent(intent, source="brain_ai")
            return intent
        except ValueError:
            return NEEDS_CLARIFICATION

    except RuntimeError as e:
        # п.6: все провайдеры упали → keyword-эвристика
        logger.warning(f"[BrainAI] All providers failed, using keyword fallback: {e}")
        result = _keyword_fallback(text)
        if result != NEEDS_CLARIFICATION:
            logger.info(f"[BrainAI] Keyword fallback → {result}")
        return result

    except Exception as e:
        logger.warning(f"[BrainAI] Failed: {e}")
        return NEEDS_CLARIFICATION


async def build_clarification_message(text: str, language: str = "ru") -> str:
    """
    Генерирует подсказку когда запрос совсем непонятен.
    Служебное сообщение — НЕ AI_CHAT диалог.
    """
    from services.ai_provider.hub import get_hub

    system_prompt = (
        f"Ты помощник Telegram-бота. Пользователь написал непонятный запрос.\n"
        f"Напиши КОРОТКИЙ ответ (2-3 строки максимум):\n"
        f"1. Одна фраза — что не понял\n"
        f"2. 1-2 конкретных варианта что он мог иметь в виду\n\n"
        f"Доступные сервисы:\n{SERVICE_HINTS}\n\n"
        f"Отвечай на языке: {language}. Без markdown. Дружелюбно и коротко."
    )

    hub = get_hub()
    try:
        response_text, _ = await hub.chat(
            messages=[{"role": "user", "content": f"Запрос: {text}"}],
            system=system_prompt,
            max_tokens=120,
            temperature=0.4,
        )
        return response_text.strip()
    except Exception as e:
        logger.warning(f"[BrainAI] Clarification failed: {e}")
        return (
            "🤔 Не совсем понял запрос.\n\n"
            "Напиши /help чтобы увидеть всё что я умею,\n"
            "или /ai чтобы просто поговорить."
        )


async def classify(text: str, language: str = "ru") -> Intent:
    """
    Главная функция классификации.

    1. Regex-паттерны → Intent (без AI, гибко)
    2. Brain AI → Intent.AI_CHAT | конкретный Intent
    3. Совсем непонятно → Intent.CLARIFICATION
    """
    if not text or not text.strip():
        return Intent.UNKNOWN

    # 1. Паттерны
    intent = classify_by_patterns(text)
    if intent:
        logger.debug(f"[Classifier] pattern → {intent.value}")
        return intent

    # 2. Brain AI
    result = await classify_by_brain_ai(text, language)
    if result != NEEDS_CLARIFICATION:
        logger.debug(f"[Classifier] brain_ai → {result.value}")
        return result

    # 3. Нужно уточнение
    logger.debug(f"[Classifier] clarification needed: '{text}'")
    return Intent.CLARIFICATION

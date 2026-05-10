"""
brain/classifier.py — Классификатор интентов.

Pipeline:
  1. Regex-паттерны (быстро, гибко — ловит глаголы, вопросы, падежи)
  2. Brain AI (Hub) → определяет сервис ИЛИ решает что это AI_CHAT
  3. CLARIFICATION → только если Brain AI совсем не понял

Brain AI и AI Chat — разные сущности:
  - Brain AI: классификатор, не ведёт диалог, только маршрутизирует
  - AI Chat: разговорный агент с историей (services/ai_chat/chat.py)
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
# re.search() по тексту в нижнем регистре
# Порядок важен: специфичные — выше
# ---------------------------------------------------------------------------
PATTERN_MAP: list[tuple[str, Intent]] = [

    # --- Системные ---
    (r"^/start\b|^старт$|^начать$", Intent.START),
    (r"^/help\b|помог|что умеешь|список команд|что ты умеешь|команды", Intent.HELP),
    (r"кто тебя создал|кто твой создатель|кто тебя сделал|кто разработчик|кто твой разработчик|кто твой автор|кто написал тебя|кто тебя написал|кто твой владелец", Intent.WHO_MADE_YOU),
    (r"^/settings\b|настройк|настроить бота", Intent.SETTINGS),

    # --- Профиль ---
    (r"^/profile\b|мой профил|моя анкет|посмотреть профил", Intent.PROFILE_VIEW),
    (r"(измени|редактир|поменя|сменить|обнови).*(профил|имя|никнейм|ассистент)", Intent.PROFILE_EDIT),

    # --- Экономика ---
    (r"^/balance\b|^баланс$|^мой баланс$|^мои монеты$|сколько.*(монет|экоин|ecoins)|покажи баланс", Intent.BALANCE),
    (r"^/daily\b|^бонус$|ежедневн|бонус дня|дейли", Intent.DAILY_BONUS),
    (r"^(передать|дать|отдать|скинуть)\s+\d+|^/transfer\b", Intent.TRANSFER),
    (r"^/referral\b|^рефералы$|^реф$|^рефер$|реферальная ссылка|моя реф", Intent.REFERRAL),
    (r"^/top\b|^лидеры$|^топ$|таблица лидеров|лучшие по монетам", Intent.LEADERBOARD),

    # --- Питомец ---
    (r"^/pet\b|^питомец$|^мой питомец$|меню питомца|главное меню питомца", Intent.PET_MENU),
    (r"состояние питомца|как питомец|питомец жив|статус питомца", Intent.PET_STATUS),
    (r"^покорми питомца$|^накорми питомца$|покорм.{0,10}питомц|питомец голод", Intent.PET_FEED),
    (r"^поиграй с питомцем$|^поиграть с питомцем$|поигра.{0,10}питомц|питомец скуча", Intent.PET_PLAY),
    (r"^лечить питомца$|^вылечить питомца$|^лечи питомца$|вылеч.{0,10}питомц|питомец бол", Intent.PET_HEAL),
    (r"^создать питомца$|^завести питомца$|^новый питомец$|хочу питомц|купить питомц", Intent.PET_NEW),
    (r"^сменить имя питомцу$|^переименовать питомца$|^новое имя питомцу$", Intent.PET_RENAME),

    # --- Отношения ---
    (r"^встречаться$|^встречайся$", Intent.RELATIONSHIP_PROPOSE),
    (r"^мои отношения$|^мой брак$|^мои отнош$|статус отношений|статус брака", Intent.RELATIONSHIP_STATUS),
    (r"^расстаться$|^расстанемся$", Intent.RELATIONSHIP_BREAKUP),
    (r"^брак$|^пожениться$", Intent.MARRIAGE_PROPOSE),
    (r"^развод$|^развестись$", Intent.MARRIAGE_DIVORCE),
    (r"(добав|стать|хочу быть).*(брат|сестр|отц|мать|усынов|семь)", Intent.FAMILY_ADD),
    (r"моя семья|семейное дерево|список семьи|семья", Intent.FAMILY_VIEW),

    # --- Действия (реплай на пользователя в группе) ---
    # ^ чтобы строгий классификатор группового чата их видел
    (r"^(обним|обнять|поцелу|поцеловать|погладь|погладить|ударь|ударить|подари|подарить|укуси|укусить|станцу|станцевать|потанцевать|подмигн|подмигнуть|прижм|прижать|похлопа|похлопать|дать пять|дай пять|подбодр|подбодрить|угости|угостить|поаплодир|поаплодировать)", Intent.ACTION_DO),

    # --- Чёрный список ---
    (r"(заблокир|добав).*(пользовател|чс|чёрн)|чёрный список", Intent.BLACKLIST_ADD),
    (r"(разблокир|убра).*(пользовател|чс|чёрн)", Intent.BLACKLIST_REMOVE),
    (r"^/blacklist\b|^чс$|^мой чс$|^чёрный список$|покажи чс|покажи чёрный список|список заблокированных|мои заблокированные", Intent.BLACKLIST_VIEW),

    # --- События ---
    (r"(создай|создать|новое|организ).*(событи|встреч|меропри)|^/event\b", Intent.EVENT_CREATE),
    (r"(список|ближайш|покажи).*(событи|встреч)|^/events\b", Intent.EVENT_LIST),
    (r"(участвовать|участвую|присоединить|хочу на).*(событи|встреч)", Intent.EVENT_JOIN),

    # --- Казино ---
    # казино — только без аргументов
    (r"^/casino\b|^казино$", Intent.CASINO_OPEN),
    # слоты [ставка]
    (r"^/slots\b|^/слоты\b|^слоты(\s+\d+)?$", Intent.CASINO_SLOTS),
    # рулетка [тип] [ставка]  — тип: к/ч/чет/нечет/мало/много/0-36
    (r"^/roulette\b|^/рулетка\b|^рулетка(\s+\S+)?(\s+\d+)?$", Intent.CASINO_ROULETTE),
    # кости [число 1-6] [ставка]
    (r"^/dice\b|^/кости\b|^кости(\s+\d+)?(\s+\d+)?$", Intent.CASINO_DICE),
    # монетка [о/р] [ставка]
    (r"^/coin\b|^/монетка\b|^монетка(\s+\S+)?(\s+\d+)?$", Intent.CASINO_COIN),
    # мины [ставка]
    (r"^/mines\b|^/мины\b|^мины(\s+\d+)?$", Intent.CASINO_MINES),
    # джокер [ставка]
    (r"^/joker\b|^/джокер\b|^джокер(\s+\d+)?$", Intent.CASINO_JOKER),
    # колесо [ставка]
    (r"^/wheel\b|^/колесо\b|^колесо(\s+\d+)?$", Intent.CASINO_WHEEL),

    # --- Мини-игры ---
    (r"^/quiz\b|викторина|quiz|задай вопрос|тест на знания", Intent.GAME_QUIZ),
    (r"кубик|брось кубик|кинь кубик", Intent.GAME_DICE),  # /dice убран — занят CASINO_DICE
    (r"правда или действие|^/truth\b|^/dare\b|truth or dare", Intent.GAME_TRUTH_DARE),
    (r"что бы ты выбрал|что лучше|^/wouldyou\b|выбор между", Intent.GAME_WOULD_YOU),
    (r"загадк|загадай|^/riddle\b|задай загадку", Intent.GAME_RIDDLE),

    # --- Медиасервисы ---
    (r"(найди|скачай|включи|поставь|хочу послушать|поищи|сыграй).*(музык|трек|песн|song|music)|хочу послушать|музыкальн|включи.*(рок|джаз|поп|рэп|хип.хоп)", Intent.MUSIC_SEARCH),
    (r"(какая|какой|узнай|скажи|покажи|будет).*(погода|погоду|температур|осадки|дождь|снег|ветер)|(какой|какая).*(прогноз|погода)|прогноз на (завтра|неделю|сегодня)|прогноз погоды|погода в|^/weather\b", Intent.WEATHER),
    (r"(как сказать|как будет|как переводится|переведи|перевод|переводи).*(на |по )|как по-(русски|английски|немецки|французски|испански|китайски|японски)|как сказать .* по|translate|^/translate\b", Intent.TRANSLATE),
    (r"нарисуй|сгенерируй|создай картинк|сделай картинк|изобрази|генерировать изображение", Intent.IMAGE_GEN),
    (r"(что такое|кто такой|кто такая|расскажи о|объясни|что значит|значение слова|wiki|энциклопедия)", Intent.ENCYCLOPEDIA),
    (r"(найди|рекоменд|посоветуй|хочу читать|ищу).*(книг|автор|роман|повест)|^/book\b", Intent.BOOK_SEARCH),
    (r"(найди|рекоменд|посоветуй|хочу смотреть|ищу).*(аниме|anime)|^/anime\b", Intent.ANIME_SEARCH),

    # --- Задачи ---
    (r"(создай|добавь|новая|запиши|поставь).*(задач|todo|дело|цель)|^/todo\b", Intent.TASK_CREATE),
    (r"(мои|список|покажи|все).*(задач|todo|дела)|^/tasks\b", Intent.TASK_LIST),
    (r"(выполнил|сделал|готово|закрой|отметь).*(задач|дело|пункт)|задача выполнена", Intent.TASK_DONE),
    (r"(напомни|напоминание|установи напоминание|не забудь|remind)|^/remind\b", Intent.REMINDER_CREATE),

    # --- AI чат — явный запрос на разговор ---
    (r"^/ai\b|^/chat\b|поговори со мной|давай поговорим|пообщайся|поболтай", Intent.AI_CHAT),

    # --- Модерация групп ---
    # Снять варн / варны — ВЫШЕ варна, чтобы не перехватывался
    (r"^/unwarn\b|снять варн|убрать варн|удалить варн|\-варн|\bunwarn\b", Intent.GROUP_UNWARN),
    (r"^/warns\b|\bварны\b|сколько варнов|проверить варны", Intent.GROUP_WARNS),
    (r"^/clearwarns\b|очистить варны|сбросить варны|снять варны|убрать варны", Intent.GROUP_CLEARWARNS),
    # Варн
    (r"^/warn\b|\bварн\b|варнить|предупредить|предупреждение\b|\bwarn\b", Intent.GROUP_WARN),
    # Разбан — ВЫШЕ бана
    (r"^/unban\b|\bразбан\b|разбанить|разблокировать\b|\bunban\b", Intent.GROUP_UNBAN),
    # Бан
    (r"^/ban\b|\bбан\b|забанить|\bban\b", Intent.GROUP_BAN),
    # Размут — ВЫШЕ мута
    (r"^/unmute\b|\bразмут\b|размутить|разглушить|говори снова|\bunmute\b", Intent.GROUP_UNMUTE),
    # Мут
    (r"^/mute\b|\bмут\b|замутить|заглушить|помолчи|заткнись|молчать|замолчи|\bsilence\b|\bmute\b", Intent.GROUP_MUTE),
    # Кик
    # Повышение / понижение
    (r"^/promote\b|\bповысить\b|повышение\b|продвинуть\b|\bpromote\b|назначить\b", Intent.GROUP_PROMOTE),
    (r"^/demote\b|\bпонизить\b|понижение\b|разжаловать\b|\bdemote\b|снять роль", Intent.GROUP_DEMOTE),
    # Настройки / статистика / приветствие
    (r"^/groupsettings\b|настройки группы", Intent.GROUP_SETTINGS),
    (r"^/stats\b|\bстатистика\b|активность группы", Intent.GROUP_STATS),
    (r"^/setwelcome\b|приветствие группы|настроить приветствие", Intent.GROUP_WELCOME),
    # Роль / администраторы — ВЫШЕ профиля чтобы не перехватывался
    (r"^/role\b|моя роль|какая моя роль|кто я в группе|мой статус в группе|мои права в группе", Intent.GROUP_ROLE),
    (r"^/admins\b|список админов|кто админ|администраторы группы|модераторы группы|кто модератор|кто управляет", Intent.GROUP_ADMINS),
]

# Компилируем паттерны один раз при загрузке модуля
_COMPILED: list[tuple[re.Pattern, Intent]] = [
    (re.compile(pattern, re.IGNORECASE | re.UNICODE), intent)
    for pattern, intent in PATTERN_MAP
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
    for pattern, intent in _COMPILED:
        if pattern.search(text):
            return intent
    return None


def classify_by_patterns_strict(text: str) -> Optional[Intent]:
    """
    Строгая классификация для группового чата БЕЗ обращения по имени бота.
    Срабатывает ТОЛЬКО на паттерны, привязанные к началу строки (^)
    или к слэш-командам (/command).
    Исключает случайные срабатывания на обычный разговор.
    """
    strict_pattern = re.compile(r'(?:^|\(\^)')
    for pattern, intent in _COMPILED:
        raw = pattern.pattern
        # Берём только паттерны, у которых хотя бы одна альтернатива начинается с ^ или /
        parts = raw.split("|")
        has_anchor = any(
            p.lstrip("(").startswith("^") or p.lstrip("(").startswith("/")
            for p in parts
        )
        if not has_anchor:
            continue
        if pattern.search(text):
            return intent
    return None


async def classify_by_brain_ai(text: str, language: str = "ru") -> "Intent | str":
    """
    Brain AI — определяет к какому СЕРВИСУ относится запрос,
    или решает что это разговорный AI_CHAT.

    Возвращает Intent или NEEDS_CLARIFICATION.
    НЕ является AI-чатом — только маршрутизатор.
    """
    from services.ai_provider.hub import get_hub

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

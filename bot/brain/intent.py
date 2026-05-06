"""
brain/intent.py — Все возможные интенты и их категории.
Brain определяет intent по тексту и маршрутизирует к нужному сервису.
"""

from __future__ import annotations
from enum import Enum


class Intent(str, Enum):
    # --- AI Чат ---
    AI_CHAT = "ai_chat"

    # --- Профиль ---
    PROFILE_VIEW = "profile_view"
    PROFILE_EDIT = "profile_edit"

    # --- Экономика ---
    BALANCE = "balance"
    DAILY_BONUS = "daily_bonus"
    TRANSFER = "transfer"
    REFERRAL = "referral"

    # --- Питомец ---
    PET_STATUS = "pet_status"
    PET_FEED = "pet_feed"
    PET_PLAY = "pet_play"
    PET_HEAL = "pet_heal"
    PET_NEW = "pet_new"

    # --- Виртуальный мир ---
    RELATIONSHIP_PROPOSE = "relationship_propose"
    RELATIONSHIP_STATUS = "relationship_status"
    RELATIONSHIP_BREAKUP = "relationship_breakup"
    MARRIAGE_PROPOSE = "marriage_propose"
    MARRIAGE_DIVORCE = "marriage_divorce"
    FAMILY_ADD = "family_add"
    FAMILY_VIEW = "family_view"
    ACTION_DO = "action_do"
    BLACKLIST_ADD = "blacklist_add"
    BLACKLIST_REMOVE = "blacklist_remove"

    # --- События ---
    EVENT_CREATE = "event_create"
    EVENT_LIST = "event_list"
    EVENT_JOIN = "event_join"

    # --- Казино ---
    CASINO_OPEN = "casino_open"
    CASINO_SLOTS = "casino_slots"
    CASINO_ROULETTE = "casino_roulette"
    CASINO_BLACKJACK = "casino_blackjack"
    CASINO_CRASH = "casino_crash"
    CASINO_POKER = "casino_poker"

    # --- Мини-игры ---
    GAME_QUIZ = "game_quiz"
    GAME_DICE = "game_dice"
    GAME_TRUTH_DARE = "game_truth_dare"
    GAME_WOULD_YOU = "game_would_you"
    GAME_RIDDLE = "game_riddle"

    # --- Медиасервисы ---
    MUSIC_SEARCH = "music_search"
    WEATHER = "weather"
    TRANSLATE = "translate"
    VOICE_TO_TEXT = "voice_to_text"
    IMAGE_GEN = "image_gen"
    ENCYCLOPEDIA = "encyclopedia"
    BOOK_SEARCH = "book_search"
    ANIME_SEARCH = "anime_search"

    # --- Задачи ---
    TASK_CREATE = "task_create"
    TASK_LIST = "task_list"
    TASK_DONE = "task_done"
    REMINDER_CREATE = "reminder_create"

    # --- Группы ---
    GROUP_WARN = "group_warn"
    GROUP_UNWARN = "group_unwarn"
    GROUP_WARNS = "group_warns"
    GROUP_CLEARWARNS = "group_clearwarns"
    GROUP_BAN = "group_ban"
    GROUP_UNBAN = "group_unban"
    GROUP_MUTE = "group_mute"
    GROUP_UNMUTE = "group_unmute"
    GROUP_PROMOTE = "group_promote"
    GROUP_DEMOTE = "group_demote"
    GROUP_SETTINGS = "group_settings"
    GROUP_STATS = "group_stats"
    GROUP_WELCOME = "group_welcome"
    GROUP_ROLE = "group_role"
    GROUP_ADMINS = "group_admins"
    GROUP_RULES = "group_rules"

    # --- Системные ---
    START = "start"
    HELP = "help"
    SETTINGS = "settings"
    UNKNOWN = "unknown"

    # --- Служебные (не хэндлеры, обрабатываются в router.py) ---
    CLARIFICATION = "clarification"   # Brain AI не смог определить сервис


# Категории интентов для быстрой проверки
CASINO_INTENTS = {
    Intent.CASINO_OPEN, Intent.CASINO_SLOTS, Intent.CASINO_ROULETTE,
    Intent.CASINO_BLACKJACK, Intent.CASINO_CRASH, Intent.CASINO_POKER,
}

GAME_INTENTS = {
    Intent.GAME_QUIZ, Intent.GAME_DICE, Intent.GAME_TRUTH_DARE,
    Intent.GAME_WOULD_YOU, Intent.GAME_RIDDLE,
}

MEDIA_INTENTS = {
    Intent.MUSIC_SEARCH, Intent.WEATHER, Intent.TRANSLATE,
    Intent.VOICE_TO_TEXT, Intent.IMAGE_GEN, Intent.ENCYCLOPEDIA,
    Intent.BOOK_SEARCH, Intent.ANIME_SEARCH,
}

VIRTUAL_WORLD_INTENTS = {
    Intent.RELATIONSHIP_PROPOSE, Intent.RELATIONSHIP_STATUS, Intent.RELATIONSHIP_BREAKUP,
    Intent.MARRIAGE_PROPOSE, Intent.MARRIAGE_DIVORCE,
    Intent.FAMILY_ADD, Intent.FAMILY_VIEW,
    Intent.ACTION_DO, Intent.BLACKLIST_ADD, Intent.BLACKLIST_REMOVE,
    Intent.PET_STATUS, Intent.PET_FEED, Intent.PET_PLAY, Intent.PET_HEAL, Intent.PET_NEW,
    Intent.EVENT_CREATE, Intent.EVENT_LIST, Intent.EVENT_JOIN,
}

ECONOMY_INTENTS = {
    Intent.BALANCE, Intent.DAILY_BONUS, Intent.TRANSFER, Intent.REFERRAL,
}

GROUP_MODERATION_INTENTS = {
    Intent.GROUP_WARN, Intent.GROUP_UNWARN, Intent.GROUP_WARNS, Intent.GROUP_CLEARWARNS,
    Intent.GROUP_BAN, Intent.GROUP_UNBAN,
    Intent.GROUP_MUTE, Intent.GROUP_UNMUTE,
    Intent.GROUP_PROMOTE, Intent.GROUP_DEMOTE,
    Intent.GROUP_SETTINGS, Intent.GROUP_STATS, Intent.GROUP_WELCOME,
    Intent.GROUP_ROLE, Intent.GROUP_ADMINS, Intent.GROUP_RULES,
}

TASK_INTENTS = {
    Intent.TASK_CREATE, Intent.TASK_LIST, Intent.TASK_DONE, Intent.REMINDER_CREATE,
}

# Интенты доступные только в личном чате
PRIVATE_ONLY_INTENTS = {
    Intent.PROFILE_EDIT, Intent.SETTINGS, Intent.DAILY_BONUS,
    Intent.TRANSFER, Intent.REFERRAL, Intent.PET_NEW,
    Intent.IMAGE_GEN, Intent.VOICE_TO_TEXT,
}

# ---------------------------------------------------------------------------
# Микросервисы — в группе вызываются ТОЛЬКО при обращении по имени ассистента
# ---------------------------------------------------------------------------
MICROSERVICE_INTENTS = {
    Intent.AI_CHAT,
    Intent.MUSIC_SEARCH, Intent.WEATHER, Intent.TRANSLATE,
    Intent.ENCYCLOPEDIA, Intent.BOOK_SEARCH, Intent.ANIME_SEARCH,
    Intent.IMAGE_GEN, Intent.VOICE_TO_TEXT,
    Intent.TASK_CREATE, Intent.TASK_LIST, Intent.TASK_DONE, Intent.REMINDER_CREATE,
}

# World-функции — работают в группе без обращения по имени
GROUP_WORLD_INTENTS = {
    Intent.GAME_QUIZ, Intent.GAME_DICE, Intent.GAME_TRUTH_DARE,
    Intent.GAME_WOULD_YOU, Intent.GAME_RIDDLE,
    Intent.ACTION_DO, Intent.RELATIONSHIP_PROPOSE, Intent.MARRIAGE_PROPOSE,
    Intent.EVENT_CREATE, Intent.EVENT_LIST, Intent.EVENT_JOIN,
    Intent.GROUP_WARN, Intent.GROUP_UNWARN, Intent.GROUP_WARNS, Intent.GROUP_CLEARWARNS,
    Intent.GROUP_BAN, Intent.GROUP_UNBAN,
    Intent.GROUP_MUTE, Intent.GROUP_UNMUTE,
    Intent.GROUP_PROMOTE, Intent.GROUP_DEMOTE,
    Intent.GROUP_SETTINGS, Intent.GROUP_STATS, Intent.GROUP_WELCOME,
    Intent.GROUP_ROLE, Intent.GROUP_ADMINS, Intent.GROUP_RULES,
    Intent.HELP, Intent.BALANCE, Intent.DAILY_BONUS,
    Intent.PET_STATUS, Intent.PET_FEED, Intent.PET_PLAY, Intent.PET_HEAL,
    Intent.CASINO_OPEN, Intent.CASINO_SLOTS, Intent.CASINO_ROULETTE,
    Intent.CASINO_BLACKJACK, Intent.CASINO_CRASH, Intent.CASINO_POKER,
    Intent.RELATIONSHIP_STATUS, Intent.RELATIONSHIP_BREAKUP,
    Intent.MARRIAGE_DIVORCE, Intent.FAMILY_ADD, Intent.FAMILY_VIEW,
    Intent.BLACKLIST_ADD, Intent.BLACKLIST_REMOVE,
    Intent.PROFILE_VIEW,
}

# Все интенты разрешённые в группах (объединение)
GROUP_ALLOWED_INTENTS = GROUP_WORLD_INTENTS | MICROSERVICE_INTENTS

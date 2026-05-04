"""
onboarding/states.py — Все FSM-состояния приложения.
"""

# --- Онбординг ---
ONBOARDING_LANGUAGE = "onboarding:language"
ONBOARDING_BOT_NAME = "onboarding:bot_name"
ONBOARDING_PERSONALITY = "onboarding:personality"
ONBOARDING_NICKNAME = "onboarding:nickname"
ONBOARDING_COMPLETE = "onboarding:complete"

# --- Настройки профиля ---
SETTINGS_ASSISTANT_NAME = "settings:assistant_name"
SETTINGS_NICKNAME = "settings:nickname"
SETTINGS_BIO = "settings:bio"
SETTINGS_BIRTHDAY = "settings:birthday"

# --- Питомец ---
PET_NAMING = "pet:naming"

# --- Задачи ---
TASK_AWAITING_TITLE = "task:awaiting_title"
TASK_AWAITING_DUE = "task:awaiting_due"
REMINDER_AWAITING_TEXT = "reminder:awaiting_text"
REMINDER_AWAITING_TIME = "reminder:awaiting_time"

# --- Перевод монет ---
TRANSFER_AWAITING_AMOUNT = "transfer:awaiting_amount"

# --- Казино ---
CASINO_AWAITING_BET = "casino:awaiting_bet"

# --- Группа ---
GROUP_AWAITING_WELCOME = "group:awaiting_welcome"
GROUP_AWAITING_WARN_REASON = "group:awaiting_warn_reason"

# --- События ---
EVENT_AWAITING_TITLE = "event:awaiting_title"
EVENT_AWAITING_DATE = "event:awaiting_date"
EVENT_AWAITING_DESCRIPTION = "event:awaiting_description"

# --- Семья ---
FAMILY_AWAITING_CONFIRM = "family:awaiting_confirm"

# --- Отношения ---
RELATIONSHIP_AWAITING_CONFIRM = "relationship:awaiting_confirm"


def is_active_fsm(state: str | None) -> bool:
    """Проверяет есть ли активное FSM-состояние."""
    return bool(state and ":" in state)

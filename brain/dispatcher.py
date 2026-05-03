"""
brain/dispatcher.py — Центральная точка регистрации всех хэндлеров.
Импортирует все модули-хэндлеры, чтобы декораторы @register() сработали.
Вызывается один раз при старте приложения.
"""

from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


def register_all_handlers() -> None:
    """
    Импортирует все хэндлеры — это запускает декораторы @register()
    и регистрирует их в brain/router.py.

    Порядок импортов не важен, т.к. каждый хэндлер регистрирует себя сам.
    """

    # --- Системные ---
    import brain.handlers.system          # /start, /help, /settings

    # --- Профиль ---
    import brain.handlers.profile         # просмотр и редактирование профиля

    # --- Экономика ---
    import brain.handlers.economy         # баланс, бонус, перевод, рефералы

    # --- Питомец ---
    import brain.handlers.pet             # все действия с питомцем

    # --- Виртуальный мир ---
    import brain.handlers.relationships   # отношения и браки
    import brain.handlers.family          # семейные роли
    import brain.handlers.actions         # действия между пользователями
    import brain.handlers.events          # события

    # --- Казино ---
    import brain.handlers.casino          # все игры казино

    # --- Мини-игры ---
    import brain.handlers.games           # quiz, dice, truth/dare, etc.

    # --- Медиасервисы ---
    import brain.handlers.media           # музыка, погода, перевод, энциклопедия, книги, аниме

    # --- AI-чат ---
    import brain.handlers.ai_chat         # основной AI-диалог

    # --- Задачи ---
    import brain.handlers.tasks           # todo и напоминания

    # --- Группы ---
    import brain.handlers.groups          # модерация, настройки групп

    from brain.router import get_registered_intents
    registered = get_registered_intents()
    logger.info(f"[Brain] Registered {len(registered)} handlers: {registered}")

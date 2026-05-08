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
    import bot.brain.handlers.system          # /start, /help, /settings

    # --- Профиль ---
    import bot.brain.handlers.profile         # просмотр и редактирование профиля

    # --- Экономика ---
    import bot.brain.handlers.economy         # баланс, бонус, перевод, рефералы

    # --- Питомец ---
    import bot.brain.handlers.pets            # все действия с питомцем (30 видов, XP, уровни)

    # --- Виртуальный мир ---
    import bot.brain.handlers.relationships   # отношения и браки
    import bot.brain.handlers.family          # семейные роли
    import bot.brain.handlers.actions         # действия между пользователями
    import bot.brain.handlers.events          # события

    # --- Казино ---
    import bot.brain.handlers.casino          # все игры казино

    # --- Мини-игры ---
    import bot.brain.handlers.games           # quiz, dice, truth/dare, etc.

    # --- Медиасервисы ---
    import bot.brain.handlers.media           # музыка, погода, перевод, энциклопедия, книги, аниме

    # --- AI-чат ---
    import bot.brain.handlers.ai_chat         # основной AI-диалог

    # --- Задачи ---
    import bot.brain.handlers.tasks           # todo и напоминания

    # --- Группы ---
    import bot.brain.handlers.groups          # модерация, настройки групп

    from bot.brain.router import get_registered_intents
    registered = get_registered_intents()
    logger.info(f"[Brain] Registered {len(registered)} handlers: {registered}")

"""
tests/test_brain_classifier.py — Тесты NLP-классификатора Brain.
"""

import pytest
from brain.classifier import classify_by_keywords
from brain.intent import Intent


class TestKeywordClassifier:
    """Тесты быстрой классификации по ключевым словам."""

    def test_start_command(self):
        assert classify_by_keywords("/start") == Intent.START

    def test_help_command(self):
        assert classify_by_keywords("/help") == Intent.HELP

    def test_balance_keyword(self):
        assert classify_by_keywords("мой баланс") == Intent.BALANCE
        assert classify_by_keywords("сколько монет") == Intent.BALANCE

    def test_daily_bonus(self):
        assert classify_by_keywords("ежедневный бонус") == Intent.DAILY_BONUS
        assert classify_by_keywords("/daily") == Intent.DAILY_BONUS

    def test_pet_status(self):
        assert classify_by_keywords("/pet") == Intent.PET_STATUS
        assert classify_by_keywords("мой питомец") == Intent.PET_STATUS

    def test_pet_feed(self):
        assert classify_by_keywords("покормить питомца") == Intent.PET_FEED
        assert classify_by_keywords("покорми") == Intent.PET_FEED

    def test_casino_open(self):
        assert classify_by_keywords("/casino") == Intent.CASINO_OPEN
        assert classify_by_keywords("казино") == Intent.CASINO_OPEN

    def test_casino_slots(self):
        assert classify_by_keywords("слоты") == Intent.CASINO_SLOTS
        assert classify_by_keywords("/slots") == Intent.CASINO_SLOTS

    def test_music_search(self):
        assert classify_by_keywords("найди музыку") == Intent.MUSIC_SEARCH
        assert classify_by_keywords("скачай песню") == Intent.MUSIC_SEARCH

    def test_weather(self):
        assert classify_by_keywords("погода") == Intent.WEATHER
        assert classify_by_keywords("/weather") == Intent.WEATHER

    def test_translate(self):
        assert classify_by_keywords("переведи привет") == Intent.TRANSLATE

    def test_encyclopedia(self):
        assert classify_by_keywords("что такое Python") == Intent.ENCYCLOPEDIA
        assert classify_by_keywords("кто такой Пушкин") == Intent.ENCYCLOPEDIA

    def test_task_create(self):
        assert classify_by_keywords("создать задачу") == Intent.TASK_CREATE
        assert classify_by_keywords("/todo") == Intent.TASK_CREATE

    def test_reminder(self):
        assert classify_by_keywords("напомни мне завтра") == Intent.REMINDER_CREATE

    def test_unknown_returns_none(self):
        assert classify_by_keywords("привет как дела") is None
        assert classify_by_keywords("расскажи мне что-нибудь") is None

    def test_group_warn(self):
        assert classify_by_keywords("/warn") == Intent.GROUP_WARN

    def test_profile_view(self):
        assert classify_by_keywords("/profile") == Intent.PROFILE_VIEW
        assert classify_by_keywords("мой профиль") == Intent.PROFILE_VIEW

    def test_relationship_propose(self):
        assert classify_by_keywords("будь моей") == Intent.RELATIONSHIP_PROPOSE
        assert classify_by_keywords("давай встречаться") == Intent.RELATIONSHIP_PROPOSE

    def test_marriage(self):
        assert classify_by_keywords("выйти замуж") == Intent.MARRIAGE_PROPOSE
        assert classify_by_keywords("жениться") == Intent.MARRIAGE_PROPOSE

    def test_case_insensitive(self):
        assert classify_by_keywords("КАЗИНО") == Intent.CASINO_OPEN
        assert classify_by_keywords("ПОГОДА") == Intent.WEATHER

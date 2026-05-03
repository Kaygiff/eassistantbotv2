"""
tests/test_i18n.py — Тесты i18n загрузчика.
"""

import pytest
from i18n.loader import t, SUPPORTED_LANGS, FALLBACK_LANG


class TestI18nLoader:

    def test_supported_languages(self):
        assert "ru" in SUPPORTED_LANGS
        assert "en" in SUPPORTED_LANGS
        assert "kz" in SUPPORTED_LANGS

    def test_fallback_is_ru(self):
        assert FALLBACK_LANG == "ru"

    def test_translate_known_key_ru(self):
        result = t("ru", "common.error")
        assert result
        assert "❌" in result

    def test_translate_known_key_en(self):
        result = t("en", "common.error")
        assert result
        assert "❌" in result

    def test_translate_with_format_args(self):
        result = t("ru", "economy.balance", balance=500)
        assert "500" in result

    def test_translate_unknown_key_returns_key(self):
        result = t("ru", "nonexistent.key")
        assert result == "[nonexistent.key]"

    def test_translate_unsupported_lang_falls_back(self):
        # Неизвестный язык должен вернуть ru
        result = t("zz", "common.error")
        assert result
        assert result != "[common.error]"

    def test_translate_daily_bonus_format(self):
        result = t("ru", "economy.daily_bonus", amount=200, streak=5)
        assert "200" in result
        assert "5" in result

    def test_translate_pets_status_format(self):
        result = t("ru", "pets.status",
                   name="Барсик", species="🐱 cat",
                   mood="😊", hunger=80, energy=90, level=2)
        assert "Барсик" in result
        assert "80" in result

    def test_all_supported_langs_have_common_error(self):
        for lang in SUPPORTED_LANGS:
            result = t(lang, "common.error")
            # Не должно быть "[common.error]" — либо перевод либо fallback
            assert result != "[common.error]", f"Missing translation for lang={lang}"

"""
scripts/check_env.py — Проверяет что все обязательные env-переменные заданы.
Запускай перед деплоем: python scripts/check_env.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

REQUIRED = [
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_WEBHOOK_URL",
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "SUPABASE_SERVICE_KEY",
    "DATABASE_URL",
    "REDIS_URL",
    "OPENAI_API_KEY",
    "EADMIN_SECRET_KEY",
]

OPTIONAL = [
    "MISTRAL_API_KEY",
    "DEEPSEEK_API_KEY",
    "GROQ_API_KEY",
    "COHERE_API_KEY",
    "PERPLEXITY_API_KEY",
    "QWEN_API_KEY",
    "YI_API_KEY",
    "ASSEMBLYAI_API_KEY",
    "STABILITY_API_KEY",
    "DEEPL_API_KEY",
    "OPENWEATHERMAP_API_KEY",
    "SENTRY_DSN",
]


def check():
    print("🔍 Проверка переменных окружения...\n")
    errors = []
    warnings = []

    for key in REQUIRED:
        val = os.getenv(key)
        if not val:
            errors.append(f"  ❌ {key} — ОТСУТСТВУЕТ (обязательная)")
        else:
            masked = val[:6] + "..." if len(val) > 6 else "***"
            print(f"  ✅ {key} = {masked}")

    print()

    for key in OPTIONAL:
        val = os.getenv(key)
        if not val:
            warnings.append(f"  ⚠️  {key} — не задана (опциональная)")
        else:
            masked = val[:6] + "..." if len(val) > 6 else "***"
            print(f"  ✅ {key} = {masked}")

    if warnings:
        print("\n" + "\n".join(warnings))

    if errors:
        print("\n" + "\n".join(errors))
        print(f"\n❌ Найдено {len(errors)} обязательных переменных без значений.")
        sys.exit(1)
    else:
        print(f"\n✅ Все обязательные переменные заданы. Готов к запуску!")


if __name__ == "__main__":
    check()

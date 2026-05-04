"""
Начальные данные для dev-окружения.
Создаёт тестового пользователя, пополняет кошелёк, добавляет quiz-вопросы.
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

import psycopg2
import psycopg2.extras

DATABASE_URL = os.getenv("DATABASE_URL")


def seed():
    if not DATABASE_URL:
        print("❌ DATABASE_URL не задан в .env")
        sys.exit(1)

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    print("🌱 Начинаем сидирование...")

    # --- Тестовый пользователь ---
    user_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO users (id, telegram_id, username, first_name, language, assistant_name)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (telegram_id) DO NOTHING
    """, (user_id, 123456789, "test_user", "Test", "ru", "Алекс"))
    print("  ✅ Тестовый пользователь создан (telegram_id=123456789)")

    # --- Кошелёк ---
    cur.execute("""
        INSERT INTO ecoin_wallets (user_id, balance)
        VALUES (%s, %s)
        ON CONFLICT (user_id) DO NOTHING
    """, (user_id, 1000))
    print("  ✅ Кошелёк: 1000 Ecoins")

    # --- Ежедневный бонус ---
    cur.execute("""
        INSERT INTO daily_bonuses (user_id, streak_days)
        VALUES (%s, 0)
        ON CONFLICT (user_id) DO NOTHING
    """, (user_id,))
    print("  ✅ daily_bonuses инициализирован")

    # --- Quiz вопросы (пример) ---
    questions = [
        {
            "question": "Какая планета самая большая в Солнечной системе?",
            "options": ["Земля", "Сатурн", "Юпитер", "Нептун"],
            "correct_index": 2,
            "category": "science",
            "difficulty": "easy",
            "language": "ru",
        },
        {
            "question": "Сколько цветов в радуге?",
            "options": ["5", "6", "7", "8"],
            "correct_index": 2,
            "category": "general",
            "difficulty": "easy",
            "language": "ru",
        },
        {
            "question": "Which planet is closest to the Sun?",
            "options": ["Venus", "Mercury", "Mars", "Earth"],
            "correct_index": 1,
            "category": "science",
            "difficulty": "easy",
            "language": "en",
        },
    ]

    import json
    for q in questions:
        cur.execute("""
            INSERT INTO quiz_questions (question, options, correct_index, category, difficulty, language)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            q["question"],
            json.dumps(q["options"], ensure_ascii=False),
            q["correct_index"],
            q["category"],
            q["difficulty"],
            q["language"],
        ))
    print(f"  ✅ {len(questions)} quiz-вопросов добавлено")

    cur.close()
    conn.close()
    print("\n✅ Сидирование завершено.")


if __name__ == "__main__":
    seed()

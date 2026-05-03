"""
Запуск SQL-миграций в Supabase.
Выполняет все файлы из db/migrations/ по порядку.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")
MIGRATIONS_DIR = Path(__file__).parent.parent / "db" / "migrations"


def run_migrations():
    if not DATABASE_URL:
        print("❌ DATABASE_URL не задан в .env")
        sys.exit(1)

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migration_files:
        print("⚠️  Миграции не найдены.")
        return

    for path in migration_files:
        print(f"▶ Применяю {path.name}...")
        try:
            sql = path.read_text(encoding="utf-8")
            cur.execute(sql)
            print(f"  ✅ {path.name} — OK")
        except Exception as e:
            print(f"  ❌ {path.name} — ОШИБКА: {e}")
            conn.close()
            sys.exit(1)

    cur.close()
    conn.close()
    print("\n✅ Все миграции применены.")


if __name__ == "__main__":
    run_migrations()

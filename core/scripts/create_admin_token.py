"""
scripts/create_admin_token.py — Генерирует JWT токен для доступа к EAdmin API.
Использование: python scripts/create_admin_token.py [admin_id]
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()


def main():
    admin_id = sys.argv[1] if len(sys.argv) > 1 else "admin"
    from api.auth import create_admin_token
    token = create_admin_token(admin_id)
    print(f"\n✅ JWT токен для EAdmin:\n")
    print(f"  {token}\n")
    print(f"Используй в заголовке: Authorization: Bearer {token[:30]}...")
    print(f"Токен бессрочный. Храни в безопасном месте.\n")


if __name__ == "__main__":
    main()

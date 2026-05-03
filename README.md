# E'assistant — AI Telegram Bot Platform

> Версия 1.1 · Финальная архитектура

AI-ассистент и развлекательная платформа на базе Telegram.

---

## Быстрый старт

```bash
# 1. Клонируй репозиторий
git clone https://github.com/your-org/eassistant.git
cd eassistant

# 2. Настрой окружение
cp .env.example .env
# Заполни .env реальными ключами

# 3. Запусти через Docker Compose (dev)
docker-compose up --build

# 4. Примени миграции (в Supabase SQL Editor или через скрипт)
python scripts/migrate.py
```

---

## Архитектура

```
eassistant/
├── bot/           # Telegram Webhook — точка входа
├── brain/         # NLP-роутер — центральный компонент
├── onboarding/    # FSM-диалог онбординга
├── auth/          # Авторизация и сессии
├── services/      # Микросервисы (AI, музыка, погода, и др.)
├── virtual_world/ # Социальный слой (отношения, питомцы, события)
├── casino/        # Казино на Ecoins
├── economy/       # Кошелёк, транзакции, бонусы, рефералы
├── ai_provider/   # AI Provider Hub с Circuit Breaker
├── queue/         # Celery + Redis
├── safety/        # Rate limit, бан, модерация контента
├── i18n/          # Локализация (RU, KZ, UZ, TJ, TM, KG, BY, EN)
├── db/            # Supabase + Redis клиенты + миграции
├── models/        # Pydantic модели
├── api/           # FastAPI REST API v1
├── eadmin/        # Админ-панель (Next.js PWA)
└── tests/         # Тесты
```

## Технологии

| Слой | Технология |
|------|-----------|
| Bot | aiogram 3 + Webhook |
| API | FastAPI + uvicorn |
| DB | Supabase (PostgreSQL) |
| Cache | Redis |
| Queue | Celery + Redis |
| AI | OpenAI GPT-4o + 7 резервных провайдеров |
| Deploy | Railway + Docker |
| Admin | Next.js PWA |

## Языки

RU · KZ · UZ · TJ · TM · KG · BY · EN

## Лицензия

Proprietary · E'assistant Team

# EAdmin — E'assistant Admin Panel

> Next.js 14 PWA · Dark theme · Bioluminescent fox 🦊

## Быстрый старт

```bash
cd eadmin
cp .env.local.example .env.local
# Заполни NEXT_PUBLIC_API_URL

npm install
npm run dev
# Открой http://localhost:3000
```

## .env.local

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Получить токен для входа

```bash
cd ..
python scripts/create_admin_token.py
```

Скопируй токен и вставь на странице /login.

## Страницы

| Путь | Описание |
|------|----------|
| `/dashboard` | Главный дашборд — статистика, языки, казино |
| `/users` | Таблица пользователей, поиск, бан/разбан |
| `/groups` | Список групп и их настройки |
| `/stats` | Графики роста и экономики |
| `/casino` | Статистика казино и раундов |
| `/flags` | Feature Flags — включение/выключение функций |
| `/brain` | Brain Editor — кастомные правила классификатора |
| `/broadcast` | Массовые рассылки по языкам |
| `/moderation` | Быстрый бан/разбан |
| `/settings` | Информация и ссылки |

## Сборка для production

```bash
npm run build
npm start
```

## Docker

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY . .
RUN npm ci && npm run build
CMD ["npm", "start"]
```

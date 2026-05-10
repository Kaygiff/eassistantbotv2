"""
api/app.py — Главное FastAPI приложение.
Подключает webhook, health check и REST API v1.
"""

from __future__ import annotations
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from infra.monitoring.metrics import init_sentry, init_logging
from infra.monitoring.health import get_health
from bot.webhook import webhook_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_logging()
    init_sentry()

    from bot.brain.dispatcher import register_all_handlers
    from bot.brain.editor import load_rules_into_classifier
    from infra.safety.content_moderation import load_stopwords

    register_all_handlers()
    await load_rules_into_classifier()
    await load_stopwords()

    yield


app = FastAPI(
    title="E'assistant API",
    version="1.1.0",
    docs_url="/docs" if os.getenv("APP_ENV") != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)

EADMIN_URL = os.getenv("EADMIN_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[EADMIN_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router)

# ── Статические файлы (guide.html и т.д.) ──────────────────────────────────
_STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.isdir(_STATIC_DIR):
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.get("/guide", include_in_schema=False)
async def guide():
    """Открывает страницу руководства пользователя (используется в Mini App Telegram)."""
    path = os.path.join(_STATIC_DIR, "guide.html")
    return FileResponse(path, media_type="text/html")


from api.routes import users, admin, stats, flags, brain_editor, notifications, groups, casino
app.include_router(users.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")
app.include_router(flags.router, prefix="/api/v1")
app.include_router(brain_editor.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(groups.router, prefix="/api/v1")
app.include_router(casino.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return await get_health()


@app.get("/")
async def root():
    return {"service": "E'assistant API", "version": "1.1.0"}

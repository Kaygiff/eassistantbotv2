"""
Supabase / PostgreSQL клиент.
Используется во всех сервисах для работы с основным хранилищем.
"""

import os
from functools import lru_cache
from supabase import create_client, Client
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str
    supabase_service_key: str

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


@lru_cache()
def get_supabase_client() -> Client:
    """Anon client — для операций от имени пользователя (Row Level Security)."""
    s = get_settings()
    return create_client(s.supabase_url, s.supabase_key)


@lru_cache()
def get_supabase_admin() -> Client:
    """Service role client — для admin-операций, обходит RLS."""
    s = get_settings()
    return create_client(s.supabase_url, s.supabase_service_key)


# Удобные алиасы
supabase: Client = get_supabase_client()
supabase_admin: Client = get_supabase_admin()

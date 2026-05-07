-- ==============================================================================
-- 011_music_cache.sql — Дополнительный индекс для music_cache
-- Таблица уже создана в 006_chat_media.sql
-- ==============================================================================

-- Индекс для поиска по названию (ILIKE запросы)
CREATE INDEX IF NOT EXISTS idx_music_cache_title ON music_cache (title);
CREATE INDEX IF NOT EXISTS idx_music_cache_artist ON music_cache (artist);

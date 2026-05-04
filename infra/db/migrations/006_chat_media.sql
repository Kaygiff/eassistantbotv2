-- ==============================================================================
-- 006_chat_media.sql — История чата и кэш музыки
-- ==============================================================================

CREATE TABLE IF NOT EXISTS chat_messages (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role        VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content     TEXT NOT NULL,
    model_used  VARCHAR(50),
    tokens_used INTEGER,
    response_ms INTEGER,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Основной индекс для выборки истории по пользователю (последние N сообщений)
CREATE INDEX idx_chat_messages_user_time ON chat_messages(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS music_cache (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    youtube_id  VARCHAR(20) UNIQUE NOT NULL,
    title       VARCHAR(255),
    artist      VARCHAR(255),
    storage_url TEXT NOT NULL,      -- CDN URL mp3 файла
    lyrics_url  TEXT,               -- URL текста песни (если есть)
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_music_youtube_id ON music_cache(youtube_id);

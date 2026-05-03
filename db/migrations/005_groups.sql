-- ==============================================================================
-- 005_groups.sql — Групповое пространство
-- ==============================================================================

CREATE TABLE IF NOT EXISTS groups (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id         BIGINT UNIQUE NOT NULL,   -- Telegram chat_id
    title           VARCHAR(255) NOT NULL,
    owner_id        UUID REFERENCES users(id) ON DELETE SET NULL,
    language        VARCHAR(5) NOT NULL DEFAULT 'ru',
    welcome_message TEXT,
    warn_threshold  INTEGER NOT NULL DEFAULT 3,
    bot_name        VARCHAR(100),              -- White-label: кастомное имя бота
    bot_avatar_url  TEXT,                      -- White-label: кастомный аватар
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_groups_chat_id  ON groups(chat_id);
CREATE INDEX idx_groups_owner_id ON groups(owner_id);

CREATE TABLE IF NOT EXISTS group_members (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id  UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role      VARCHAR(20) NOT NULL DEFAULT 'user'
              CHECK (role IN ('owner','co_owner','admin','moderator','user')),
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_group_member UNIQUE (group_id, user_id)
);

CREATE INDEX idx_group_members_group ON group_members(group_id);
CREATE INDEX idx_group_members_user  ON group_members(user_id);

CREATE TABLE IF NOT EXISTS group_warns (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id    UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    issued_by   UUID REFERENCES users(id) ON DELETE SET NULL,
    reason      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_warns_group_user ON group_warns(group_id, user_id);

-- ==============================================================================
-- 012_group_moderation.sql — Групповые баны и муты
-- ==============================================================================

CREATE TABLE IF NOT EXISTS group_bans (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id    UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    banned_by   UUID REFERENCES users(id) ON DELETE SET NULL,
    reason      TEXT,
    ban_until   TIMESTAMPTZ,          -- NULL = постоянный бан
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_group_ban UNIQUE (group_id, user_id)
);

CREATE INDEX idx_group_bans_group_user ON group_bans(group_id, user_id);

CREATE TABLE IF NOT EXISTS group_mutes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id    UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    muted_by    UUID REFERENCES users(id) ON DELETE SET NULL,
    reason      TEXT,
    mute_until  TIMESTAMPTZ NOT NULL, -- мут всегда временный
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_group_mute UNIQUE (group_id, user_id)
);

CREATE INDEX idx_group_mutes_group_user ON group_mutes(group_id, user_id);

-- Добавляем VIP в роли если ещё не добавлен
ALTER TABLE group_members
    DROP CONSTRAINT IF EXISTS group_members_role_check;

ALTER TABLE group_members
    ADD CONSTRAINT group_members_role_check
    CHECK (role IN ('owner', 'co_owner', 'admin', 'moderator', 'vip', 'user'));

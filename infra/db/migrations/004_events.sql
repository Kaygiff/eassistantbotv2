-- ==============================================================================
-- 004_events.sql — События (пользовательские + системные авто-события)
-- ==============================================================================

CREATE TABLE IF NOT EXISTS events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    creator_id  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    chat_id     BIGINT NOT NULL,   -- Telegram group chat_id
    title       VARCHAR(100) NOT NULL,
    description TEXT,
    event_at    TIMESTAMPTZ NOT NULL,
    type        VARCHAR(20) NOT NULL DEFAULT 'open' CHECK (type IN ('open', 'invite')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_events_creator  ON events(creator_id);
CREATE INDEX idx_events_chat_id  ON events(chat_id);
CREATE INDEX idx_events_event_at ON events(event_at);

CREATE TABLE IF NOT EXISTS event_participants (
    event_id   UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status     VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('accepted', 'declined', 'pending')),
    joined_at  TIMESTAMPTZ,
    PRIMARY KEY (event_id, user_id)
);

CREATE INDEX idx_event_participants_user ON event_participants(user_id);

-- ==============================================================================
-- 007_games.sql — Мини-игры и казино
-- ==============================================================================

-- Сессии мини-игр (не казино)
CREATE TABLE IF NOT EXISTS game_sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    opponent_id UUID REFERENCES users(id) ON DELETE SET NULL,
    game_type   VARCHAR(50) NOT NULL,
    mode        VARCHAR(20) NOT NULL DEFAULT 'solo' CHECK (mode IN ('solo', 'multiplayer')),
    status      VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'finished', 'abandoned')),
    result      VARCHAR(20) CHECK (result IN ('win', 'loss', 'draw')),
    score       JSONB,
    room_code   VARCHAR(16),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ
);

CREATE INDEX idx_game_sessions_user   ON game_sessions(user_id);
CREATE INDEX idx_game_sessions_room   ON game_sessions(room_code);

-- Таблица лидеров
CREATE TABLE IF NOT EXISTS game_leaderboard (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    game_type   VARCHAR(50) NOT NULL,
    wins        INTEGER NOT NULL DEFAULT 0,
    losses      INTEGER NOT NULL DEFAULT 0,
    draws       INTEGER NOT NULL DEFAULT 0,
    best_score  INTEGER NOT NULL DEFAULT 0,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_leaderboard UNIQUE (user_id, game_type)
);

CREATE INDEX idx_leaderboard_game ON game_leaderboard(game_type, wins DESC);

-- Вопросы для викторин
CREATE TABLE IF NOT EXISTS quiz_questions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question      TEXT NOT NULL,
    options       JSONB NOT NULL,    -- ["вариант A", "вариант B", ...]
    correct_index INTEGER NOT NULL,
    category      VARCHAR(50),
    difficulty    VARCHAR(10) CHECK (difficulty IN ('easy', 'medium', 'hard')),
    language      VARCHAR(5) NOT NULL DEFAULT 'ru'
);

CREATE INDEX idx_quiz_lang_cat ON quiz_questions(language, category);

-- Раунды казино (отдельно от мини-игр)
CREATE TABLE IF NOT EXISTS casino_rounds (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    opponent_id UUID REFERENCES users(id) ON DELETE SET NULL,  -- для мультиплеера
    game_type   VARCHAR(30) NOT NULL,   -- slots, roulette, blackjack, crash, poker, etc.
    mode        VARCHAR(20) NOT NULL DEFAULT 'solo' CHECK (mode IN ('solo', 'multiplayer')),
    amount      BIGINT NOT NULL CHECK (amount > 0),    -- ставка
    payout      BIGINT NOT NULL DEFAULT 0,             -- выплата
    house_fee   BIGINT NOT NULL DEFAULT 0,             -- комиссия казино
    result      JSONB,                                 -- детали раунда
    outcome     VARCHAR(10) CHECK (outcome IN ('win', 'loss', 'push')),
    seed_hash   VARCHAR(64),                           -- Provably Fair (для Crash)
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_casino_user_id    ON casino_rounds(user_id);
CREATE INDEX idx_casino_created_at ON casino_rounds(created_at DESC);
CREATE INDEX idx_casino_game_type  ON casino_rounds(game_type);

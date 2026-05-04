-- ==============================================================================
-- 003_pets_actions.sql — Питомцы-тамагочи и действия между пользователями
-- ==============================================================================

-- Питомцы (один активный на пользователя)
CREATE TABLE IF NOT EXISTS pets (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name                VARCHAR(50) NOT NULL,
    species             VARCHAR(20) NOT NULL CHECK (species IN ('cat','dog','rabbit','hamster','fox','dragon')),
    level               INTEGER NOT NULL DEFAULT 1,
    mood                VARCHAR(20) NOT NULL DEFAULT 'happy' CHECK (mood IN ('happy','neutral','sad','sick')),
    hunger              INTEGER NOT NULL DEFAULT 100 CHECK (hunger BETWEEN 0 AND 100),
    energy              INTEGER NOT NULL DEFAULT 100 CHECK (energy BETWEEN 0 AND 100),
    is_sick             BOOLEAN NOT NULL DEFAULT false,
    is_dead             BOOLEAN NOT NULL DEFAULT false,
    born_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_interaction_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_pets_user_id  ON pets(user_id);
CREATE INDEX idx_pets_is_dead  ON pets(is_dead);
CREATE INDEX idx_pets_is_sick  ON pets(is_sick);

-- Лог действий между пользователями
CREATE TABLE IF NOT EXISTS actions_log (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    initiator_id  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action_type   VARCHAR(50) NOT NULL,
    category      VARCHAR(20) NOT NULL CHECK (category IN ('emotional','friendly','aggressive','nsfw','profane','gift')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Индекс для cooldown-проверки: одно действие на пару за 5 минут
CREATE INDEX idx_actions_cooldown ON actions_log(initiator_id, target_id, action_type, created_at DESC);
CREATE INDEX idx_actions_created  ON actions_log(created_at DESC);

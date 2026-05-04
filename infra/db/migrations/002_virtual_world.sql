-- ==============================================================================
-- 002_virtual_world.sql — Отношения, браки, семейные роли, blacklist, профили
-- ==============================================================================

-- Профиль виртуального мира (1:1 к users)
CREATE TABLE IF NOT EXISTS virtual_world_profiles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    nickname    VARCHAR(50),
    status      VARCHAR(100),
    bio         TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Отношения (dating / married)
-- user_a_id < user_b_id — гарантирует уникальность пары без дублей
CREATE TABLE IF NOT EXISTS relationships (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_a_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_b_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status      VARCHAR(20) NOT NULL CHECK (status IN ('dating', 'married')),
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    married_at  TIMESTAMPTZ,   -- NULL при status = 'dating'
    CONSTRAINT chk_user_order CHECK (user_a_id < user_b_id),
    CONSTRAINT uq_relationship UNIQUE (user_a_id, user_b_id)
);

CREATE INDEX idx_relationships_user_a ON relationships(user_a_id);
CREATE INDEX idx_relationships_user_b ON relationships(user_b_id);

-- Семейные роли
CREATE TABLE IF NOT EXISTS family_relations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    initiator_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    initiator_role  VARCHAR(30) NOT NULL,  -- parent, sibling, grandparent, uncle, etc.
    target_role     VARCHAR(30) NOT NULL,  -- зеркальная роль
    status          VARCHAR(10) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_family_pair UNIQUE (initiator_id, target_id)
);

CREATE INDEX idx_family_initiator ON family_relations(initiator_id);
CREATE INDEX idx_family_target    ON family_relations(target_id);
CREATE INDEX idx_family_status    ON family_relations(status);

-- Черный список (односторонний)
CREATE TABLE IF NOT EXISTS blacklist (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    blocker_id  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    blocked_id  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_blacklist UNIQUE (blocker_id, blocked_id),
    CONSTRAINT chk_no_self_block CHECK (blocker_id != blocked_id)
);

CREATE INDEX idx_blacklist_blocker ON blacklist(blocker_id);
CREATE INDEX idx_blacklist_blocked ON blacklist(blocked_id);

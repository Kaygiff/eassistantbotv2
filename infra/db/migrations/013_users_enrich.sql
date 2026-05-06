-- ==============================================================================
-- 013_users_enrich.sql — Расширение таблицы users полезными полями
-- ==============================================================================

-- last_name: фамилия из Telegram профиля
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_name VARCHAR(128);

-- is_premium: Telegram Premium подписка
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_premium BOOLEAN NOT NULL DEFAULT false;

-- last_seen_at: время последней активности (обновляется при каждом сообщении)
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now();

-- messages_count: счётчик сообщений пользователя (для статистики/ранга)
ALTER TABLE users ADD COLUMN IF NOT EXISTS messages_count BIGINT NOT NULL DEFAULT 0;

-- xp: очки опыта (для уровневой системы)
ALTER TABLE users ADD COLUMN IF NOT EXISTS xp BIGINT NOT NULL DEFAULT 0;

-- level: текущий уровень пользователя
ALTER TABLE users ADD COLUMN IF NOT EXISTS level INTEGER NOT NULL DEFAULT 1;

-- rep: репутация (плюсики/минусики от других пользователей)
ALTER TABLE users ADD COLUMN IF NOT EXISTS rep INTEGER NOT NULL DEFAULT 0;

-- is_admin: флаг глобального администратора бота
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT false;

-- referral_code: уникальный код для приглашения (генерируется при регистрации)
ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_code VARCHAR(16) UNIQUE;

-- locale: полная локаль пользователя (например ru_RU, en_US)
ALTER TABLE users ADD COLUMN IF NOT EXISTS locale VARCHAR(10);

-- Индексы для новых полей
CREATE INDEX IF NOT EXISTS idx_users_last_seen   ON users(last_seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_users_level        ON users(level DESC);
CREATE INDEX IF NOT EXISTS idx_users_xp           ON users(xp DESC);
CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code);
CREATE INDEX IF NOT EXISTS idx_users_is_admin      ON users(is_admin) WHERE is_admin = true;

-- Функция генерации реферального кода при INSERT если не задан
CREATE OR REPLACE FUNCTION generate_referral_code()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.referral_code IS NULL THEN
        NEW.referral_code := upper(substring(replace(gen_random_uuid()::text, '-', ''), 1, 8));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_referral_code ON users;
CREATE TRIGGER trg_users_referral_code
    BEFORE INSERT ON users
    FOR EACH ROW EXECUTE FUNCTION generate_referral_code();

-- Заполнить referral_code для уже существующих пользователей
UPDATE users
SET referral_code = upper(substring(replace(gen_random_uuid()::text, '-', ''), 1, 8))
WHERE referral_code IS NULL;

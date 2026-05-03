-- ==============================================================================
-- 001_users.sql — Пользователи, кошельки, бонусы, рефералы
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Основной профиль пользователя
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id     BIGINT UNIQUE NOT NULL,
    username        VARCHAR(64),
    first_name      VARCHAR(128),
    language        VARCHAR(5) NOT NULL DEFAULT 'ru',   -- ru|kz|uz|tj|tm|kg|by|en
    assistant_name  VARCHAR(50) NOT NULL DEFAULT 'Ассистент',
    nickname        VARCHAR(50),
    bio             TEXT,
    avatar_url      TEXT,
    birthday        DATE,
    timezone        VARCHAR(50) DEFAULT 'UTC',
    is_banned       BOOLEAN NOT NULL DEFAULT false,
    ban_until       TIMESTAMPTZ,
    ban_reason      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_language    ON users(language);
CREATE INDEX idx_users_created_at  ON users(created_at DESC);

-- Кошелёк (1:1 к users)
CREATE TABLE IF NOT EXISTS ecoin_wallets (
    user_id     UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    balance     BIGINT NOT NULL DEFAULT 0 CHECK (balance >= 0),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Ежедневные бонусы (1:1 к users)
CREATE TABLE IF NOT EXISTS daily_bonuses (
    user_id              UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    streak_days          INTEGER NOT NULL DEFAULT 0,
    last_bonus_at        TIMESTAMPTZ,
    total_bonuses_earned BIGINT NOT NULL DEFAULT 0
);

-- Реферальная система
CREATE TABLE IF NOT EXISTS referrals (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_id            UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    referee_id             UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ref_code               VARCHAR(32) NOT NULL,
    bonus_paid             BOOLEAN NOT NULL DEFAULT false,
    total_commission_earned BIGINT NOT NULL DEFAULT 0,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_referrals_referrer ON referrals(referrer_id);
CREATE INDEX idx_referrals_ref_code ON referrals(ref_code);

-- Audit Log (авторизации, транзакции, действия админов, IP)
CREATE TABLE IF NOT EXISTS audit_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE SET NULL,
    action      VARCHAR(100) NOT NULL,
    details     JSONB,
    ip_address  INET,
    geo         VARCHAR(100),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_user_id    ON audit_log(user_id);
CREATE INDEX idx_audit_created_at ON audit_log(created_at DESC);

-- Автоудаление audit_log старше 90 дней (через pg_cron или триггер)
-- В production рекомендуется настроить через Supabase scheduled functions

-- Обновление updated_at автоматически
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_wallets_updated_at
    BEFORE UPDATE ON ecoin_wallets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

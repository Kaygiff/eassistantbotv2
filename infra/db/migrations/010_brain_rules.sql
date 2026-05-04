-- ==============================================================================
-- 010_brain_rules.sql — Кастомные правила Brain Editor
-- Редактируются через EAdmin без перезапуска сервиса
-- ==============================================================================

CREATE TABLE IF NOT EXISTS brain_rules (
    intent      VARCHAR(50) PRIMARY KEY,
    keywords    JSONB NOT NULL DEFAULT '[]',   -- массив строк-ключевых слов
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_brain_rules_updated_at
    BEFORE UPDATE ON brain_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Таблица для Feature Flags (нужна для feature_flags/flags.py)
CREATE TABLE IF NOT EXISTS feature_flags (
    name        VARCHAR(100) PRIMARY KEY,
    enabled     BOOLEAN NOT NULL DEFAULT true,
    description TEXT,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Таблица для пользовательских Feature Flags (A/B тесты)
CREATE TABLE IF NOT EXISTS feature_flag_users (
    flag_name   VARCHAR(100) NOT NULL,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    enabled     BOOLEAN NOT NULL DEFAULT true,
    PRIMARY KEY (flag_name, user_id)
);

-- Таблица стоп-слов для content_moderation.py
CREATE TABLE IF NOT EXISTS stopwords (
    id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    word    VARCHAR(100) UNIQUE NOT NULL,
    lang    VARCHAR(5) DEFAULT NULL   -- NULL = для всех языков
);

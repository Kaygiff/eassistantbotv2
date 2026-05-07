-- ==============================================================================
-- 008_economy.sql — Транзакции Ecoins
-- ==============================================================================

CREATE TABLE IF NOT EXISTS ecoin_transactions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type          VARCHAR(10) NOT NULL CHECK (type IN ('credit', 'debit')),
    amount        BIGINT NOT NULL CHECK (amount > 0),
    balance_after BIGINT NOT NULL CHECK (balance_after >= 0),
    reason        VARCHAR(40) NOT NULL CHECK (reason IN (
                    'daily_bonus', 'referral_signup', 'referral_commission',
                    'game_win', 'casino_bet', 'transfer_in', 'transfer_out',
                    'pet_heal', 'admin'
                  )),
    related_id    UUID,   -- Ссылка на связанный объект (nullable)
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_ecoin_tx_user_id    ON ecoin_transactions(user_id, created_at DESC);
CREATE INDEX idx_ecoin_tx_reason     ON ecoin_transactions(reason);
CREATE INDEX idx_ecoin_tx_created_at ON ecoin_transactions(created_at DESC);

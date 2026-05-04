-- ==============================================================================
-- 009_tasks.sql — Задачи и напоминания (объединённая таблица)
-- ==============================================================================

CREATE TABLE IF NOT EXISTS tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    group_id        UUID REFERENCES groups(id) ON DELETE CASCADE,   -- NULL для личных задач
    type            VARCHAR(10) NOT NULL CHECK (type IN ('todo', 'reminder')),
    title           TEXT NOT NULL,
    priority        VARCHAR(10) NOT NULL DEFAULT 'medium'
                    CHECK (priority IN ('high', 'medium', 'low')),
    due_at          TIMESTAMPTZ,   -- для todo: дедлайн; для reminder: время срабатывания
    repeat_rule     VARCHAR(20) CHECK (repeat_rule IN ('once', 'daily', 'weekly', 'monthly')),
    status          VARCHAR(10) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'done')),
    reminder_sent   BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_tasks_user_id    ON tasks(user_id, status);
CREATE INDEX idx_tasks_group_id   ON tasks(group_id);
CREATE INDEX idx_tasks_due_at     ON tasks(due_at) WHERE status = 'pending';
CREATE INDEX idx_tasks_reminder   ON tasks(due_at) WHERE type = 'reminder' AND reminder_sent = false;

CREATE TRIGGER trg_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

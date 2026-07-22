-- ============================================================
-- Fitness Discord Bot — PostgreSQL Schema
-- Single-user, single-channel. 9 tables.
-- ============================================================

-- ------------------------------------------------------------
-- 1. conversation_context
-- Rolling window of turns for the Context Loader (last 10 turns).
-- ------------------------------------------------------------
CREATE TABLE conversation_context (
    id          BIGSERIAL PRIMARY KEY,
    role        TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content     TEXT NOT NULL,
    intent      TEXT,                      -- ClassifiedIntent, nullable (assistant turns won't have one)
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_conversation_context_recent
    ON conversation_context (created_at DESC);


-- ------------------------------------------------------------
-- 2. meals
-- One row per meal instance per day. Also captures skipped meals
-- via status, so "I skipped dinner" doesn't need a separate table.
-- ------------------------------------------------------------
CREATE TABLE meals (
    id          BIGSERIAL PRIMARY KEY,
    meal_date   DATE NOT NULL,
    meal_type   TEXT NOT NULL CHECK (meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')),
    status      TEXT NOT NULL DEFAULT 'logged' CHECK (status IN ('logged', 'skipped')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_meals_date ON meals (meal_date);
-- One meal_type per day per status keeps "add 2 eggs" / "actually I had 4 eggs"
-- unambiguous — there's exactly one active lunch row to update.
CREATE UNIQUE INDEX uq_meals_date_type_logged
    ON meals (meal_date, meal_type)
    WHERE status = 'logged';


-- ------------------------------------------------------------
-- 3. food_items
-- Individual food entries within a meal. Nutrition is 100% LLM-estimated,
-- no nutrition DB. Low-confidence items get flagged for clarification
-- instead of guessing.
-- ------------------------------------------------------------
CREATE TABLE food_items (
    id                  BIGSERIAL PRIMARY KEY,
    meal_id             BIGINT NOT NULL REFERENCES meals(id) ON DELETE CASCADE,
    food_name           TEXT NOT NULL,
    quantity_desc        TEXT NOT NULL,        -- raw text as user said it, e.g. "200g", "3", "a bowl"
    quantity_grams       NUMERIC(7,2),          -- nullable until resolved
    confidence          TEXT NOT NULL CHECK (confidence IN ('high', 'low')),
    needs_clarification BOOLEAN NOT NULL DEFAULT FALSE,
    calories            NUMERIC(7,2),
    protein_g           NUMERIC(6,2),
    carbs_g             NUMERIC(6,2),
    fat_g               NUMERIC(6,2),
    fiber_g             NUMERIC(6,2),
    micronutrients      JSONB,                 -- e.g. {"iron_mg": 2.1, "vitamin_c_mg": 8}
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_food_items_meal ON food_items (meal_id);
CREATE INDEX idx_food_items_pending_clarification
    ON food_items (needs_clarification) WHERE needs_clarification = TRUE;


-- ------------------------------------------------------------
-- 4. muscle_groups
-- Master list. is_active + sort_order make it easy to extend later
-- without breaking historical workout data.
-- ------------------------------------------------------------
CREATE TABLE muscle_groups (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order  SMALLINT NOT NULL DEFAULT 0
);

INSERT INTO muscle_groups (name, sort_order) VALUES
    ('Chest', 1), ('Back', 2), ('Shoulders', 3),
    ('Biceps', 4), ('Triceps', 5), ('Legs', 6);


-- ------------------------------------------------------------
-- 5. workouts
-- One row per day. is_rest_day folds "rest day" logging in here
-- instead of a separate table.
-- ------------------------------------------------------------
CREATE TABLE workouts (
    id            BIGSERIAL PRIMARY KEY,
    workout_date  DATE NOT NULL UNIQUE,
    is_rest_day   BOOLEAN NOT NULL DEFAULT FALSE,
    notes         TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_workouts_date ON workouts (workout_date);


-- ------------------------------------------------------------
-- 6. workout_muscle_groups
-- Join table. "Push day" expands into 3 rows (chest/shoulders/triceps)
-- against one workout row.
-- ------------------------------------------------------------
CREATE TABLE workout_muscle_groups (
    id                BIGSERIAL PRIMARY KEY,
    workout_id        BIGINT NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
    muscle_group_id   INT NOT NULL REFERENCES muscle_groups(id),
    UNIQUE (workout_id, muscle_group_id)
);

CREATE INDEX idx_wmg_muscle_group ON workout_muscle_groups (muscle_group_id);


-- ------------------------------------------------------------
-- 7. goal_types
-- Lookup table for tracked metrics. Adding a new metric (e.g. sugar,
-- sodium) later is a row insert, not a schema change.
-- ------------------------------------------------------------
CREATE TABLE goal_types (
    id      SERIAL PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE,     -- 'calories', 'protein', 'carbs', 'fat', 'fiber'
    unit    TEXT NOT NULL             -- 'kcal', 'g'
);

INSERT INTO goal_types (name, unit) VALUES
    ('calories', 'kcal'), ('protein', 'g'), ('carbs', 'g'),
    ('fat', 'g'), ('fiber', 'g');


-- ------------------------------------------------------------
-- 8. goals
-- Versioned via effective_from — never overwritten, so historical
-- queries ("what was my protein target 2 weeks ago") stay correct.
-- Current value = MAX(effective_from) <= target date, per goal_type.
-- ------------------------------------------------------------
CREATE TABLE goals (
    id              BIGSERIAL PRIMARY KEY,
    goal_type_id    INT NOT NULL REFERENCES goal_types(id),
    target_value    NUMERIC(7,2) NOT NULL,
    effective_from  DATE NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_goals_type_effective
    ON goals (goal_type_id, effective_from DESC);


-- ------------------------------------------------------------
-- 9. notifications_log
-- Record of what the Notification Agent has sent, so the scheduler
-- doesn't duplicate alerts and you have an audit trail.
-- ------------------------------------------------------------
CREATE TABLE notifications_log (
    id                  BIGSERIAL PRIMARY KEY,
    notification_type   TEXT NOT NULL,      -- 'missed_macro', 'meal_reminder', 'workout_reminder', etc.
    related_date        DATE NOT NULL,      -- the day the notification is about
    message             TEXT NOT NULL,
    sent_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_notifications_date_type
    ON notifications_log (related_date, notification_type);


-- ============================================================
-- Helper view: current active goal per type (handles the
-- "effective_from" versioning so app code doesn't repeat this logic)
-- ============================================================
CREATE VIEW current_goals AS
SELECT DISTINCT ON (g.goal_type_id)
    gt.name AS goal_name,
    gt.unit,
    g.target_value,
    g.effective_from
FROM goals g
JOIN goal_types gt ON gt.id = g.goal_type_id
WHERE g.effective_from <= CURRENT_DATE
ORDER BY g.goal_type_id, g.effective_from DESC;

# Fitness Discord Bot

Single-user, single-channel Discord bot. Natural language only, no slash
commands. LLM classifies intent → routes to a tool agent (nutrient
estimator, SQL generator, workout logger) → composes a reply. Separate
APScheduler path sends proactive notifications (missed macros, reminders).

Stack: Python, Discord.py, Azure OpenAI, PostgreSQL (asyncpg).

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in real values
python -m scripts.init_db
python -m scripts.seed_goals      # edit TARGETS in the script first
python -m scripts.check_connection
```

## Build order

Build bottom-up. Each phase should be independently testable before
moving to the next — don't wire the Discord round-trip until the piece
underneath it is already proven to work standalone.

- **Phase 0 (done)** — config, db pool, schema, seed script. Verify with
  `scripts/check_connection.py`.
- **Phase 1** — `bot/client.py` + `bot/main.py`: dumb Discord echo bot,
  filtered to `DISCORD_CHANNEL_ID`. Proves Discord plumbing works.
- **Phase 2** — `bot/context/loader.py`: write every message to
  `conversation_context`, fetch last `context_window_turns` (10) turns.
- **Phase 3** — `bot/agents/classifier.py` +
  `bot/agents/prompts/classifier_prompt.txt`: context + message →
  `ClassifiedIntent`. Test standalone against the query catalog before
  wiring into the bot.
- **Phase 4** — `bot/agents/router.py` + `bot/agents/nutrient_estimator.py`
  + `bot/db/queries.py`: food logging end-to-end. Cover both the
  high-confidence path (auto-log) and low-confidence path (ask for
  clarification instead of logging).
- **Phase 5** — `bot/validation/sql_schema.py` +
  `bot/agents/sql_generator.py`: schema + request → parameterized SQL,
  Pydantic-validated, retry-on-failure loop. This is the highest-risk
  piece — test extensively against the query catalog before wiring into
  the router.
- **Phase 6** — `bot/agents/response_composer.py`: wire full round-trip
  reply back through `client.py`.
- **Phase 7** — `bot/notifications/scheduler.py` +
  `bot/notifications/notification_agent.py`: 3 daily IST checks, reads
  DB, sends alerts. Test by calling the job function manually before
  relying on the schedule.

## Design notes

- `bot/config.py` is the single source of truth for env/settings —
  don't read `os.environ` elsewhere.
- `bot/db/models.py` grows one phase at a time; don't pre-build models
  for tables you haven't wired up yet.
- Muscle groups master list: Chest, Back, Shoulders, Biceps, Triceps,
  Legs — stored in `muscle_groups` table (extensible) and mirrored in
  `Settings.muscle_groups` for quick reference.
- Goals are versioned via `effective_from`, never overwritten. Query the
  `current_goals` view instead of re-deriving "latest goal" logic.
- SQL generator must only ever produce parameterized queries — never
  interpolate user input directly.

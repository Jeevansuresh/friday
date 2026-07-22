"""
One-off script: inserts your starting goal targets into `goals`.
Edit the TARGETS dict below with your real numbers before running.

Usage:
    python -m scripts.seed_goals
"""
import asyncio
from datetime import date

import asyncpg

from friday.config import get_settings

# Edit these before running.
TARGETS = {
    "calories": 2200,
    "protein": 150,
    "carbs": 220,
    "fat": 70,
    "fiber": 30,
}

EFFECTIVE_FROM = date.today()


async def main() -> None:
    settings = get_settings()
    conn = await asyncpg.connect(dsn=settings.database_url)
    try:
        for goal_name, target_value in TARGETS.items():
            goal_type_id = await conn.fetchval(
                "SELECT id FROM goal_types WHERE name = $1", goal_name
            )
            if goal_type_id is None:
                print(f"Skipping unknown goal type: {goal_name}")
                continue

            await conn.execute(
                """
                INSERT INTO goals (goal_type_id, target_value, effective_from)
                VALUES ($1, $2, $3)
                """,
                goal_type_id,
                target_value,
                EFFECTIVE_FROM,
            )
            print(f"Seeded {goal_name} = {target_value} from {EFFECTIVE_FROM}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

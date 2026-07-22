"""
Phase 0 sanity check: confirms the pool connects and current_goals
returns your seeded data. Run this after init_db.py + seed_goals.py.

Usage:
    python -m scripts.check_connection
"""
import asyncio

from friday.db.pool import close_pool, init_pool


async def main() -> None:
    pool = await init_pool()
    try:
        rows = await pool.fetch("SELECT * FROM current_goals ORDER BY goal_name")
        if not rows:
            print("Connected, but current_goals is empty — did you run seed_goals.py?")
            return

        print("Connected. Current goals:")
        for row in rows:
            print(f"  {row['goal_name']}: {row['target_value']} {row['unit']}")
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())

"""
One-off script: applies schema.sql to the database pointed at by
DATABASE_URL. Run manually, not part of the bot's runtime.

Usage:
    python -m scripts.init_db
"""
import asyncio
from pathlib import Path

import asyncpg

from friday.config import get_settings

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.sql"


async def main() -> None:
    settings = get_settings()
    schema_sql = SCHEMA_PATH.read_text()

    conn = await asyncpg.connect(dsn=settings.database_url)
    try:
        # schema.sql has multiple statements separated by ';' — asyncpg's
        # execute() can run a whole script in one call.
        await conn.execute(schema_sql)
        print(f"Schema applied successfully from {SCHEMA_PATH}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

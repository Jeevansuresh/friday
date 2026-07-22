"""
Single asyncpg pool for the whole bot. main.py creates it once at startup
and passes it down (or modules import get_pool() after init() has run) —
either works for a single-process bot this size; init()/get_pool() is used
here so agents/notifications can grab it without threading it through
every function signature.
"""
import asyncpg

from friday.config import get_settings

_pool: asyncpg.Pool | None = None


async def init_pool() -> asyncpg.Pool:
    global _pool
    if _pool is not None:
        return _pool

    settings = get_settings()
    _pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=1,
        max_size=5,
    )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError(
            "Pool not initialized. Call init_pool() during startup before "
            "any code tries to use get_pool()."
        )
    return _pool

from typing import Optional

import asyncpg

from app.models.settings import settings
from app.utils.logging import get_logger


logger = get_logger(__name__)
_pool: Optional[asyncpg.Pool] = None


async def init_db() -> None:
    global _pool
    _pool = await asyncpg.create_pool(dsn=settings.db_dsn, min_size=1, max_size=5)
    logger.info("db_pool_ready")


async def shutdown_db() -> None:
    if _pool is not None:
        await _pool.close()


async def fetch_one(query: str, *args):
    if _pool is None:
        raise RuntimeError("DB not initialized")
    async with _pool.acquire() as conn:
        return await conn.fetchrow(query, *args)

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

pool: AsyncConnectionPool | None = None


async def init_pool(dsn: str) -> None:
    global pool
    pool = AsyncConnectionPool(dsn, kwargs={"row_factory": dict_row}, open=False)
    await pool.open()


async def close_pool() -> None:
    if pool is not None:
        await pool.close()


def get_pool() -> AsyncConnectionPool:
    if pool is None:
        raise RuntimeError("database pool not initialised")
    return pool

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)
UNBOUND = "a job lock needs a session bound to an engine"


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session


@asynccontextmanager
async def exclusive_job(db: AsyncSession, name: str) -> AsyncIterator[bool]:
    bound = db.bind
    if not isinstance(bound, AsyncEngine):
        raise RuntimeError(UNBOUND)
    async with bound.connect() as guard:
        yield bool(await guard.scalar(select(func.pg_try_advisory_xact_lock(func.hashtextextended(name, 0)))))

from collections.abc import AsyncIterator

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

ERASURE_SETTING = "bodha.erasure"

engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session


async def permit_record_erasure(session: AsyncSession) -> None:
    await session.execute(select(func.set_config(ERASURE_SETTING, "on", True)))

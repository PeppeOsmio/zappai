from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from zappai.config import settings


def get_db_url() -> str:
    db_full_url = f"postgresql+asyncpg://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"
    return db_full_url


engine = create_async_engine(url=get_db_url())


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

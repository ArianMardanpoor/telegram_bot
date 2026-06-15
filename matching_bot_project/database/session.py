from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

from bot.core.config import settings   # ✅ اضافه کن

engine = create_async_engine(
    settings.DATABASE_URL,   # ✅ درست
    echo=False,
    pool_pre_ping=False,
)

# Async session factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Base model
Base = declarative_base()


async def get_db_session() -> AsyncSession:
    """
    Dependency helper for FastAPI / bot handlers.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
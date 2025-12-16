"""Database connection and session management.

Provides async PostgreSQL connection via SQLAlchemy 2.0.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

# Default connection string (override via environment)
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/fedrec"


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


# Engine and session factory (initialized lazily)
_engine = None
_async_session_factory = None


def get_engine(database_url: str = DATABASE_URL):
    """Get or create the async database engine.

    Args:
        database_url: PostgreSQL connection string.

    Returns:
        AsyncEngine instance.
    """
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory(database_url: str = DATABASE_URL) -> async_sessionmaker[AsyncSession]:
    """Get or create the async session factory.

    Args:
        database_url: PostgreSQL connection string.

    Returns:
        Async session factory.
    """
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_engine(database_url)
        _async_session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get database session.

    Yields:
        AsyncSession instance.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db(database_url: str = DATABASE_URL) -> None:
    """Initialize database tables (FOR TESTING ONLY).

    WARNING: This bypasses Alembic migrations and creates tables directly
    from SQLAlchemy models. Use this ONLY for:
    - Test database setup (pytest fixtures)
    - Local development quick setup

    For production and normal development, use Alembic migrations:
        alembic upgrade head

    Args:
        database_url: PostgreSQL connection string.
    """
    engine = get_engine(database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    global _engine, _async_session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None

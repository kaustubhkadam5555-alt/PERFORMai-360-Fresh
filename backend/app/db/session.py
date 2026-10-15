import asyncio
from typing import AsyncGenerator, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Async database engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency provider for FastAPI route handlers."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_database_connection(timeout_seconds: float = 3.0) -> Tuple[bool, str]:
    """
    Executes a simple probe (SELECT 1) against PostgreSQL to verify connectivity.
    Returns (True, 'connected') if successful, or (False, reason) if connection fails.
    Does not leak credentials or internal stack traces in error messages.
    """
    try:
        async with asyncio.timeout(timeout_seconds):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True, "connected"
    except asyncio.TimeoutError:
        return False, "Database connection timed out"
    except Exception as exc:
        # Sanitize exception message so connection credentials/passwords are never leaked
        error_type = type(exc).__name__
        return False, f"Database connection unavailable ({error_type})"

# app/db/session.py
#
# PURPOSE:
#   Creates the async SQLAlchemy engine and session factory.
#   Exposes `get_db` — a FastAPI dependency that yields an AsyncSession
#   and handles commit/rollback automatically.
#
# HOW IT WORKS IN A ROUTE:
#   @router.get("/")
#   async def handler(db: AsyncSession = Depends(get_db)):
#       result = await db.execute(select(Datasource))
#       ...
#   FastAPI injects `db`, and `get_db` closes/rolls back the session
#   when the request completes — no manual session management needed.

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from app.core.config import settings


# The async engine manages the connection pool to the InsightX metadata DB
# pool_pre_ping=True: tests connections before use — handles stale connections
#   gracefully after network interruptions or DB restarts
engine = create_async_engine(
    settings.database_url,
    echo=False,           # Set True in development to log all SQL statements
    pool_size=10,         # Persistent connections in the pool
    max_overflow=20,      # Temporary connections allowed above pool_size under load
    pool_pre_ping=True,
)

# Session factory — instantiated once, called many times
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Avoids "DetachedInstanceError" when reading after commit
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session per request.

    - Commits automatically on successful request completion
    - Rolls back automatically if an exception is raised
    - Always closes the session (via async context manager)

    Inject this into any route handler:
        db: AsyncSession = Depends(get_db)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
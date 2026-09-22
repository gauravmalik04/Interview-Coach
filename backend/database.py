import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from backend.config import settings

logger = logging.getLogger("ai_interview.database")

# Create asynchronous SQLAlchemy engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.DEBUG,
    future=True,
    connect_args={"check_same_thread": False, "timeout": 30},
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Declarative base class for models
Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing database session to FastAPI endpoints."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db() -> None:
    """Initialize database tables."""
    # Import models here to ensure they are registered with Base.metadata
    from backend.models import user, interview, report, coach  # noqa: F401
    
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        from sqlalchemy import text
        await conn.execute(text("PRAGMA journal_mode=WAL;"))
        await conn.execute(text("PRAGMA busy_timeout=30000;"))
        await conn.run_sync(Base.metadata.create_all)

        # Non-destructive SQLite schema migration for existing databases
        def migrate_schema(sync_conn):
            from sqlalchemy import inspect, text
            inspector = inspect(sync_conn)
            if "interview_sessions" in inspector.get_table_names():
                existing_cols = {col["name"] for col in inspector.get_columns("interview_sessions")}
                if "interview_mode" not in existing_cols:
                    logger.info("Migrating schema: adding 'interview_mode' to interview_sessions")
                    sync_conn.execute(text("ALTER TABLE interview_sessions ADD COLUMN interview_mode VARCHAR(20) DEFAULT 'real'"))
                if "language" not in existing_cols:
                    logger.info("Migrating schema: adding 'language' to interview_sessions")
                    sync_conn.execute(text("ALTER TABLE interview_sessions ADD COLUMN language VARCHAR(30) DEFAULT 'python'"))
                if "current_question_id" not in existing_cols:
                    logger.info("Migrating schema: adding 'current_question_id' to interview_sessions")
                    sync_conn.execute(text("ALTER TABLE interview_sessions ADD COLUMN current_question_id VARCHAR(50) DEFAULT NULL"))

        await conn.run_sync(migrate_schema)
    logger.info("Database tables initialized successfully.")

async def close_db() -> None:
    """Dispose the engine connection pool."""
    logger.info("Closing database engine...")
    await engine.dispose()
    logger.info("Database engine closed.")

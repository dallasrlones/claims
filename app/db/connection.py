# app/db/connection.py

import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import logging

logger = logging.getLogger(__name__)

# Get the DATABASE_URL from environment variables
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres_change_me@db:5432/claims_db"
)

logger.info(f"DATABASE_URL in app.db.connection: {DATABASE_URL}")

# Create async engine with pool options
async_engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800
)

# Async session factory
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Dependency to provide a session
async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

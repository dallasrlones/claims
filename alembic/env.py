from logging.config import fileConfig
import os

from sqlalchemy import create_engine, pool
from alembic import context
from sqlmodel import SQLModel
from app.models.claim import Claim, ClaimProcedure  # Import your models

# Print out detected tables to debug
print(f"Detected tables: {SQLModel.metadata.tables.keys()}")

# Alembic config object
config = context.config

# Function to get the database URL and ensure it's using the synchronous driver
def get_url():
    url = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres_change_me@db:5432/claims_db")
    return url.replace("+asyncpg", "+psycopg2")

# Set the DB URL for Alembic
config.set_main_option("sqlalchemy.url", get_url())

# Logging configuration
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Track SQLModel metadata for autogeneration
target_metadata = SQLModel.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # Include this to detect type changes
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_engine(
        get_url(),
        poolclass=pool.NullPool
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True  # Include this to detect type changes
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

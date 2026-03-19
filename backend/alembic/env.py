"""Alembic database migration environment configuration.

This module is the entry point Alembic uses when running migrations.
It supports both offline (SQL script generation) and online (live database)
migration modes, using an async SQLAlchemy engine to match the application's
async database layer.
"""

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Ensure the backend package root is on sys.path so application modules
# (config.database, config.settings) can be imported during migrations.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config.model_registry  # noqa: F401 - registrs all models into Base.metadata
from config.database import Base  # noqa: E402
from config.settings import settings  # noqa: E402

# Alembic Config object — provides access to values in alembic.ini.
config = context.config

# Configure Python logging from alembic.ini if a config file is present.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inject the application database URL so alembic.ini does not need to
# hard-code credentials.
config.set_main_option("sqlalchemy.url", settings.database_url)

# Metadata from the declarative base, used by Alembic's autogenerate
# to detect schema differences between models and the live database.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Offline mode configures Alembic with a plain URL instead of a live
    engine, allowing SQL migration scripts to be generated without an
    active database connection.

    The generated SQL is written to the script output rather than
    executed directly.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations synchronously using an existing connection.

    This is a synchronous helper called inside the async context via
    ``run_sync``, bridging SQLAlchemy's async API with Alembic's
    synchronous migration runner.

    Args:
        connection: An active synchronous SQLAlchemy ``Connection`` object
            provided by the async engine's ``run_sync`` bridge.

    """
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations against the live database.

    Builds a transient async engine from the Alembic config section,
    opens a connection, delegates to ``do_run_migrations`` via
    ``run_sync``, then disposes of the engine to release pool resources.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Online mode creates a live database connection and applies migrations
    directly. This function drives the async migration coroutine using
    ``asyncio.run``, keeping Alembic's synchronous entry point compatible
    with the application's async engine.
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

"""Alembic environment configuration for async PostgreSQL migrations."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.models.business_need import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — generates SQL script."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:  # type: ignore[no-untyped-def]
    """Execute migrations within a connection context."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with an async engine."""
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.core.config import settings

    # Always follow the app's DATABASE_URL — not only alembic.ini (Docker/local parity).
    # Some connection strings include query params like `?sslmode=require` which
    # asyncpg.connect does not accept as a keyword argument. Sanitize the URL
    # by removing `sslmode` and translate it into a proper `ssl` connect arg.
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

    raw_url = settings.database_url
    split = urlsplit(raw_url)
    query_items = dict(parse_qsl(split.query))
    sslmode = query_items.pop("sslmode", None)
    new_query = urlencode(query_items)
    sanitized_url = urlunsplit((split.scheme, split.netloc, split.path, new_query, split.fragment))

    connect_args = {}
    if sslmode:
        connect_args["ssl"] = True

    connectable = create_async_engine(
        sanitized_url,
        poolclass=pool.NullPool,
        connect_args=connect_args or None,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migrations — delegates to async runner."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

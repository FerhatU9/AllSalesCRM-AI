"""Alembic environment for the explicit DATABASE_URL connection."""

from __future__ import annotations

import os

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

from allsales.models import Base

load_dotenv()
config = context.config
target_metadata = Base.metadata


def get_url() -> str:
    value = os.environ.get("DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError("Set DATABASE_URL before running migrations")
    if not (value.startswith("postgresql+psycopg://") or value.startswith("sqlite+pysqlite://")):
        raise RuntimeError("Use a PostgreSQL psycopg URL, or SQLite for tests only")
    return value


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(), target_metadata=target_metadata, literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(get_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

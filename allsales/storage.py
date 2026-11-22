"""Database connection helpers. A database URL must be configured explicitly."""

from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is required for database-backed features")
    if not (url.startswith("postgresql+psycopg://") or url.startswith("sqlite+pysqlite://")):
        raise RuntimeError("DATABASE_URL must use PostgreSQL psycopg or SQLite for tests")
    return url


def session_factory(url: str | None = None) -> sessionmaker[Session]:
    engine: Engine = create_engine(url or database_url(), pool_pre_ping=True)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

"""Connection and session helpers for the configured development database.

Reuse a database engine per URL instead of creating a connection pool for every
API request. Keep test databases separate by their complete URL.
"""
from __future__ import annotations

import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is required for database-backed features")
    if not (url.startswith("postgresql+psycopg://") or url.startswith("sqlite+pysqlite://")):
        raise RuntimeError("DATABASE_URL must use PostgreSQL psycopg or SQLite for tests")
    return url


@lru_cache(maxsize=8)
def _factory_for_url(url: str) -> sessionmaker[Session]:
    engine = create_engine(url, pool_pre_ping=True)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def session_factory(url: str | None = None) -> sessionmaker[Session]:
    return _factory_for_url(url or database_url())

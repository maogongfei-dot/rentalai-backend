"""Phase 5-B2 / Phase 9-A1: SQLAlchemy database bootstrap.

Single entry point for the SQLAlchemy stack used by the ``backend/`` package.

* If ``DATABASE_URL`` is set (after trimming), it is used for the engine.
  Heroku/Render-style ``postgres://`` URLs are normalized to ``postgresql://``
  for SQLAlchemy + psycopg2.
* If ``DATABASE_URL`` is unset or empty, behavior matches pre–Phase 9-A1:
  local SQLite at ``sqlite:///./rentalai.db``.

Exposed names:

* ``SQLALCHEMY_DATABASE_URL`` — resolved URL string (for logs/tests).
* ``engine`` — bound Engine.
* ``SessionLocal`` — sessionmaker for short-lived sessions.
* ``Base`` — declarative base for ORM models.
* ``get_db`` — FastAPI dependency that yields a session and closes it.

No tables are declared here; callers register models on ``Base``.
"""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker


def _normalize_database_url(raw: str | None) -> str | None:
    if raw is None:
        return None
    u = str(raw).strip()
    if not u:
        return None
    if u.startswith("postgres://"):
        return "postgresql://" + u[len("postgres://") :]
    return u


def _resolve_sqlalchemy_database_url() -> str:
    url = _normalize_database_url(os.getenv("DATABASE_URL"))
    if url:
        return url
    return "sqlite:///./rentalai.db"


SQLALCHEMY_DATABASE_URL = _resolve_sqlalchemy_database_url()

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

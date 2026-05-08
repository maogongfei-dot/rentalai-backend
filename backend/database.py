"""Phase 5-B2: SQLAlchemy database bootstrap.

Single, minimal entry point for the SQLAlchemy stack used by the new
``backend/`` package. SQLite is the default during local development; a
PostgreSQL ``DATABASE_URL`` may replace it later without changing call sites.

This module deliberately exposes only three names:

* ``engine``       — SQLAlchemy Engine bound to the configured database URL.
* ``SessionLocal`` — sessionmaker factory for short-lived request sessions.
* ``Base``         — declarative base class for future ORM models.

No tables are declared here and no data is migrated. Existing Phase 4 / 5-A
JSON-backed code paths are not touched.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


SQLALCHEMY_DATABASE_URL = "sqlite:///./rentalai.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

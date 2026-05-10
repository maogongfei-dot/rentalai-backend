"""Phase 5-B4: one-shot database table initializer.

Creates every table currently registered on ``Base.metadata`` against the
configured SQLAlchemy engine. Safe to re-run: ``create_all`` is a no-op for
tables that already exist.

Run from the repository root so the SQLite file ``./rentalai.db`` lands in a
predictable location:

    python -m backend.init_db

No business logic, no JSON-to-DB migration, no edits to existing modules.
"""

from __future__ import annotations

import logging

__all__ = ["ensure_sqlalchemy_tables", "main"]


def ensure_sqlalchemy_tables(logger: logging.Logger | None = None) -> None:
    """Import all ORM modules and run ``create_all`` (PostgreSQL or SQLite per ``DATABASE_URL``)."""
    log = logger or logging.getLogger(__name__)

    # Register every model on ``Base.metadata`` before create_all.
    import backend.db_models  # noqa: F401

    from backend.database import Base, SQLALCHEMY_DATABASE_URL, engine

    if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
        log.info("Using SQLite database")
    else:
        log.info("Using PostgreSQL database")

    log.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    log.info("Database tables ready")

    table_names = sorted(Base.metadata.tables.keys())
    log.info(
        "SQLAlchemy OK: create_all done; dialect=%s tables=%s",
        engine.dialect.name,
        ", ".join(table_names) if table_names else "(none)",
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ensure_sqlalchemy_tables()
    print("Database tables created successfully.")


if __name__ == "__main__":
    main()

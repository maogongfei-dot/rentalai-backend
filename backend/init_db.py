"""Phase 5-B4: one-shot database table initializer.

Creates every table currently registered on ``Base.metadata`` against the
configured SQLAlchemy engine. Safe to re-run: ``create_all`` is a no-op for
tables that already exist.

Run from the repository root so the SQLite file ``./rentalai.db`` lands in a
predictable location:

    python -m backend.init_db

No business logic, no JSON-to-DB migration, no edits to existing modules.
"""

from backend.database import Base, engine
from backend.db_models.short_rent_db_model import ShortRentDB  # noqa: F401  (registers table on Base.metadata)


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")


if __name__ == "__main__":
    main()

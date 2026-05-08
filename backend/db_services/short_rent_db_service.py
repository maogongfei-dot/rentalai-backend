"""Phase 5-C1: minimal CRUD helpers for ``short_rent_listings`` (SQLAlchemy).

Does not replace the existing JSON storage in ``backend/storage/``; callers
may use both until a later phase wires the API to the database layer.

``available_dates`` is persisted as JSON text via ``json.dumps`` before insert.
Rows returned from ``get_all_short_rents`` keep the stored string as-is.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select

from backend.database import SessionLocal
from backend.db_models.short_rent_db_model import ShortRentDB

_COLUMN_NAMES = (
    "id",
    "title",
    "location",
    "postcode",
    "price_per_day",
    "available_dates",
    "min_days",
    "max_days",
    "landlord_id",
    "description",
    "created_at",
)


def _serialize_available_dates(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def create_short_rent(data: dict) -> ShortRentDB:
    """Insert one row into ``short_rent_listings``, commit, and return the ORM instance."""
    payload = {name: data.get(name) for name in _COLUMN_NAMES}
    payload["available_dates"] = _serialize_available_dates(data.get("available_dates"))

    row = ShortRentDB(**payload)
    db = SessionLocal()
    try:
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    finally:
        db.close()


def get_all_short_rents() -> list[ShortRentDB]:
    """Return all rows from ``short_rent_listings`` (``available_dates`` left as stored text)."""
    db = SessionLocal()
    try:
        return list(db.scalars(select(ShortRentDB)).all())
    finally:
        db.close()

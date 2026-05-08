"""Phase 5-B3: SQLAlchemy ORM model for short-term rental listings.

Mirrors the JSON shape used by the existing Phase 4 / 5-A ``ShortRentListing``
data class so a future migration can copy rows over without field renames.

``available_dates`` is stored as a JSON string in a TEXT column for now; a
proper array / JSONB column can be introduced when migrating to PostgreSQL.

This module only defines the table schema. No CRUD helpers, no data
migration, no Phase 4 / 5-A behavior changes.
"""

from sqlalchemy import Column, Float, Integer, String, Text

from backend.database import Base


class ShortRentDB(Base):
    __tablename__ = "short_rent_listings"

    id = Column(String, primary_key=True)
    title = Column(String)
    location = Column(String)
    postcode = Column(String)
    price_per_day = Column(Float)
    available_dates = Column(Text)
    min_days = Column(Integer)
    max_days = Column(Integer)
    landlord_id = Column(String)
    description = Column(Text)
    created_at = Column(String)

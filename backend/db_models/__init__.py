"""SQLAlchemy ORM models for the backend package (Phase 5-B3+).

Import this package (or call :func:`backend.init_db.ensure_sqlalchemy_tables`) before
``Base.metadata.create_all`` so every model module is loaded and tables are registered.
"""

from backend.db_models.short_rent_db_model import ShortRentDB
from backend.db_models.user_db_model import User

__all__ = ["ShortRentDB", "User"]

"""Phase 5-C2: manual smoke test for ``short_rent_db_service`` (no pytest).

Run from the repository root so ``backend`` imports resolve and SQLite uses
``./rentalai.db`` next to the project root (see ``backend/database.py``):

    python tests/test_short_rent_db_service.py

If ``test-short-rent-001`` already exists, a new suffix is appended to the id
and insert is retried once.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Allow ``python tests/test_short_rent_db_service.py`` (script dir is ``tests/``).
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlalchemy.exc import IntegrityError

from backend.db_services.short_rent_db_service import create_short_rent, get_all_short_rents


def main() -> None:
    test_data = {
        "id": "test-short-rent-001",
        "title": "Test Short Rent Room",
        "location": "London",
        "postcode": "E1 6AN",
        "price_per_day": 55.0,
        "available_dates": ["2026-06-01", "2026-06-02"],
        "min_days": 2,
        "max_days": 14,
        "landlord_id": "test-landlord-001",
        "description": "Test short rent listing",
        "created_at": "2026-05-08",
    }

    try:
        row = create_short_rent(test_data)
    except IntegrityError:
        test_data["id"] = f"test-short-rent-001-{uuid.uuid4().hex[:8]}"
        row = create_short_rent(test_data)

    all_rows = get_all_short_rents()

    print(f"创建结果 title: {row.title}")
    print(f"当前数据库短租总数量: {len(all_rows)}")


if __name__ == "__main__":
    main()

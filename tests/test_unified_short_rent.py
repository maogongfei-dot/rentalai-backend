"""Smoke test for unified short rent search (run from project root:

    python tests/test_unified_short_rent.py
)."""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.services.unified_short_rent_service import (
    get_combined_short_rent_results,
    get_ranked_short_rent_results,
    search_all_short_rent,
)


def main() -> None:
    bundle = search_all_short_rent()
    internal = bundle["internal"]
    external = bundle["external"]
    combined = get_combined_short_rent_results()
    ranked = get_ranked_short_rent_results()

    print("内部短租数量:", len(internal))
    print("外部短租数量:", len(external))
    print("合并后总数量:", len(combined))
    print()
    print("排序后前5条 (title | source_type | price_per_day):")
    for row in ranked[:5]:
        title = row.get("title", "")
        st = row.get("source_type", "")
        price = row.get("price_per_day")
        print(f"  - {title} | {st} | {price}")


if __name__ == "__main__":
    main()

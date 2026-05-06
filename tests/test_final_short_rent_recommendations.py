"""Smoke test for get_final_short_rent_recommendations (run from project root:

    python tests/test_final_short_rent_recommendations.py
)."""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.services.unified_short_rent_service import get_final_short_rent_recommendations


def main() -> None:
    results = get_final_short_rent_recommendations()

    print("最终推荐总数量:", len(results))
    print()
    print("前 5 条推荐结果:")
    for i, row in enumerate(results[:5], start=1):
        print(f"  [{i}]")
        print("    title:", row.get("title", ""))
        print("    source_type:", row.get("source_type", ""))
        print("    source:", row.get("source", ""))
        print("    price_per_day:", row.get("price_per_day"))
        print("    explanation:", row.get("explanation", ""))
        print()


if __name__ == "__main__":
    main()

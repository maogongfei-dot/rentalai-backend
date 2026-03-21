# P7 Phase1：Zoopla 列表页原始抓取调试（在 rental_app 下执行）
#   python scripts/run_zoopla_scrape.py --limit 5
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from data.scraper.zoopla_scraper import (  # noqa: E402
    DEFAULT_ZOOPLA_SEARCH_URL,
    ZooplaScraper,
)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    p = argparse.ArgumentParser(description="Zoopla 列表页抓取（P7 Phase1，raw dict）")
    p.add_argument("--url", default=None, help="search_url（默认伦敦租赁列表）")
    p.add_argument("--limit", type=int, default=5, help="最多条数")
    p.add_argument("--headed", action="store_true", help="有界面模式")
    p.add_argument("--debug", action="store_true")
    p.add_argument("--save-sample", action="store_true", help="写入 zoopla_raw_sample.json")
    p.add_argument("--save-html", action="store_true")
    p.add_argument("--screenshot", action="store_true")
    p.add_argument("--output-dir", default=None)
    args = p.parse_args()

    query: dict = {
        "headless": not args.headed,
        "debug": args.debug,
        "save_raw_sample": args.save_sample,
        "save_raw_html": args.save_html,
        "save_screenshots": args.screenshot,
        "output_dir": args.output_dir,
    }
    if args.url:
        query["search_url"] = args.url

    scraper = ZooplaScraper()
    rows = scraper.scrape(query=query, limit=args.limit)
    ok = len(rows) > 0
    stats = scraper.last_scrape_stats
    print(
        json.dumps(
            {
                "ok": ok,
                "search_url": args.url or DEFAULT_ZOOPLA_SEARCH_URL,
                "cards_in_dom": stats.get("cards_in_dom") if stats else None,
                "returned": len(rows),
                "sample": rows[0] if rows else None,
                "listing_ids": [r.get("listing_id") for r in rows[:10]],
            },
            indent=2,
            ensure_ascii=False,
        ),
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

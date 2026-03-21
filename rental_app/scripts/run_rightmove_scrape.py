# P6 Phase3：Rightmove 列表页原始抓取调试（在 rental_app 下执行）
#   python scripts/run_rightmove_scrape.py
#   python scripts/run_rightmove_scrape.py --limit 5 --debug --save-sample
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from data.scraper.rightmove_scraper import (  # noqa: E402
    DEFAULT_RIGHTMOVE_SEARCH_URL,
    RightmoveScraper,
)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
    p = argparse.ArgumentParser(
        description="Rightmove 列表页抓取（原始 dict，P6 Phase3）",
    )
    p.add_argument("--url", default=None, help="search_url（默认伦敦区域列表）")
    p.add_argument("--limit", type=int, default=5, help="最多条数")
    p.add_argument("--headed", action="store_true", help="有界面浏览器")
    p.add_argument("--debug", action="store_true", help="打印卡片数与样本字段")
    p.add_argument(
        "--save-sample",
        action="store_true",
        help="写入 samples/debug/rightmove_raw_sample.json",
    )
    p.add_argument("--save-html", action="store_true", help="保存列表页 HTML 到 samples/debug")
    p.add_argument("--screenshot", action="store_true", help="保存截图到 samples/debug")
    args = p.parse_args()

    query: dict = {
        "headless": not args.headed,
        "debug": args.debug,
        "save_raw_sample": args.save_sample,
        "save_raw_html": args.save_html,
        "save_screenshots": args.screenshot,
    }
    if args.url:
        query["search_url"] = args.url

    scraper = RightmoveScraper()
    rows = scraper.scrape(query=query, limit=args.limit)
    ok = len(rows) > 0
    stats = scraper.last_scrape_stats
    print(
        json.dumps(
            {
                "ok": ok,
                "search_url": args.url or DEFAULT_RIGHTMOVE_SEARCH_URL,
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

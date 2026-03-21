# P7 Phase1：Zoopla 列表页连通性探针（在 rental_app 下执行）
#   python scripts/run_zoopla_probe.py
#   python scripts/run_zoopla_probe.py --url "https://www.zoopla.co.uk/to-rent/property/london/"
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from data.scraper.playwright_runner import run_zoopla_probe  # noqa: E402


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
    p = argparse.ArgumentParser(description="Zoopla 页面探针（不解析 listing 卡片）")
    p.add_argument("--url", default=None, help="覆盖默认 search_url")
    p.add_argument("--headed", action="store_true")
    p.add_argument("--save-html", action="store_true")
    p.add_argument("--screenshot", action="store_true")
    p.add_argument("--output-dir", default=None)
    args = p.parse_args()
    r = run_zoopla_probe(
        search_url=args.url,
        headless=not args.headed,
        save_raw_html=args.save_html,
        save_screenshots=args.screenshot,
        output_dir=args.output_dir,
    )
    print(json.dumps(r, indent=2, ensure_ascii=False))
    sys.exit(0 if r.get("success") else 1)


if __name__ == "__main__":
    main()

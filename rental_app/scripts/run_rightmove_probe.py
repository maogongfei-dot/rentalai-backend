# P6 Phase2：本地调试 — 在 rental_app 目录下执行:
#   python scripts/run_rightmove_probe.py
#   python scripts/run_rightmove_probe.py --headed --save-html --screenshot
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from data.scraper.playwright_runner import run_rightmove_probe  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(
        description="Rightmove 页面探针（P6 Phase2，不解析 listing）",
    )
    p.add_argument("--url", default=None, help="覆盖默认 search_url")
    p.add_argument("--headed", action="store_true", help="有界面模式（headless=False）")
    p.add_argument("--save-html", action="store_true", help="写入 data/scraper/samples/debug/")
    p.add_argument("--screenshot", action="store_true", help="同上目录保存 PNG")
    p.add_argument(
        "--output-dir",
        default=None,
        help="调试输出目录（默认 samples/debug）",
    )
    args = p.parse_args()
    result = run_rightmove_probe(
        search_url=args.url,
        headless=not args.headed,
        save_raw_html=args.save_html,
        save_screenshots=args.screenshot,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()

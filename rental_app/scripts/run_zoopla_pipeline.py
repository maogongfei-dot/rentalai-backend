# P7 Phase2：Zoopla → normalizer → storage 调试入口（在 rental_app 下执行）
#   python scripts/run_zoopla_pipeline.py --limit 3
#   python scripts/run_zoopla_pipeline.py --limit 3 --no-save --save-raw --save-normalized
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from data.pipeline.zoopla_pipeline import run_zoopla_pipeline  # noqa: E402


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    p = argparse.ArgumentParser(
        description="Zoopla → normalizer → storage 闭环（P7 Phase2）",
    )
    p.add_argument("--url", default=None, help="search_url（默认伦敦租赁列表）")
    p.add_argument("--limit", type=int, default=5, help="抓取条数上限")
    p.add_argument(
        "--no-save",
        action="store_true",
        help="不写 storage（仅抓取 + 标准化）",
    )
    p.add_argument(
        "--storage-path",
        default=None,
        help="listings.json 路径（默认 data/listings.json）",
    )
    p.add_argument("--save-raw", action="store_true", help="写入 zoopla_raw_sample.json")
    p.add_argument(
        "--save-normalized",
        action="store_true",
        help="写入 zoopla_normalized_sample.json",
    )
    p.add_argument("--headed", action="store_true", help="有界面浏览器")
    p.add_argument("--debug", action="store_true", help="传给 scraper 的 debug 输出")
    args = p.parse_args()

    query: dict = {
        "headless": not args.headed,
        "debug": args.debug,
    }
    if args.url:
        query["search_url"] = args.url

    result = run_zoopla_pipeline(
        query=query,
        limit=args.limit,
        persist=not args.no_save,
        storage_path=args.storage_path,
        save_raw_sample=args.save_raw,
        save_normalized_sample=args.save_normalized,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()

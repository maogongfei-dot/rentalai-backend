# P7 Phase3：多平台聚合 pipeline 调试入口（在 rental_app 下执行）
#   python scripts/run_multi_source_pipeline.py --sources rightmove
#   python scripts/run_multi_source_pipeline.py --sources zoopla
#   python scripts/run_multi_source_pipeline.py --sources rightmove,zoopla --limit 3 --save-aggregated-sample
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from data.pipeline.multi_source_pipeline import run_multi_source_pipeline  # noqa: E402


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    p = argparse.ArgumentParser(
        description="多平台 Rightmove + Zoopla 聚合调度（P7 Phase3）",
    )
    p.add_argument(
        "--sources",
        default="rightmove,zoopla",
        help="逗号分隔：rightmove / zoopla（默认两者）",
    )
    p.add_argument("--limit", type=int, default=5, help="每平台 limit")
    p.add_argument("--no-save", action="store_true", help="子 pipeline 不写 storage")
    p.add_argument("--storage-path", default=None)
    p.add_argument(
        "--save-aggregated-sample",
        action="store_true",
        help="写入 samples/debug/multi_source_aggregated_sample.json",
    )
    p.add_argument("--headed", action="store_true", help="子抓取有界面（两平台 query.headless）")
    args = p.parse_args()

    srcs = [s.strip().lower() for s in args.sources.split(",") if s.strip()]

    query: dict = {"headless": not args.headed}
    result = run_multi_source_pipeline(
        sources=srcs,
        query=query,
        limit_per_source=args.limit,
        persist=not args.no_save,
        storage_path=args.storage_path,
        save_aggregated_sample=args.save_aggregated_sample,
    )

    # 控制台不打印完整 listings，仅样本与统计
    out = dict(result)
    out["aggregated_listings_sample"] = result.get("aggregated_listings_sample") or []

    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()

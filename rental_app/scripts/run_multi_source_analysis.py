# P7 Phase4：多平台抓取 + analyze-batch 统一调试入口（在 rental_app 下执行）
#   python scripts/run_multi_source_analysis.py --sources rightmove --limit 3
#   python scripts/run_multi_source_analysis.py --sources zoopla --limit 3
#   python scripts/run_multi_source_analysis.py --sources rightmove,zoopla --limit 2 --save-analysis-sample
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from data.pipeline.analysis_bridge import run_multi_source_analysis  # noqa: E402


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    p = argparse.ArgumentParser(
        description="多平台聚合 → analyze-batch（P7 Phase4 桥接）",
    )
    p.add_argument(
        "--sources",
        default="rightmove,zoopla",
        help="逗号分隔：rightmove / zoopla",
    )
    p.add_argument("--limit", type=int, default=5, help="每平台 limit")
    p.add_argument("--no-save", action="store_true", help="子 pipeline 不写 storage")
    p.add_argument("--storage-path", default=None)
    p.add_argument("--budget", type=float, default=None, help="可选：写入每条 batch property")
    p.add_argument("--target-postcode", default=None, help="可选：target_postcode")
    p.add_argument(
        "--save-aggregated-sample",
        action="store_true",
        help="写入 data/scraper/samples/debug/multi_source_aggregated_sample.json",
    )
    p.add_argument(
        "--save-analysis-sample",
        action="store_true",
        help="写入 data/scraper/samples/debug/multi_source_analysis_sample.json",
    )
    p.add_argument("--headed", action="store_true", help="子抓取有界面（query.headless）")
    args = p.parse_args()

    srcs = [s.strip().lower() for s in args.sources.split(",") if s.strip()]
    query: dict = {"headless": not args.headed}

    result = run_multi_source_analysis(
        sources=srcs,
        query=query,
        limit_per_source=args.limit,
        persist=not args.no_save,
        storage_path=args.storage_path,
        save_aggregated_sample=args.save_aggregated_sample,
        save_analysis_sample=args.save_analysis_sample,
        budget=args.budget,
        target_postcode=args.target_postcode,
    )

    # 控制台省略完整 analysis_envelope（体积大）；需要时看 sample 文件或自行改打印
    slim = {k: v for k, v in result.items() if k != "analysis_envelope"}
    print(json.dumps(slim, indent=2, ensure_ascii=False, default=str))
    if result.get("analysis_envelope"):
        env = result["analysis_envelope"]
        d = env.get("data") if isinstance(env, dict) else None
        if isinstance(d, dict):
            print(
                "\n--- analysis_envelope.data (keys only) ---\n",
                json.dumps(list(d.keys()), ensure_ascii=False),
            )

    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()

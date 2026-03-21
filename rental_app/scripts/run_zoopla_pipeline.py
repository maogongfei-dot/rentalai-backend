# P6 Phase5：Zoopla 闭环 CLI 占位（在 rental_app 下执行）
#   python scripts/run_zoopla_pipeline.py
# 输出占位 JSON；下一阶段将实现与 run_rightmove_pipeline 对称的真实链路。
from __future__ import annotations

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
    r = run_zoopla_pipeline()
    print(json.dumps(r, indent=2, ensure_ascii=False))
    sys.exit(0 if r.get("success") else 1)


if __name__ == "__main__":
    main()

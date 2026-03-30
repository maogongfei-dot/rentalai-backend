#!/usr/bin/env python3
"""
Phase 3 合同分析 CLI：默认输出「产品化」分段报告；``--json`` 输出完整结构化 JSON。

用法（在 rental_app 目录下）::

    python scripts/contract_phase3_demo.py path/to/contract.txt
    python scripts/contract_phase3_demo.py --json path/to/contract.txt
    echo "Rent 800 pcm. Admin fee 200." | python scripts/contract_phase3_demo.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_text(path: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    return sys.stdin.read()


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 3 合同分析 CLI（两层输出 + 展示层）")
    parser.add_argument(
        "file",
        nargs="?",
        default=None,
        help="合同文本文件路径；省略则从 stdin 读取",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="输出完整 JSON（structured_analysis / explain / presentation）",
    )
    args = parser.parse_args()

    root = _root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from contract_analysis.service import analyze_contract_with_explain

    text = _load_text(args.file)
    out = analyze_contract_with_explain(contract_text=text)

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
        return

    pres = out.get("presentation") or {}
    plain = pres.get("plain_text")
    if isinstance(plain, str) and plain.strip():
        print(plain)
        return

    from contract_analysis.presentation import format_contract_analysis_cli_report

    sa = out.get("structured_analysis") or {}
    ex = out.get("explain") or {}
    print(format_contract_analysis_cli_report(sa, ex))


if __name__ == "__main__":
    main()

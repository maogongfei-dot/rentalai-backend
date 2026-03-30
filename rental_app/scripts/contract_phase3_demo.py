#!/usr/bin/env python3
"""
Phase 3 合同分析 CLI 演示：从文件或 stdin 读入文本，打印 JSON 结果。

用法（在 rental_app 目录下）::

    python scripts/contract_phase3_demo.py path/to/contract.txt
    echo "Rent 800 pcm. Admin fee 200." | python scripts/contract_phase3_demo.py

可选环境变量（仅演示）：无
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_text() -> str:
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        return p.read_text(encoding="utf-8", errors="replace")
    return sys.stdin.read()


def main() -> None:
    root = _root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from contract_analysis.service import analyze_contract

    text = _load_text()
    out = analyze_contract(contract_text=text)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

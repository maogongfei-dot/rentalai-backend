#!/usr/bin/env python3
"""
Phase 4：合同分析 HTTP 接口本地冒烟（需已启动 ``python run.py`` 或等价 uvicorn）。

用法（在 ``rental_app`` 目录下）::

    python scripts/contract_analysis_api_smoke.py

可选环境变量 ``RENTALAI_API_BASE``（默认 ``http://127.0.0.1:8000``），与前端构建注入习惯一致。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests


def _root() -> Path:
    return Path(__file__).resolve().parent.parent


def main() -> int:
    base = (os.environ.get("RENTALAI_API_BASE") or "http://127.0.0.1:8000").rstrip("/")
    root = _root()
    sample_rel = "contract_analysis/samples/sample_contract.txt"
    sample_path = (root / sample_rel).resolve()

    print(f"API base: {base}")
    print()

    # 1) 文本分析
    url_text = f"{base}/api/contract/analysis/text"
    payload_text = {
        "contract_text": (
            "Assured shorthold tenancy. Monthly rent £950 pcm payable in advance. "
            "Deposit £1095 protected in DPS."
        ),
        "metadata": {"source_name": "smoke-text", "monthly_rent": 950.0, "deposit_amount": 1095.0},
    }
    try:
        r1 = requests.post(url_text, json=payload_text, timeout=120)
    except requests.exceptions.ConnectionError:
        print("ERROR: 无法连接 API。请先在本目录执行: python run.py", file=sys.stderr)
        return 1
    print(f"[1] POST /api/contract/analysis/text -> HTTP {r1.status_code}")
    if r1.ok:
        data = r1.json()
        res = data.get("result") or {}
        print(f"    ok={data.get('ok')} engine={data.get('engine')}")
        print(f"    result keys: {list(res.keys())}")
        sv = res.get("summary_view") or {}
        expected_sv = (
            "overall_conclusion",
            "key_risk_summary",
            "risk_category_summary",
            "highlighted_risk_clauses",
            "clause_severity_overview",
            "contract_completeness_overview",
            "action_advice",
        )
        missing = [k for k in expected_sv if k not in sv]
        if missing:
            print(f"    ERROR: summary_view missing keys: {missing}", file=sys.stderr)
            return 1
        oc = str(sv.get("overall_conclusion", ""))[:120]
        print(f"    summary_view.overall_conclusion (preview): {oc!r}")
        ra = res.get("raw_analysis") or {}
        print(f"    raw_analysis keys: {list(ra.keys())}")
    else:
        print(r1.text[:500])
        return 1

    print()

    # 2) 文件路径分析（相对 rental_app 根）
    if not sample_path.is_file():
        print(f"[2] SKIP file-path: missing {sample_path}", file=sys.stderr)
        return 0

    url_file = f"{base}/api/contract/analysis/file-path"
    payload_file = {"file_path": sample_rel, "metadata": {"source_name": "smoke-file"}}
    r2 = requests.post(url_file, json=payload_file, timeout=120)
    print(f"[2] POST /api/contract/analysis/file-path -> HTTP {r2.status_code}")
    if r2.ok:
        data = r2.json()
        res = data.get("result") or {}
        print(f"    ok={data.get('ok')} engine={data.get('engine')}")
        print(f"    result keys: {list(res.keys())}")
        ar = (res.get("raw_analysis") or {}).get("analysis_result") or {}
        summ = str(ar.get("summary", ""))[:120]
        print(f"    raw_analysis.analysis_result summary (preview): {summ!r}")
    else:
        print(r2.text[:500])
        return 1

    print()
    print("Smoke OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

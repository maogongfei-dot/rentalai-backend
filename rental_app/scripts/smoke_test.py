#!/usr/bin/env python3
"""
Minimal post-deploy smoke: GET /health + POST housing query (canonical: /api/ai/query).

Backend also mounts POST /ai/query as an alias; this script tries /api/ai/query first,
then /ai/query if the first returns HTTP 404.

Usage (from rental_app directory):
  python scripts/smoke_test.py https://your-api.onrender.com

Or set env (VITE name preferred for parity with frontend):
  VITE_RENTALAI_API_BASE  or  RENTALAI_API_BASE
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Optional, Tuple

# Canonical path used by web_public assets; FastAPI registers both this and /ai/query.
QUERY_PATH_PRIMARY = "/api/ai/query"
QUERY_PATH_FALLBACK = "/ai/query"


def _get_base() -> str:
    b = (
        os.environ.get("VITE_RENTALAI_API_BASE")
        or os.environ.get("RENTALAI_API_BASE")
        or (sys.argv[1] if len(sys.argv) > 1 else "")
    )
    return str(b).strip().rstrip("/")


def _req_json(
    method: str,
    url: str,
    body: Optional[dict[str, Any]] = None,
    timeout: float = 120.0,
) -> Tuple[int, dict]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        raw = json.dumps(body).encode("utf-8")
        data = raw
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            return resp.getcode(), json.loads(text) if text.strip() else {}
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace") if e.fp else ""
        try:
            return e.code, json.loads(text) if text.strip() else {}
        except json.JSONDecodeError:
            return e.code, {"_raw": text}


def _post_query(base: str, body: dict[str, Any]) -> Tuple[int, dict, str]:
    paths = (QUERY_PATH_PRIMARY, QUERY_PATH_FALLBACK)
    last_code = 0
    last_data: dict = {}
    for path in paths:
        url = f"{base}{path}"
        code, data = _req_json("POST", url, body, timeout=120.0)
        last_code, last_data = code, data
        if code != 404:
            return code, data, path
    return last_code, last_data, paths[-1]


def main() -> int:
    base = _get_base()
    if not base:
        print(
            "Usage: VITE_RENTALAI_API_BASE or RENTALAI_API_BASE, or:\n"
            "  python scripts/smoke_test.py https://your-api.onrender.com",
            file=sys.stderr,
        )
        return 1

    health_url = f"{base}/health"

    print("GET", health_url)
    code, h = _req_json("GET", health_url, None, timeout=30.0)
    print("  status:", code, "| success:", h.get("success"), "| service:", h.get("service"), "| health:", h.get("status"))

    sample = os.environ.get("RENTALAI_SMOKE_QUERY", "2 bed flat in Milton Keynes under 1500 pcm")
    code, q, path_used = _post_query(base, {"user_text": sample})
    print("POST", f"{base}{path_used}")
    print("  body user_text:", repr(sample[:80] + ("..." if len(sample) > 80 else "")))
    print("  status:", code)
    print("  success:", q.get("success"))
    pq = q.get("parsed_query") if isinstance(q.get("parsed_query"), dict) else {}
    print("  location (parsed):", pq.get("location"))
    ms = q.get("market_stats") if isinstance(q.get("market_stats"), dict) else {}
    print("  total_listings:", ms.get("total_listings"))
    td = q.get("top_deals") if isinstance(q.get("top_deals"), dict) else {}
    rows = td.get("top_deals") if isinstance(td.get("top_deals"), list) else []
    print("  top_deals count:", len(rows))
    rep = q.get("recommendation_report") if isinstance(q.get("recommendation_report"), dict) else {}
    print("  recommendation_report.summary_sentence:", (rep.get("summary_sentence") or "")[:120])

    if code != 200:
        print(f"FAIL: non-200 from housing query ({path_used})", file=sys.stderr)
        return 2
    if h.get("status") != "ok" and not h.get("success"):
        print("WARN: /health body unexpected", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

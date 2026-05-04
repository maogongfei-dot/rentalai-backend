# Phase 1-A5：外部短租搜索骨架（模拟数据，无爬虫、无真实 API）。
from __future__ import annotations

import random
from typing import Any


def search_external_short_rent(query: dict) -> list[dict]:
    """
    根据搜索条件返回模拟外部短租房源（3～5 条），结构与 ListingSchema 常用字段对齐，
    并包含约定展示字段 id / price / location。
    """
    if not isinstance(query, dict):
        query = {}

    location = str(query.get("location") or "").strip() or "London"

    mn = query.get("min_price")
    mx = query.get("max_price")
    try:
        lo = float(mn) if mn is not None else 400.0
    except (TypeError, ValueError):
        lo = 400.0
    try:
        hi = float(mx) if mx is not None else 1500.0
    except (TypeError, ValueError):
        hi = 1500.0
    if hi < lo:
        lo, hi = hi, lo

    n = random.randint(3, 5)
    span = max(hi - lo, 1.0)
    titles = [
        f"Short let near {location}",
        f"Private room — {location}",
        f"Bright studio — {location}",
        f"Spare room (external) — {location}",
        f"Flexible stay — {location}",
    ]

    out: list[dict[str, Any]] = []
    for i in range(n):
        # 在 [lo, hi] 内分散取值，避免全挤在边界
        t = (i + 0.5) / max(n, 1)
        jitter = random.uniform(-0.08, 0.08) * span
        price = lo + span * t + jitter
        price = round(max(lo, min(hi, price)), 2)

        ext_id = f"ext_{location.lower().replace(' ', '_')[:12]}_{i + 1:02d}_{random.randint(1000, 9999)}"
        row: dict[str, Any] = {
            "id": ext_id,
            "listing_id": ext_id,
            "title": titles[i % len(titles)],
            "price": price,
            "rent_pcm": price,
            "location": location,
            "city": location,
            "listing_mode": "short_rent",
            "source_type": "external",
            "availability_status": "available",
            "image_urls": ["https://example.com/image1.jpg"],
        }
        out.append(row)

    return out


def merge_external_into_pool(pool: list[dict], external_list: list[dict]) -> list[dict]:
    """
    将外部房源插在 pool 前面（优先展示），返回新列表，不修改入参中的 list 对象本身
    （但 list 元素仍为同一 dict 引用；需要深拷贝时由调用方处理）。
    """
    if not isinstance(external_list, list):
        external_list = []
    if not isinstance(pool, list):
        pool = []
    ext = [x for x in external_list if isinstance(x, dict)]
    rest = [x for x in pool if isinstance(x, dict)]
    return ext + rest

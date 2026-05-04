# 第一版：仅根据 availability_status 做本地可展示性判断（无网络、无爬虫）。
from __future__ import annotations


def check_listing_availability(listing: dict) -> dict:
    """
    根据 listing 中的 availability_status 判断房源是否仍可展示。

    - rented / paused → 不可展示
    - available → 可展示
    - 缺失、unknown 或其它未识别值 → 不可展示；未知类原因 reason 为 availability_unknown
    """
    if not isinstance(listing, dict):
        listing = {}

    raw = listing.get("availability_status")
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return {
            "is_available": False,
            "availability_status": "unknown",
            "reason": "availability_unknown",
        }

    if not isinstance(raw, str):
        return {
            "is_available": False,
            "availability_status": "unknown",
            "reason": "availability_unknown",
        }

    status = raw.strip().lower()

    if status == "available":
        return {
            "is_available": True,
            "availability_status": "available",
            "reason": "",
        }
    if status == "rented":
        return {
            "is_available": False,
            "availability_status": "rented",
            "reason": "rented",
        }
    if status == "paused":
        return {
            "is_available": False,
            "availability_status": "paused",
            "reason": "paused",
        }
    if status == "unknown":
        return {
            "is_available": False,
            "availability_status": "unknown",
            "reason": "availability_unknown",
        }

    return {
        "is_available": False,
        "availability_status": status,
        "reason": "availability_unknown",
    }


def filter_available_listings(listings: list[dict]) -> list[dict]:
    """
    仅保留可展示房源；每条结果附带 availability_check_result（check_listing_availability 返回值）。
    不修改入参中的原始 dict（浅拷贝后写入新字段）。
    """
    out: list[dict] = []
    for listing in listings:
        if not isinstance(listing, dict):
            continue
        result = check_listing_availability(listing)
        if not result.get("is_available"):
            continue
        row = {**listing, "availability_check_result": result}
        out.append(row)
    return out

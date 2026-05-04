# 本地房源新鲜度：过期 / 需刷新判断（无网络）。
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def _parse_iso_utc(value: str) -> datetime | None:
    """将 ISO 8601 字符串解析为带 UTC 偏移的 datetime；无法解析则 None。"""
    s = value.strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def is_listing_stale(listing: dict) -> bool:
    """
    是否视为过期 / 需刷新：
    - 无 availability_checked_at → True
    - 当前 UTC 时间与该时间差 > 24 小时 → True
    - 否则 False
    """
    if not isinstance(listing, dict):
        return True

    raw = listing.get("availability_checked_at")
    if raw is None:
        return True
    if not isinstance(raw, str) or not raw.strip():
        return True

    checked = _parse_iso_utc(raw)
    if checked is None:
        return True

    now = datetime.now(timezone.utc)
    return now - checked > timedelta(hours=24)


def mark_listing_checked(listing: dict) -> dict:
    """写入 availability_checked_at（当前 UTC，ISO 字符串），返回新 dict。"""
    if not isinstance(listing, dict):
        return {
            "availability_checked_at": datetime.now(timezone.utc).isoformat(),
        }
    out: dict[str, Any] = {**listing}
    out["availability_checked_at"] = datetime.now(timezone.utc).isoformat()
    return out


def filter_fresh_listings(listings: list[dict]) -> list[dict]:
    """只保留未 stale 的房源（非 dict 条目丢弃）。"""
    if not isinstance(listings, list):
        return []
    return [x for x in listings if isinstance(x, dict) and not is_listing_stale(x)]

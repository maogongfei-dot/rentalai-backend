"""
Phase A1：统一房源标准结构（canonical house schema）。
任意来源 dict → normalize_house_record → 固定字段；推荐链路再经 canonical_to_listing_row 回到现有 ListingSchema / 引擎字段。
"""

from __future__ import annotations

import copy
from typing import Any

from data.normalizer.listing_normalizer import normalize_listing_payload

# ---------------------------------------------------------------------------
# 统一字段定义：与 ListingSchema / 推荐引擎兼容，并扩展展示与评分字段
# ---------------------------------------------------------------------------

HOUSE_SCHEMA_FIELDS: tuple[str, ...] = (
    "listing_id",
    "source",
    "source_url",
    "listing_title",
    "city",
    "area",
    "postcode",
    "address_text",
    "rent",
    "bills",
    "deposit",
    "bedrooms",
    "bathrooms",
    "furnished",
    "property_type",
    "couple_friendly",
    "near_station",
    "commute_minutes",
    "available_date",
    "min_tenancy_months",
    "features",
    "notes",
    "final_score",
    "scores",
    "raw_source_data",
)


def _first(data: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if k not in data:
            continue
        v = data[k]
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        return v
    return None


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip().replace("£", "").replace(",", "")
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _to_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if value == 1:
            return True
        if value == 0:
            return False
        return None
    if isinstance(value, str):
        s = value.strip().lower()
        if s in ("yes", "true", "1", "y", "included", "包"):
            return True
        if s in ("no", "false", "0", "n", "excluded"):
            return False
    return None


def _features_from_raw(raw: dict[str, Any]) -> list[str] | None:
    v = raw.get("features")
    if v is None:
        return None
    if isinstance(v, list):
        out = [str(x).strip() for x in v if str(x).strip()]
        return out if out else None
    if isinstance(v, str):
        parts = [p.strip() for p in v.split(",") if p.strip()]
        return parts if parts else None
    return None


def _clean_str(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def normalize_house_record(raw: dict[str, Any], source: str = "unknown") -> dict[str, Any]:
    """
    原始房源 dict → 统一 canonical dict（含 HOUSE_SCHEMA_FIELDS 全部键；缺省为 None）。
    内部先走现有 normalize_listing_payload（ListingSchema），再合并别名字段与数值/布尔清洗。
    """
    if not isinstance(raw, dict):
        raw = {}
    raw_source_data: dict[str, Any] = copy.deepcopy(raw)

    # 原始字段 → ListingSchema（与 data/normalizer 一致）
    ls = normalize_listing_payload(raw, source=source)
    d = ls.to_dict()

    # 别名字段 → 标准键；以下数值/布尔用 _to_* 做基础清洗（与 listing_normalizer 互补）
    rent = _to_float(_first(raw, "rent", "rent_pcm", "price", "monthly_rent"))
    if rent is None:
        rent = d.get("rent_pcm")
    if rent is not None:
        rent = float(rent)

    listing_title = _first(raw, "listing_title", "house_label", "title", "name") or d.get("title")
    address_text = _first(raw, "address_text", "address", "full_address", "displayAddress") or d.get("address")
    area = _first(raw, "area", "area_name", "neighbourhood") or d.get("area_name")
    city = d.get("city") or _clean_str(_first(raw, "city", "town"))
    postcode = d.get("postcode") or _clean_str(_first(raw, "postcode", "post_code"))

    bills = _to_bool(_first(raw, "bills", "bills_included", "bill_included", "includes_bills"))
    if bills is None:
        bills = d.get("bills_included")

    dep = _to_float(_first(raw, "deposit", "deposit_amount"))
    if dep is None:
        dep = _to_float(d.get("deposit"))
    deposit = dep

    br = _to_float(_first(raw, "bedrooms", "beds", "bed", "bedroom"))
    if br is None and d.get("bedrooms") is not None:
        br = float(d["bedrooms"])
    bedrooms = br

    bt = _to_float(_first(raw, "bathrooms", "baths", "bath"))
    if bt is None and d.get("bathrooms") is not None:
        bt = float(d["bathrooms"])
    bathrooms = bt
    furnished = _to_bool(_first(raw, "furnished", "is_furnished")) or d.get("furnished")
    commute_minutes = _to_int(_first(raw, "commute_minutes", "commute", "commute_mins")) or d.get(
        "commute_minutes"
    )

    couple_friendly = _to_bool(_first(raw, "couple_friendly", "couples_ok", "couple_ok"))
    near_station = _to_bool(_first(raw, "near_station", "close_to_station", "walk_to_station"))
    if near_station is None and isinstance(d.get("summary"), str):
        sl = d["summary"].lower()
        if "station" in sl or "tube" in sl:
            near_station = True

    available_date = _clean_str(_first(raw, "available_date", "available_from", "move_in_date")) or d.get(
        "available_from"
    )
    min_tenancy_months = _to_int(_first(raw, "min_tenancy_months", "min_term_months")) or d.get(
        "min_tenancy_months"
    )

    notes = _clean_str(_first(raw, "notes", "note", "remarks")) or d.get("summary")
    features = _features_from_raw(raw)
    if not features and isinstance(d, dict):
        features = _features_from_raw(d)

    final_score = _to_float(raw.get("final_score"))
    scores = raw.get("scores") if isinstance(raw.get("scores"), dict) else None

    src = _clean_str(d.get("source")) or _clean_str(source) or "unknown"

    out: dict[str, Any] = {
        "listing_id": d.get("listing_id"),
        "source": src,
        "source_url": d.get("source_url"),
        "listing_title": listing_title,
        "city": city,
        "area": area,
        "postcode": postcode,
        "address_text": address_text,
        "rent": rent,
        "bills": bills,
        "deposit": deposit,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "furnished": furnished,
        "property_type": d.get("property_type"),
        "couple_friendly": couple_friendly,
        "near_station": near_station,
        "commute_minutes": commute_minutes,
        "available_date": available_date,
        "min_tenancy_months": min_tenancy_months,
        "features": features,
        "notes": notes,
        "final_score": final_score,
        "scores": scores,
        "raw_source_data": raw_source_data,
    }

    # 保证键集稳定
    for k in HOUSE_SCHEMA_FIELDS:
        if k not in out:
            out[k] = None
    return {k: out[k] for k in HOUSE_SCHEMA_FIELDS}


def canonical_to_listing_row(canonical: dict[str, Any]) -> dict[str, Any]:
    """
    canonical dict → 与 ai_demo_listings / export_listings 兼容的扁平 dict（rent_pcm、title、area_name…）。
    供 _passes_filters、listing_dict_to_engine_house、normalize_listing_payload 复用。
    """
    if not isinstance(canonical, dict):
        canonical = {}

    row: dict[str, Any] = {
        "listing_id": canonical.get("listing_id"),
        "source": canonical.get("source"),
        "source_url": canonical.get("source_url"),
        "title": canonical.get("listing_title"),
        "address": canonical.get("address_text"),
        "postcode": canonical.get("postcode"),
        "area_name": canonical.get("area"),
        "city": canonical.get("city"),
        "rent_pcm": canonical.get("rent"),
        "bills_included": canonical.get("bills"),
        "deposit": canonical.get("deposit"),
        "bedrooms": canonical.get("bedrooms"),
        "bathrooms": canonical.get("bathrooms"),
        "furnished": canonical.get("furnished"),
        "property_type": canonical.get("property_type"),
        "commute_minutes": canonical.get("commute_minutes"),
        "summary": canonical.get("notes"),
        "min_tenancy_months": canonical.get("min_tenancy_months"),
        "available_from": canonical.get("available_date"),
        "couple_friendly": canonical.get("couple_friendly"),
        "near_station": canonical.get("near_station"),
        "features": canonical.get("features"),
        "final_score": canonical.get("final_score"),
        "scores": canonical.get("scores"),
    }
    return {k: v for k, v in row.items() if v is not None}


def normalize_house_records(records: list[dict[str, Any]], source: str = "unknown") -> list[dict[str, Any]]:
    """批量标准化；单条非 dict 时按空 dict 处理。"""
    if not isinstance(records, list):
        return []
    out: list[dict[str, Any]] = []
    for item in records:
        if not isinstance(item, dict):
            item = {}
        out.append(normalize_house_record(item, source=source))
    return out

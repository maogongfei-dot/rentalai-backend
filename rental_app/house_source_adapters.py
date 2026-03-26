"""
Phase A3：多来源数据清洗层（source adapter）→ 中间结构 → normalize_house_record → canonical。
与 normalize 分工：本模块侧重来源字段别名、容错与默认值；canonical 侧重统一 schema。
"""

from __future__ import annotations

import copy
import re
from typing import Any, Callable

from house_canonical import normalize_house_record

# ---------------------------------------------------------------------------
# 基础容错：类型转换与默认值（来源兼容）
# ---------------------------------------------------------------------------


def _ensure_dict(raw: Any) -> dict[str, Any]:
    return raw if isinstance(raw, dict) else {}


def _str(v: Any, default: str | None = None) -> str | None:
    if v is None:
        return default
    s = str(v).strip()
    return s if s else default


def _to_float(v: Any) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = re.sub(r"[^\d.\-]", "", v.replace(",", "").replace("£", ""))
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _to_int(v: Any) -> int | None:
    f = _to_float(v)
    if f is None:
        return None
    try:
        return int(f)
    except (TypeError, ValueError):
        return None


def _to_bool(v: Any) -> bool | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        if v == 1:
            return True
        if v == 0:
            return False
        return None
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("yes", "true", "1", "y", "included"):
            return True
        if s in ("no", "false", "0", "n", "excluded"):
            return False
    return None


def _first(d: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if k in d and d[k] is not None:
            if isinstance(d[k], str) and not str(d[k]).strip():
                continue
            return d[k]
    return None


# ---------------------------------------------------------------------------
# 各来源字段映射 → 接近 ListingSchema / normalize 别名的中间 dict
# ---------------------------------------------------------------------------


def clean_rightmove_style_record(raw: dict[str, Any]) -> dict[str, Any]:
    """Rightmove 风格：id / price_pcm / display_address / property_sub_type 等。"""
    r = _ensure_dict(raw)
    lid = _str(_first(r, "listing_id", "id", "property_id"))
    rent = _to_float(_first(r, "price_pcm", "rent_pcm", "rent", "price"))
    title = _str(_first(r, "title", "summary")) or _str(r.get("display_address")) or "Untitled listing"
    addr = _str(r.get("display_address")) or _str(r.get("address"))
    out: dict[str, Any] = {
        "listing_id": lid or "rm-%s" % (hash(str(r)) % 10_000_000),
        "source_url": _str(_first(r, "property_url", "url", "link")),
        "title": title[:500],
        "address": addr,
        "rent_pcm": rent,
        "bedrooms": _to_float(r.get("bedrooms")),
        "bathrooms": _to_float(r.get("bathrooms")),
        "property_type": _str(r.get("property_sub_type")) or _str(r.get("letting_type")),
        "postcode": _str(r.get("postcode")),
        "summary": _str(r.get("summary")),
        "furnished": _infer_furnished(_str(r.get("furnished_type"))),
        "city": _str(_first(r, "city", "town")),
        "area_name": _str(r.get("area")),
    }
    loc = r.get("location")
    if isinstance(loc, dict):
        out.setdefault("city", _str(loc.get("city")))
        out.setdefault("postcode", out.get("postcode") or _str(loc.get("postcode")))
    return {k: v for k, v in out.items() if v is not None}


def _infer_furnished(s: str | None) -> bool | None:
    if not s:
        return None
    sl = s.lower()
    if "furnish" in sl and "un" not in sl[:3]:
        return True
    if "unfurnish" in sl or "unfurnished" in sl:
        return False
    return None


def clean_zoopla_style_record(raw: dict[str, Any]) -> dict[str, Any]:
    """Zoopla 风格：num_bedrooms / price / listing_url / category 等。"""
    r = _ensure_dict(raw)
    lid = _str(_first(r, "listing_id", "listingUrn", "id"))
    rent = _to_float(_first(r, "price", "rent_pcm", "rent"))
    title = _str(_first(r, "title", "heading")) or _str(r.get("address")) or "Untitled listing"
    out: dict[str, Any] = {
        "listing_id": lid or "zp-%s" % (abs(hash(str(r))) % 10_000_000),
        "source_url": _str(_first(r, "listing_url", "url", "link")),
        "title": title[:500],
        "address": _str(r.get("address")),
        "rent_pcm": rent,
        "bedrooms": _to_float(_first(r, "num_bedrooms", "bedrooms", "beds")),
        "bathrooms": _to_float(_first(r, "num_bathrooms", "bathrooms")),
        "property_type": _str(r.get("category")),
        "postcode": _str(r.get("postcode")),
        "summary": _str(r.get("description")),
        "furnished": _infer_furnished(_str(r.get("furnished_state"))),
        "city": _str(r.get("city")),
        "area_name": _str(r.get("area")),
    }
    if r.get("featured") is not None:
        out["notes"] = "featured=%s" % r.get("featured")
    return {k: v for k, v in out.items() if v is not None}


def clean_openrent_style_record(raw: dict[str, Any]) -> dict[str, Any]:
    """OpenRent 风格：rent / bills_included / area_name / suitable_for_couples 等。"""
    r = _ensure_dict(raw)
    lid = _str(_first(r, "listing_id", "id", "property_id"))
    rent = _to_float(_first(r, "rent", "rent_pcm", "price"))
    title = _str(r.get("title")) or _str(r.get("area_name")) or "OpenRent listing"
    out: dict[str, Any] = {
        "listing_id": lid or "or-%s" % (abs(hash(str(r))) % 10_000_000),
        "source_url": _str(_first(r, "url", "link")),
        "title": title[:500],
        "address": _str(r.get("address_text")),
        "rent_pcm": rent,
        "bedrooms": _to_float(_first(r, "bedrooms", "beds")),
        "bathrooms": _to_float(r.get("bathrooms")),
        "property_type": _str(r.get("property_type")),
        "postcode": _str(r.get("postcode")),
        "bills_included": _to_bool(r.get("bills_included")),
        "deposit": _to_float(_first(r, "deposit_amount", "deposit")),
        "summary": _str(r.get("title")),
        "available_from": _str(r.get("availability")),
        "area_name": _str(r.get("area_name")),
        "city": _str(r.get("city")),
    }
    sc = r.get("suitable_for_couples")
    if sc is not None:
        out["couple_friendly"] = _to_bool(sc)
    return {k: v for k, v in out.items() if v is not None}


def clean_generic_record(raw: dict[str, Any]) -> dict[str, Any]:
    """generic_json：字段混乱时尽量映射到常见别名；无法识别则原样保留关键键。"""
    r = _ensure_dict(raw)
    rent = _to_float(_first(r, "rent_pcm", "rent", "price", "monthly_rent", "price_pcm"))
    out: dict[str, Any] = {
        "listing_id": _str(_first(r, "listing_id", "id", "external_id")),
        "source_url": _str(_first(r, "source_url", "url", "link", "listing_url")),
        "title": _str(_first(r, "listing_title", "title", "name", "heading")),
        "address": _str(_first(r, "address_text", "address", "full_address")),
        "rent_pcm": rent,
        "bedrooms": _to_float(_first(r, "bedrooms", "beds", "bed", "num_bedrooms")),
        "bathrooms": _to_float(_first(r, "bathrooms", "baths", "num_bathrooms")),
        "property_type": _str(_first(r, "property_type", "type", "category")),
        "postcode": _str(_first(r, "postcode", "post_code")),
        "city": _str(_first(r, "city", "city_name", "town")),
        "area_name": _str(_first(r, "area", "area_name", "neighbourhood")),
        "bills_included": _to_bool(_first(r, "bills_included", "bills", "bill_included")),
        "deposit": _to_float(_first(r, "deposit", "deposit_amount")),
        "summary": _str(_first(r, "summary", "description", "notes", "notes_text")),
        "commute_minutes": _to_int(r.get("commute_minutes")),
        "furnished": _to_bool(r.get("furnished")),
    }
    return {k: v for k, v in out.items() if v is not None}


# ---------------------------------------------------------------------------
# source adapter 分发逻辑
# ---------------------------------------------------------------------------

_CLEANERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "rightmove_style": clean_rightmove_style_record,
    "rightmove": clean_rightmove_style_record,
    "sample_rightmove_style": clean_rightmove_style_record,
    "zoopla_style": clean_zoopla_style_record,
    "zoopla": clean_zoopla_style_record,
    "sample_zoopla_style": clean_zoopla_style_record,
    "openrent_style": clean_openrent_style_record,
    "openrent": clean_openrent_style_record,
    "sample_openrent_style": clean_openrent_style_record,
    "generic_json_style": clean_generic_record,
    "generic": clean_generic_record,
    "unknown": clean_generic_record,
}


def resolve_cleaner_key(source: str) -> str:
    """将任意 source 字符串映射到 CLEANERS 键；未识别则 generic。"""
    s = (source or "").strip().lower().replace("-", "_")
    if not s:
        return "generic_json_style"
    if s in _CLEANERS:
        return s
    if "rightmove" in s:
        return "rightmove_style"
    if "zoopla" in s:
        return "zoopla_style"
    if "openrent" in s:
        return "openrent_style"
    if "generic" in s:
        return "generic_json_style"
    return "generic_json_style"


def clean_house_record_by_source(raw: dict[str, Any], source: str) -> dict[str, Any]:
    """仅做来源清洗，返回中间 dict（再交给 normalize_house_record）。"""
    r = _ensure_dict(raw)
    key = resolve_cleaner_key(source)
    fn = _CLEANERS.get(key, clean_generic_record)
    try:
        mid = fn(r)
    except Exception:
        mid = clean_generic_record(r)
    if not isinstance(mid, dict):
        mid = {}
    # 保留原始行内 source（若清洗未写）
    src_out = _str(r.get("source")) or source
    if src_out:
        mid.setdefault("source", src_out)
    return mid


def clean_and_normalize_house_record(raw: dict[str, Any], source: str = "unknown") -> dict[str, Any]:
    """
    两段式流程：clean_* → normalize_house_record → canonical。
    """
    r = _ensure_dict(raw)
    src = _str(r.get("source")) or source or "unknown"
    mid = clean_house_record_by_source(r, src)
    merged = copy.deepcopy(mid)
    # 清洗未覆盖的字段从原始补齐（避免丢字段）
    for k, v in r.items():
        if k not in merged and v is not None:
            merged[k] = v
    merged.setdefault("source", src)
    return normalize_house_record(merged, source=str(merged.get("source") or src))


def clean_and_normalize_house_records(
    records: list[dict[str, Any]],
    source: str | None = None,
) -> list[dict[str, Any]]:
    """
    批量清洗 + canonical；若 source 为 None，则每行使用 record['source']。
    """
    if not isinstance(records, list):
        return []
    out: list[dict[str, Any]] = []
    for item in records:
        if not isinstance(item, dict):
            continue
        src = source if source is not None else str(item.get("source") or "unknown")
        out.append(clean_and_normalize_house_record(item, source=src))
    return out

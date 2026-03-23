# P3 Phase2: 统一标准化入口 — 外部 dict → ListingSchema（无抓取、无 DB）
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Callable

from data.schema.listing_schema import ListingSchema, convert_listing_schema_to_analyze_payload


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _first(data: dict, *keys: str) -> Any:
    """取第一个存在且非空的键值。"""
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
        s = value.strip().lower()
        if not s:
            return None
        s = s.replace("£", "").replace(",", " ")
        s = s.replace("pcm", "").replace("per month", "").replace("pm", "")
        s = re.sub(r"[^\d.\-]", "", s)
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
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            return int(float(s))
        except ValueError:
            return None
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
        if s in ("yes", "true", "1", "y", "included", "include"):
            return True
        if s in ("no", "false", "0", "n", "excluded", "not included"):
            return False
        return None
    return None


def _clean_string(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _clean_postcode(value: Any) -> str | None:
    s = _clean_string(value)
    if not s:
        return None
    return s.upper()


def _clean_string_list(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        parts = [p.strip() for p in value.split(",") if p.strip()]
        return parts if parts else None
    if isinstance(value, list):
        out: list[str] = []
        for x in value:
            cs = _clean_string(x)
            if cs:
                out.append(cs)
        return out if out else None
    return None


def _resolve_source(explicit: str | None, data: dict) -> str:
    s = explicit if explicit is not None else data.get("source")
    if isinstance(s, str):
        s = s.strip().lower()
        if s in ("manual", "api", "rightmove", "zoopla", "unknown", "manual_mock"):
            return s
    return "unknown"


def _base_alias_map(data: dict) -> dict[str, Any]:
    """
    将常见别名映射到 ListingSchema 字段名。
    不含 source / normalized_at / raw_data（由入口统一写入）。
    """
    m: dict[str, Any] = {}

    rf = _to_float(_first(data, "rent_pcm", "rent", "price", "monthly_rent"))
    if rf is not None:
        m["rent_pcm"] = rf

    dep = _to_float(_first(data, "deposit", "deposit_amount"))
    if dep is not None:
        m["deposit"] = dep

    bd = _to_float(_first(data, "bedrooms", "bedroom", "beds", "bed"))
    if bd is not None:
        m["bedrooms"] = bd

    bt = _to_float(_first(data, "bathrooms", "bathroom", "bath"))
    if bt is not None:
        m["bathrooms"] = bt

    url = _clean_string(_first(data, "source_url", "url", "link", "listing_url"))
    if url:
        m["source_url"] = url

    pc = _clean_postcode(_first(data, "postcode", "post_code"))
    if pc:
        m["postcode"] = pc

    lat = _to_float(_first(data, "lat", "latitude"))
    if lat is not None:
        m["lat"] = lat

    lng = _to_float(_first(data, "lng", "lon", "longitude"))
    if lng is not None:
        m["lng"] = lng

    title = _clean_string(_first(data, "title", "listing_title"))
    if title:
        m["title"] = title

    addr = _clean_string(_first(data, "address", "full_address"))
    if addr:
        m["address"] = addr

    lid = _clean_string(_first(data, "listing_id", "id", "external_id"))
    if lid:
        m["listing_id"] = lid

    ptype = _clean_string(_first(data, "property_type", "type"))
    if ptype:
        m["property_type"] = ptype

    bi = _to_bool(_first(data, "bills_included", "bills", "includes_bills"))
    if bi is not None:
        m["bills_included"] = bi

    fur = _to_bool(_first(data, "furnished", "is_furnished"))
    if fur is not None:
        m["furnished"] = fur

    area = _clean_string(_first(data, "area_name", "area", "areaName"))
    if area:
        m["area_name"] = area

    city = _clean_string(data.get("city"))
    if city:
        m["city"] = city

    cm = _to_int(_first(data, "commute_minutes", "commute", "commute_mins"))
    if cm is not None:
        m["commute_minutes"] = cm

    dm = _to_float(_first(data, "distance_miles", "distance"))
    if dm is not None:
        m["distance_miles"] = dm

    tpd = _to_float(_first(data, "target_postcode_distance_miles"))
    if tpd is not None:
        m["target_postcode_distance_miles"] = tpd

    cti = _to_bool(data.get("council_tax_included"))
    if cti is not None:
        m["council_tax_included"] = cti

    fees = _clean_string_list(data.get("other_fees"))
    if fees:
        m["other_fees"] = fees

    summ = _clean_string(_first(data, "summary", "description"))
    if summ:
        m["summary"] = summ

    af = _clean_string(data.get("available_from"))
    if af:
        m["available_from"] = af

    mn = _to_int(data.get("min_tenancy_months"))
    if mn is not None:
        m["min_tenancy_months"] = mn

    mx = _to_int(data.get("max_tenancy_months"))
    if mx is not None:
        m["max_tenancy_months"] = mx

    sa = _clean_string(data.get("scraped_at"))
    if sa:
        m["scraped_at"] = sa

    return m


def _normalize_manual_payload(data: dict) -> dict[str, Any]:
    return _base_alias_map(data)


def _normalize_api_payload(data: dict) -> dict[str, Any]:
    """与 manual 共用别名；API 常已接近 web 表单字段名。"""
    return _base_alias_map(data)


def _normalize_rightmove_payload(data: dict) -> dict[str, Any]:
    """模拟 Rightmove 风格扁平 dict 的字段入口（非爬虫）。"""
    m = _base_alias_map(data)
    if not m.get("address"):
        da = _clean_string(_first(data, "displayAddress"))
        if da:
            m["address"] = da
    if not m.get("listing_id"):
        rid = _clean_string(_first(data, "listingId", "propertyId"))
        if rid:
            m["listing_id"] = rid
    return m


def _normalize_zoopla_payload(data: dict) -> dict[str, Any]:
    """模拟 Zoopla 风格扁平 dict 的字段入口（非爬虫）。"""
    m = _base_alias_map(data)
    if not m.get("listing_id"):
        zid = _clean_string(_first(data, "listingId", "listingUrn"))
        if zid:
            m["listing_id"] = zid
    return m


def _normalize_unknown_payload(data: dict) -> dict[str, Any]:
    return _base_alias_map(data)


_DISPATCH: dict[str, Callable[[dict], dict[str, Any]]] = {
    "manual": _normalize_manual_payload,
    "manual_mock": _normalize_manual_payload,
    "api": _normalize_api_payload,
    "rightmove": _normalize_rightmove_payload,
    "zoopla": _normalize_zoopla_payload,
    "unknown": _normalize_unknown_payload,
}


def normalize_listing_payload(data: dict, source: str | None = None) -> ListingSchema:
    """
    单条外部 dict → ListingSchema。
    source 优先参数，其次 data['source']，否则 unknown。
    异常时返回最小合法 ListingSchema（含 raw_data）。
    """
    raw: dict[str, Any] = dict(data) if isinstance(data, dict) else {}
    try:
        src = _resolve_source(source, raw)
        fn = _DISPATCH.get(src, _normalize_unknown_payload)
        canonical = fn(raw)
        canonical["source"] = src
        canonical["raw_data"] = raw
        canonical["normalized_at"] = _utc_now_iso()
        return ListingSchema.from_dict(canonical)
    except Exception:
        return ListingSchema(
            source=_resolve_source(source, raw),
            normalized_at=_utc_now_iso(),
            raw_data=raw,
        )


def normalize_listing_batch(items: list[dict], source: str | None = None) -> list[ListingSchema]:
    """
    批量标准化；单条异常不拖垮整批，降级为最小 ListingSchema。
    """
    if not isinstance(items, list):
        return []
    out: list[ListingSchema] = []
    for item in items:
        try:
            if not isinstance(item, dict):
                item = {}
            out.append(normalize_listing_payload(item, source=source))
        except Exception:
            raw = item if isinstance(item, dict) else {}
            out.append(
                ListingSchema(
                    source=_resolve_source(source, raw),
                    normalized_at=_utc_now_iso(),
                    raw_data=raw,
                )
            )
    return out


def to_analyze_payload(
    listing: ListingSchema,
    *,
    budget: float | None = None,
    target_postcode: str | None = None,
) -> dict[str, Any]:
    """
    数据层：ListingSchema → 当前 /analyze 单条 properties 兼容 dict。
    不修改 API 路由；内部委托 Phase1 的 convert_listing_schema_to_analyze_payload。
    """
    return convert_listing_schema_to_analyze_payload(
        listing, budget=budget, target_postcode=target_postcode
    )


# ---------- 最小文档化示例（无独立 tests 时可读此处）----------
_EXAMPLES_DOC = """
示例（在 rental_app 目录下）:

>>> from data.normalizer.listing_normalizer import normalize_listing_payload, to_analyze_payload
>>> normalize_listing_payload({"rent": 1200, "bedrooms": 2, "source": "manual"}, source=None).rent_pcm
1200.0
>>> normalize_listing_payload({"price": "£1,250 pcm", "post_code": "e1 6an"}, source="api").postcode
'E1 6AN'
"""

if __name__ == "__main__":
    print(_EXAMPLES_DOC)

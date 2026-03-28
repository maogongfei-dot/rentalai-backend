"""
Phase D4：抓取结果清洗与整理层（Zoopla / Playwright 等 raw records）。

raw scraped records → clean_scraped_listings → normalize_house_records → recommendation-ready canonical。

不编造业务事实，仅做去重、字段清洗、结构默认值与最低质量门槛。
"""

from __future__ import annotations

import copy
import logging
import re
from typing import Any

from house_canonical import normalize_house_records

logger = logging.getLogger(__name__)

# 最近一次 clean_scraped_listings 的统计，供 loader / summary 使用
_last_scrape_clean_stats: dict[str, Any] = {}

# --- rent：支持 "£1,250 pcm" / "1250" / "1,500" 等 → float ---
_RENT_PCM = re.compile(
    r"£\s*([\d,]+(?:\.\d+)?)\s*(?:pcm|p\.c\.m\.|per\s*month|/month)?",
    re.I,
)
_RENT_POUND = re.compile(r"£\s*([\d,]+(?:\.\d+)?)")
_RE_BEDS_TEXT = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:bed|beds|bedroom|bedrooms)\b",
    re.I,
)
_RE_STUDIO = re.compile(r"\bstudio\b", re.I)
def get_last_scrape_clean_stats() -> dict[str, Any]:
    """返回最近一次 ``clean_scraped_listings`` 的统计副本（无则空 dict）。"""
    return dict(_last_scrape_clean_stats)


def _to_float_loose(v: Any) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        m = _RENT_PCM.search(s) or _RENT_POUND.search(s)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                pass
        digits = re.sub(r"[^\d.\-]", "", s.replace(",", ""))
        if not digits:
            return None
        try:
            return float(digits)
        except ValueError:
            return None
    return None


def _clean_rent_value(v: Any) -> float | None:
    # rent 清洗：£/pcm 文案、纯数字、千分位逗号 → 正浮点数
    """rent / price / rent_pcm 统一为 pcm 浮点数（与 Zoopla 展示一致）。"""
    f = _to_float_loose(v)
    if f is None or f <= 0:
        return None
    return f


def _clean_bedrooms_value(v: Any) -> float | None:
    # bedrooms 清洗：整型/字符串 "N bed(s)" / studio → 数值
    """支持数字、"1 bed"、"2 bedrooms"、studio → 0。"""
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        if _RE_STUDIO.search(s):
            return 0.0
        m = _RE_BEDS_TEXT.search(s)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
        digits = re.sub(r"[^\d.\-]", "", s)
        if digits:
            try:
                return float(digits)
            except ValueError:
                return None
    return None


def _clean_postcode_str(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    s = " ".join(s.split())
    return s.upper()


def _clean_city_area_str(v: Any) -> str | None:
    if v is None:
        return None
    s = " ".join(str(v).split())
    if not s:
        return None
    # 轻量：首字母大写风格（英文地名）；中文等保持原样
    return s.title() if s.isascii() else s


def _clean_address_text(v: Any) -> str | None:
    if v is None:
        return None
    s = " ".join(str(v).split())
    return s if s else None


def _truthy_bool(v: Any) -> bool | None:
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
        if s in ("yes", "true", "1", "y", "included", "包"):
            return True
        if s in ("no", "false", "0", "n", "excluded", "unknown", "n/a", ""):
            return False if s in ("no", "false", "0", "n", "excluded") else None
        # 非标准字符串视为未知，避免把垃圾送进推荐
        if len(s) > 64:
            return None
        return None
    return None


def _features_to_list(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str):
        parts = re.split(r"[,;|\n]+", v)
        return [p.strip() for p in parts if p.strip()]
    return []


def _first(d: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if k in d and d[k] is not None:
            if isinstance(d[k], str) and not str(d[k]).strip():
                continue
            return d[k]
    return None


def enrich_scraped_listing_defaults(record: dict[str, Any], source: str = "zoopla") -> dict[str, Any]:
    """
    仅补结构默认值，不编造房源事实。
    """
    r = copy.deepcopy(record) if isinstance(record, dict) else {}
    if source and not (r.get("source") or "").strip():
        r["source"] = source
    if r.get("features") is None:
        r["features"] = []
    if r.get("notes") is None:
        r["notes"] = ""
    for k in ("bills", "furnished", "couple_friendly", "near_station"):
        if k not in r:
            r[k] = None
    if r.get("scores") is None:
        r["scores"] = {}
    if "final_score" not in r:
        r["final_score"] = None
    return r


def is_valid_scraped_listing(record: dict[str, Any]) -> bool:
    """
    最低质量门槛：标题 + 可解析租金 + (listing_id 或 source_url)；缺一视为垃圾行。
    """
    if not isinstance(record, dict):
        return False
    title = _first(record, "listing_title", "title", "heading", "name")
    if not title or not str(title).strip():
        return False
    rent = _clean_rent_value(_first(record, "rent", "rent_pcm", "price", "monthly_rent", "price_pcm"))
    if rent is None:
        return False
    lid = _first(record, "listing_id", "listingUrn", "id", "external_id")
    url = _first(record, "source_url", "listing_url", "url", "link", "property_url")
    has_id = lid is not None and str(lid).strip()
    has_url = url is not None and str(url).strip()
    return bool(has_id or has_url)


def _normalize_url_key(url: Any) -> str:
    if not url:
        return ""
    return str(url).strip().lower().rstrip("/")


def _normalize_listing_id_key(lid: Any) -> str:
    if lid is None:
        return ""
    return str(lid).strip()


def _title_postcode_rent_key(record: dict[str, Any]) -> tuple[str, str, str] | None:
    """去重用：标题 + postcode + 租金；无 postcode 时不参与此键（避免误合并）。"""
    t = _first(record, "listing_title", "title", "heading") or ""
    t_norm = re.sub(r"\s+", " ", str(t).strip().lower())
    pc = _clean_postcode_str(_first(record, "postcode", "post_code")) or ""
    if not pc:
        return None
    rent = _clean_rent_value(_first(record, "rent", "rent_pcm", "price", "monthly_rent"))
    r_key = f"{rent:.2f}" if rent is not None else ""
    if not r_key:
        return None
    return (t_norm[:200], pc, r_key)


def _clean_scraped_fields(record: dict[str, Any]) -> dict[str, Any]:
    """单条字段清洗：租金、卧室、地址类、布尔、features。"""
    r = copy.deepcopy(record)

    rent = _clean_rent_value(_first(r, "rent", "rent_pcm", "price", "monthly_rent", "price_pcm"))
    if rent is not None:
        r["rent"] = rent
        r["rent_pcm"] = rent

    beds = _clean_bedrooms_value(_first(r, "bedrooms", "beds", "bed", "num_bedrooms"))
    if beds is not None:
        r["bedrooms"] = beds

    pc = _clean_postcode_str(_first(r, "postcode", "post_code"))
    if pc:
        r["postcode"] = pc

    city = _clean_city_area_str(_first(r, "city", "town"))
    if city:
        r["city"] = city

    area = _clean_city_area_str(_first(r, "area", "area_name", "neighbourhood"))
    if area:
        r["area"] = area
        r["area_name"] = area

    addr = _clean_address_text(_first(r, "address_text", "address", "full_address", "display_address"))
    if addr:
        r["address_text"] = addr
        r["address"] = addr

    for k in ("bills", "bills_included", "bill_included"):
        if k in r:
            b = _truthy_bool(r.get(k))
            if b is not None or k == "bills":
                r["bills"] = b
            break

    for k in ("furnished", "is_furnished", "furnished_state"):
        if k in r:
            r["furnished"] = _truthy_bool(r.get(k))
            break

    for k in ("near_station", "close_to_station", "walk_to_station"):
        if k in r:
            r["near_station"] = _truthy_bool(r.get(k))
            break

    for k in ("couple_friendly", "couples_ok", "couple_ok"):
        if k in r:
            r["couple_friendly"] = _truthy_bool(r.get(k))
            break

    r["features"] = _features_to_list(r.get("features"))
    return r


def clean_scraped_listings(records: list[dict[str, Any]], source: str = "zoopla") -> list[dict[str, Any]]:
    """
    抓取原始列表 → 默认值 → 字段清洗 → 质量过滤 → 去重（listing_id / URL / 标题+邮编+租金）。

    返回仍为非 canonical 的中间 dict，供 ``normalize_house_records`` 使用。
    """
    global _last_scrape_clean_stats

    raw_count = len(records) if isinstance(records, list) else 0
    dropped_non_dict = 0
    staging: list[dict[str, Any]] = []

    for item in records or []:
        if not isinstance(item, dict):
            dropped_non_dict += 1
            continue
        enriched = enrich_scraped_listing_defaults(item, source=source)
        cleaned = _clean_scraped_fields(enriched)
        staging.append(cleaned)

    dropped_invalid = sum(1 for r in staging if not is_valid_scraped_listing(r))
    valid_only = [r for r in staging if is_valid_scraped_listing(r)]

    # 去重逻辑：先 listing_id → source_url → (标题+邮编+租金)；第三键仅当邮编与租金均可解析时参与
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    seen_tpr: set[tuple[str, str, str]] = set()
    deduped: list[dict[str, Any]] = []
    deduped_count = 0

    for r in valid_only:
        ikey = _normalize_listing_id_key(_first(r, "listing_id", "listingUrn", "id", "external_id"))
        ukey = _normalize_url_key(_first(r, "source_url", "listing_url", "url", "link", "property_url"))
        tpr = _title_postcode_rent_key(r)

        skip = False
        if ikey and ikey in seen_ids:
            skip = True
        elif ukey and ukey in seen_urls:
            skip = True
        elif tpr is not None and tpr in seen_tpr:
            skip = True

        if skip:
            deduped_count += 1
            continue

        if ikey:
            seen_ids.add(ikey)
        if ukey:
            seen_urls.add(ukey)
        if tpr is not None:
            seen_tpr.add(tpr)
        deduped.append(r)

    cleaned_count = len(deduped)
    dropped_count = dropped_non_dict + dropped_invalid

    _last_scrape_clean_stats = {
        "raw_count": raw_count,
        "cleaned_count": cleaned_count,
        "dropped_count": dropped_count,
        "deduped_count": deduped_count,
        "dropped_non_dict": dropped_non_dict,
        "dropped_invalid": dropped_invalid,
    }
    logger.info(
        "scraped_listing_cleaner: raw=%s cleaned=%s dropped=%s deduped=%s",
        raw_count,
        cleaned_count,
        dropped_count,
        deduped_count,
    )

    return deduped


def prepare_scraped_listings_for_recommendation(
    records: list[dict[str, Any]],
    source: str = "zoopla",
) -> list[dict[str, Any]]:
    """
    接入点：clean_scraped_listings → normalize_house_records → canonical，供推荐引擎使用。

    与 ``clean_and_normalize_house_record`` 并列；本路径专用于抓取结果，含去重与抓取层清洗。
    """
    cleaned = clean_scraped_listings(records, source=source)
    return normalize_house_records(cleaned, source=source)


__all__ = [
    "clean_scraped_listings",
    "enrich_scraped_listing_defaults",
    "get_last_scrape_clean_stats",
    "is_valid_scraped_listing",
    "prepare_scraped_listings_for_recommendation",
]

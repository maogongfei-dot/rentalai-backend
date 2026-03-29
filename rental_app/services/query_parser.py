"""
Phase D10：自然语言 → 结构化查询（规则版，可替换为 LLM parser）。
"""

from __future__ import annotations

import re
from typing import Any

# --- 轻量中文地名映射（可扩展） ---
_CN_PLACES: dict[str, str] = {
    "伦敦": "London",
    "曼彻斯特": "Manchester",
    "伯明翰": "Birmingham",
    "诺丁汉": "Nottingham",
    "利物浦": "Liverpool",
    "爱丁堡": "Edinburgh",
    "格拉斯哥": "Glasgow",
}

# 伦敦子区域关键词 → area 提示
_LONDON_AREA_HINTS: list[tuple[str, str]] = [
    ("西北区", "North West London"),
    ("西北", "North West London"),
    ("西南区", "South West London"),
    ("西南", "South West London"),
    ("东区", "East London"),
    ("西区", "West London"),
    ("市中心", "Central London"),
]

_UK_POSTCODE_FULL = re.compile(
    r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b",
    re.IGNORECASE,
)
_UK_POSTCODE_OUT = re.compile(
    r"\b([A-Z]{1,2}\d{1,2}[A-Z]?)\b(?![A-Z0-9])",
    re.IGNORECASE,
)

# 英文连续大写开头词串（城市名）
_EN_TITLE_PHRASE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b",
)

# 英国城市/地区：按名称长度降序，先匹配「Milton Keynes」再匹配短名，避免误取 Manchester / 单字 Milton
_UK_CITIES_ORDERED: list[str] = [
    "Milton Keynes",
    "Greater London",
    "London",
    "Manchester",
    "Birmingham",
    "Liverpool",
    "Leeds",
    "Sheffield",
    "Bristol",
    "Edinburgh",
    "Glasgow",
    "Oxford",
    "Cambridge",
    "Reading",
    "Brighton",
    "Southampton",
    "Nottingham",
    "Leicester",
    "Coventry",
    "Cardiff",
    "Belfast",
    "Newcastle",
    "Fulham",
    "Croydon",
]


def _safe_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _to_float(v: Any) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_int(v: Any) -> int | None:
    f = _to_float(v)
    if f is None:
        return None
    try:
        return int(round(f))
    except (TypeError, ValueError):
        return None


def _digits_in_range(s: str) -> list[float]:
    """提取看起来像月租的数字（3–5 位为主）。"""
    out: list[float] = []
    for m in re.finditer(r"\b(\d{3,5})\b", s):
        try:
            n = float(m.group(1))
            if 200 <= n <= 20000:
                out.append(n)
        except ValueError:
            continue
    return out


def _extract_postcode(text: str) -> tuple[str | None, str]:
    """返回 (normalized_postcode, text_with_postcode_removed)。"""
    t = text
    m = _UK_POSTCODE_FULL.search(t)
    if m:
        pc = re.sub(r"\s+", " ", m.group(1).strip()).upper()
        t = t[: m.start()] + " " + t[m.end() :]
        return pc, t

    for m in _UK_POSTCODE_OUT.finditer(t):
        frag = m.group(1).upper()
        if len(frag) <= 4 and re.match(r"^[A-Z]{1,2}\d", frag):
            t = t[: m.start()] + " " + t[m.end() :]
            return frag, t
    return None, t


def _extract_bedrooms(text: str) -> tuple[int | None, int | None, str]:
    """(min_bed, max_bed, remaining_text)。"""
    t = text
    min_b: int | None = None
    max_b: int | None = None

    def set_pair(a: int | None, b: int | None) -> None:
        nonlocal min_b, max_b
        if a is not None:
            min_b = a if min_b is None else min(min_b, a)
        if b is not None:
            max_b = b if max_b is None else max(max_b, b)

    # 2到3居 / 2-3室 / 2至3 bed
    for m in re.finditer(
        r"(\d)\s*(?:到|至|[-~])\s*(\d)\s*(?:居|室|房|bed(?:room)?s?)?",
        t,
        re.IGNORECASE,
    ):
        a, b = int(m.group(1)), int(m.group(2))
        lo, hi = min(a, b), max(a, b)
        set_pair(lo, hi)
        t = t.replace(m.group(0), " ", 1)

    # 中文居室（长短语优先）
    cn_phrases = [
        ("两居室", 2),
        ("二居室", 2),
        ("三居室", 3),
        ("一居室", 1),
        ("两室", 2),
        ("二室", 2),
        ("三室", 3),
        ("一室", 1),
        ("两居", 2),
        ("二居", 2),
        ("三居", 3),
        ("一居", 1),
    ]
    for phrase, n in cn_phrases:
        if phrase in t:
            set_pair(n, n)
            t = t.replace(phrase, " ", 1)
            break

    # 显式：一居 / 二居 / 三居 / 1居 / 2bed
    single_patterns = [
        (r"(?:一|1)\s*(?:居|室|bed(?:room)?s?)", 1),
        (r"(?:二|两|2)\s*(?:居|室|bed(?:room)?s?)", 2),
        (r"(?:三|3)\s*(?:居|室|bed(?:room)?s?)", 3),
        (r"(?:四|4)\s*(?:居|室|bed(?:room)?s?)", 4),
        (r"\b1\s*bed(?:room)?s?\b", 1),
        (r"\b2\s*bed(?:room)?s?\b", 2),
        (r"\b3\s*bed(?:room)?s?\b", 3),
        (r"\bone\s*bed\b", 1),
        (r"\btwo\s*bed\b", 2),
    ]
    for pat, n in single_patterns:
        m = re.search(pat, t, re.IGNORECASE)
        if m:
            set_pair(n, n)
            t = t[: m.start()] + " " + t[m.end() :]

    # 2-bed / 3-bed（连字符）
    m = re.search(r"\b(\d)\s*[-]\s*bed(?:room)?s?\b", t, re.IGNORECASE)
    if m:
        n = int(m.group(1))
        set_pair(n, n)
        t = t[: m.start()] + " " + t[m.end() :]

    if min_b is not None and max_b is None:
        max_b = min_b
    if max_b is not None and min_b is None:
        min_b = max_b

    return min_b, max_b, t


def _extract_prices(text: str) -> tuple[float | None, float | None, float | None, str]:
    """min_price, max_price, target_price, remaining."""
    t = text
    min_p: float | None = None
    max_p: float | None = None
    target_p: float | None = None

    def grab_num(s: str) -> float | None:
        m = re.search(r"(\d{3,5})", s)
        if not m:
            return None
        try:
            v = float(m.group(1))
            return v if 200 <= v <= 20000 else None
        except ValueError:
            return None

    # X 到 Y / X to Y（英文）
    for m in re.finditer(
        r"(?:for\s+)?(\d{3,5})\s*(?:到|至|[-~]|to)\s*(\d{3,5})",
        t,
        re.IGNORECASE,
    ):
        a, b = float(m.group(1)), float(m.group(2))
        lo, hi = min(a, b), max(a, b)
        min_p, max_p = lo, hi
        t = t.replace(m.group(0), " ", 1)
        break

    if min_p is None:
        for m in re.finditer(r"(?:以下|以内|不超过|under|below|max)\s*[：:£]?\s*(\d{3,5})", t, re.IGNORECASE):
            max_p = float(m.group(1))
            t = t.replace(m.group(0), " ", 1)
            break
        for m in re.finditer(r"(\d{3,5})\s*(?:以下|以内|不超过)(?!\s*到)", t):
            max_p = float(m.group(1))
            t = t.replace(m.group(0), " ", 1)
            break

    if min_p is None and max_p is None:
        for m in re.finditer(r"(?:以上|至少|from|above)\s*[：:£]?\s*(\d{3,5})", t, re.IGNORECASE):
            min_p = float(m.group(1))
            t = t.replace(m.group(0), " ", 1)
            break

    if target_p is None:
        for m in re.finditer(
            r"(?:预算|budget)\s*(\d{3,5})\s*(?:左右|大概|大约|around|approx)",
            t,
            re.IGNORECASE,
        ):
            target_p = float(m.group(1))
            t = t.replace(m.group(0), " ", 1)
            break
    if target_p is None:
        for m in re.finditer(
            r"(\d{3,5})\s*(?:左右|大概|大约|around|approx)",
            t,
            re.IGNORECASE,
        ):
            target_p = float(m.group(1))
            t = t.replace(m.group(0), " ", 1)
            break

    return min_p, max_p, target_p, t


def _extract_flags_and_keywords(text: str) -> tuple[dict[str, Any], list[str], str]:
    flags = {
        "cheap_preference": False,
        "safety_preference": False,
        "commute_preference": False,
        "lifestyle_preference": False,
        "image_required": False,
        "furnished_preference": None,
    }
    keywords: list[str] = []
    t = text
    tl = t.lower()

    cheap_hits = ("便宜", "性价比", "划算", "实惠", "cheap", "affordable", "value")
    for h in cheap_hits:
        if h.lower() in tl:
            flags["cheap_preference"] = True
            if h not in keywords:
                keywords.append(h)
            break

    safety_hits = (
        "安全",
        "治安",
        "安静",
        "靠谱",
        "safe",
        "safety",
        "quiet",
        "secure",
        "crime",
    )
    for h in safety_hits:
        if h.lower() in tl:
            flags["safety_preference"] = True
            if h not in keywords:
                keywords.append(h)
            break

    commute_hits = (
        "通勤",
        "地铁",
        "车站",
        "上班",
        "近铁",
        "commute",
        "station",
        "tube",
        "underground",
        "rail",
        "bus",
        "near work",
        "walking distance",
    )
    for h in commute_hits:
        if h.lower() in tl:
            flags["commute_preference"] = True
            if h not in keywords:
                keywords.append(h)
            break

    lifestyle_hits = (
        "生活便利",
        "超市",
        "购物",
        "便利",
        "周边",
        "lifestyle",
        "amenities",
        "shops",
        "cafes",
        "restaurant",
        "gym",
    )
    for h in lifestyle_hits:
        if h.lower() in tl:
            flags["lifestyle_preference"] = True
            if h not in keywords:
                keywords.append(h)
            break

    img_hits = ("最好有图", "有图", "图片", "照片", "带图", "image", "photo", "picture")
    for h in img_hits:
        if h.lower() in tl:
            flags["image_required"] = True
            break

    if re.search(r"带家具| furnished", t, re.IGNORECASE):
        flags["furnished_preference"] = "furnished"
    if re.search(r"不带家具|unfurnished", t, re.IGNORECASE):
        flags["furnished_preference"] = "unfurnished"

    return flags, keywords, t


def _extract_location_name(text: str, raw_for_hints: str) -> tuple[str | None, str | None, list[str]]:
    """location, area, extra keywords。``raw_for_hints`` 用原始句做中文区域识别。"""
    t = re.sub(r"\s+", " ", text).strip()
    raw_h = raw_for_hints or ""
    keywords: list[str] = []
    area: str | None = None
    location: str | None = None

    # 1) 优先匹配完整英国城市名（长名优先），避免「Milton」单独命中或混入其他城市结果
    raw_scan = raw_h.strip()
    for city in _UK_CITIES_ORDERED:
        if len(city) < 3:
            continue
        if re.search(r"(?i)\b" + re.escape(city) + r"\b", raw_scan):
            location = city
            break

    if location is None:
        for cn, en in _CN_PLACES.items():
            if cn in t:
                location = en
                t = t.replace(cn, " ")
                break

    if "伦敦" in raw_h or location == "London":
        if location is None:
            location = "London"
        for cn_hint, en_area in _LONDON_AREA_HINTS:
            if cn_hint in raw_h:
                area = en_area
                keywords.append(cn_hint)
                break

    for m in _EN_TITLE_PHRASE.finditer(t):
        phrase = m.group(1).strip()
        if len(phrase) < 3:
            continue
        skip = {"I Want", "Help Me", "The", "And", "For", "Want", "Bed", "Rent"}
        if phrase in skip:
            continue
        if location is None:
            location = phrase
            t = t.replace(phrase, " ", 1)
            break

    # 剩余片段里再取一段英文地名（第二个短语）
    if location is None:
        for m in _EN_TITLE_PHRASE.finditer(t):
            phrase = m.group(1).strip()
            if len(phrase) >= 4:
                location = phrase
                break

    t = re.sub(r"\s+", " ", t).strip()
    if not location and t:
        # 去掉常见动词后取首段
        t2 = re.sub(
            r"^(我想|我要|帮我|找一下|找|看看|想|租|出租房|附近的|房子)",
            "",
            t,
            flags=re.IGNORECASE,
        )
        t2 = re.sub(r"[^\w\s\u4e00-\u9fff]", " ", t2)
        t2 = re.sub(r"\s+", " ", t2).strip()
        if len(t2) >= 2 and not re.match(r"^\d+$", t2):
            parts = [p for p in t2.split() if len(p) > 1 and not p.isdigit()]
            if parts:
                location = " ".join(parts[:4])

    return location, area, keywords


def parse_user_housing_query(user_text: str) -> dict[str, Any]:
    """
    规则版解析：提取 location / postcode / 价格 / 卧室 / 偏好。
    未识别字段保持 None 或默认值，不抛错。
    """
    raw = _safe_str(user_text)
    raw = raw.replace("，", " ").replace("、", " ")
    if not raw:
        return {
            "raw_text": "",
            "location": None,
            "postcode": None,
            "area": None,
            "min_price": None,
            "max_price": None,
            "target_price": None,
            "min_bedrooms": None,
            "max_bedrooms": None,
            "keywords": [],
            "flags": {
                "cheap_preference": False,
                "safety_preference": False,
                "commute_preference": False,
                "lifestyle_preference": False,
                "image_required": False,
                "furnished_preference": None,
            },
            "intent": "market_search",
        }

    text = raw
    postcode, text = _extract_postcode(text)
    flags, kw_flags, _ = _extract_flags_and_keywords(raw)
    min_p, max_p, target_p, text = _extract_prices(text)
    min_b, max_b, text = _extract_bedrooms(text)

    loc, area, loc_kw = _extract_location_name(text, raw)
    keywords = list(dict.fromkeys(kw_flags + loc_kw))

    # 仅有邮编时，避免把「附近的出租房」等碎片当地名
    if postcode and loc and not re.search(r"[A-Za-z]", str(loc)):
        loc = None

    return {
        "raw_text": raw,
        "location": loc,
        "postcode": postcode,
        "area": area,
        "min_price": min_p,
        "max_price": max_p,
        "target_price": target_p,
        "min_bedrooms": min_b,
        "max_bedrooms": max_b,
        "keywords": keywords,
        "flags": {
            "cheap_preference": bool(flags["cheap_preference"]),
            "safety_preference": bool(flags["safety_preference"]),
            "commute_preference": bool(flags["commute_preference"]),
            "lifestyle_preference": bool(flags["lifestyle_preference"]),
            "image_required": bool(flags["image_required"]),
            "furnished_preference": flags["furnished_preference"],
        },
        "intent": "market_search",
    }


def normalize_search_filters(parsed_query: dict[str, Any]) -> dict[str, Any]:
    """
    将 ``parse_user_housing_query`` 结果标准化为 D6–D9 可用的查询参数。
    """
    if not isinstance(parsed_query, dict):
        parsed_query = {}

    loc = parsed_query.get("location")
    pc = parsed_query.get("postcode")
    area = parsed_query.get("area")

    min_p = _to_float(parsed_query.get("min_price"))
    max_p = _to_float(parsed_query.get("max_price"))
    target_p = _to_float(parsed_query.get("target_price"))

    if target_p is not None and min_p is None and max_p is None:
        band = target_p * 0.15
        min_p = max(0.0, round(target_p - band, 2))
        max_p = round(target_p + band, 2)

    min_b = _to_int(parsed_query.get("min_bedrooms"))
    max_b = _to_int(parsed_query.get("max_bedrooms"))

    flags_in = parsed_query.get("flags") if isinstance(parsed_query.get("flags"), dict) else {}
    cheap = bool(flags_in.get("cheap_preference"))
    safety = bool(flags_in.get("safety_preference"))
    commute = bool(flags_in.get("commute_preference"))
    lifestyle = bool(flags_in.get("lifestyle_preference"))
    image_req = bool(flags_in.get("image_required"))
    furn = flags_in.get("furnished_preference")
    if furn is not None:
        furn = str(furn).strip().lower()
        if furn not in ("furnished", "unfurnished"):
            furn = None

    sort_by: str | None = None
    if cheap:
        sort_by = "price_asc"
    else:
        sort_by = None

    limit = 20
    try:
        lim = parsed_query.get("limit")
        if lim is not None:
            limit = max(1, min(100, int(lim)))
    except (TypeError, ValueError):
        pass

    out: dict[str, Any] = {
        "location": _safe_str(loc) if loc else None,
        "postcode": _safe_str(pc).upper() if pc else None,
        "area": _safe_str(area) if area else None,
        "min_price": min_p,
        "max_price": max_p,
        "min_bedrooms": min_b,
        "max_bedrooms": max_b,
        "sort_by": sort_by,
        "limit": limit,
        "filters": {
            "cheap_preference": cheap,
            "safety_preference": safety,
            "commute_preference": commute,
            "lifestyle_preference": lifestyle,
            "image_required": image_req,
            "furnished_preference": furn,
        },
    }

    if out.get("location") == "":
        out["location"] = None
    if out.get("postcode") == "":
        out["postcode"] = None
    if out.get("area") == "":
        out["area"] = None

    return out


__all__ = [
    "normalize_search_filters",
    "parse_user_housing_query",
]

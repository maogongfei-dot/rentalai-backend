# Phase1 AI 闭环：自然语言 → 结构化字段（rule/regex，无 LLM）
from __future__ import annotations

import re
from typing import Any

# 城市名优先匹配较长名称（避免 Milton 误匹配）
_UK_CITIES_ORDERED = [
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

_POSTCODE_RE = re.compile(
    r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b",
    re.IGNORECASE,
)


def _norm_space(s: str) -> str:
    return " ".join(s.split())


def _extract_budgets(text: str) -> tuple[float | None, float | None]:
    """Return (budget_min, budget_max) if inferable."""
    t = text.lower()
    nums: list[float] = []

    for m in re.finditer(
        r"(?:£\s*)?([\d]{2,5})(?:\s*(?:pcm|per\s*month|/月|镑|磅))?",
        t,
    ):
        try:
            nums.append(float(m.group(1)))
        except ValueError:
            pass

    for m in re.finditer(
        r"(?:预算|budget|under|below|max|no\s*more\s*than|不超过|以内|以下|最多)\s*[：:£]?\s*([\d]{2,5})",
        t,
        re.IGNORECASE,
    ):
        try:
            nums.append(float(m.group(1)))
        except ValueError:
            pass

    if not nums:
        return None, None

    # 单数字 + 「以内」→ max
    if re.search(r"(以内|以下|不超过|at\s*most|under|below|max)", t):
        return None, max(nums)

    if len(nums) >= 2:
        return min(nums), max(nums)

    return None, nums[0]


def _extract_bedrooms(text: str) -> int | None:
    tl = text.lower()
    if re.search(r"\bstudio\b|开间|单间公寓", tl):
        return 0
    if re.search(r"一居室|一室|一房|一卧|1\s*bed|1br|one\s*bed|single\s*bed", tl):
        return 1
    if re.search(r"两居|二居|两房|2\s*bed|2br|two\s*bed", tl):
        return 2
    if re.search(r"三居|三房|3\s*bed|3br", tl):
        return 3
    if re.search(r"四居|4\s*bed|4br|4\+", tl):
        return 4
    return None


def _extract_city(text: str) -> str | None:
    for city in _UK_CITIES_ORDERED:
        if city.lower() in text.lower():
            return city
    return None


def _extract_postcode(text: str) -> str | None:
    m = _POSTCODE_RE.search(text.upper())
    if m:
        return _norm_space(m.group(1).upper())
    return None


def _extract_property_type(text: str) -> str | None:
    tl = text.lower()
    if re.search(r"\bstudio\b|开间", tl):
        return "studio"
    if re.search(r"\bflat\b|\bapartment\b|公寓", tl):
        return "flat"
    if re.search(r"\bhouse\b|别墅|独栋", tl):
        return "house"
    if re.search(r"\broom\b|合租|单间(?!公寓)", tl):
        return "room"
    return None


def parse_user_query(raw: str) -> dict[str, Any]:
    """
    将用户一句需求解析为结构化字段；未识别则 null / 默认。
    """
    if raw is None:
        raw = ""
    raw_user_query = str(raw).strip()
    text = raw_user_query
    low = text.lower()

    budget_min, budget_max = _extract_budgets(text)
    bedrooms = _extract_bedrooms(text)
    city = _extract_city(text)
    postcode = _extract_postcode(text)
    property_type = _extract_property_type(text)

    # area：无显式 city 时尝试从「在 X 区」等截取（轻量）
    area: str | None = None
    m_area = re.search(
        r"(?:在|位于)\s*([A-Za-z][A-Za-z\s\-]{2,40}?)(?:\s+(?:附近|区域|一带)|[，,。])",
        text,
    )
    if m_area and not city:
        area = m_area.group(1).strip()

    bills_included: bool | None = None
    if re.search(
        r"bills?\s*included|包\s*bill|包bill|含bill|包水电|含水电|包费用",
        low,
    ):
        bills_included = True
    elif re.search(r"不包|不含bill|bills?\s*not|excluding\s*bills", low):
        bills_included = False

    furnished = None
    if re.search(r"\bfurnished\b|带家具|精装修|拎包入住", low):
        furnished = True
    elif re.search(r"\bunfurnished\b|不带家具|空房", low):
        furnished = False

    commute_preference = bool(
        re.search(
            r"通勤方便|通勤|上班方便|离工作|离公司近|commute|good\s*transport",
            low,
        )
    )
    near_station = bool(
        re.search(
            r"离车站近|靠近地铁|近车站|近地铁|near\s*(?:the\s*)?station|close\s*to\s*tube|walk(?:ing)?\s*distance\s*to\s*station",
            low,
        )
    )

    couple_friendly = bool(
        re.search(r"情侣|夫妻|couple|双人", low)
    )
    safety_priority = bool(
        re.search(r"安全|治安|安静|safe|safety|quiet", low)
    )

    notes_bits: list[str] = []
    if couple_friendly:
        notes_bits.append("couple")
    if safety_priority:
        notes_bits.append("safety/quiet")
    notes = ", ".join(notes_bits) if notes_bits else None

    return {
        "raw_user_query": raw_user_query,
        "city": city,
        "area": area,
        "postcode": postcode,
        "budget_max": budget_max,
        "budget_min": budget_min,
        "bedrooms": bedrooms,
        "bills_included": bills_included if bills_included else None,
        "furnished": furnished,
        "commute_preference": commute_preference if commute_preference else None,
        "near_station": near_station if near_station else None,
        "couple_friendly": couple_friendly if couple_friendly else None,
        "safety_priority": safety_priority if safety_priority else None,
        "property_type": property_type,
        "notes": notes,
    }

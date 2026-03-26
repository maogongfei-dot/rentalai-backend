# Phase1 AI：自然语言 → 结构化字段（rule/regex，无 LLM）
# Phase C1：Query Parser v2 — 预处理、预算/房型/位置/偏好增强，输出统一 structured_query。
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

# 常见区域名（与 realistic samples 等对齐，用于 area 提取）
_KNOWN_AREAS = [
    "Central Milton Keynes",
    "Bletchley",
    "Wolverton",
    "Fishermead",
    "Shoreditch",
    "Westminster",
    "Bermondsey",
    "Camden",
    "Stratford",
    "Spinningfields",
    "Ancoats",
    "Chorlton",
    "City Centre",
    "Digbeth",
    "Edgbaston",
    "Jewellery Quarter",
]

_POSTCODE_RE = re.compile(
    r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b",
    re.IGNORECASE,
)


def normalize_query_text(s: str) -> str:
    """query 预处理：去首尾空白、合并多空格、转小写（仅用于规则匹配，不替代 raw_user_query 原文）。"""
    if not s:
        return ""
    t = str(s).strip()
    t = re.sub(r"[\t\r\n]+", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.lower()


def preprocess_user_query(s: str) -> str:
    """
    轻量同义归一（在 normalize 后的小写串上操作），便于正则稳定命中。
    """
    t = normalize_query_text(s)
    # 常见中文/混写 → 英文关键词
    replacements: list[tuple[str, str]] = [
        (r"包\s*水电", "bills included"),
        (r"包\s*全部账单", "bills included"),
        (r"包bill", "bills included"),
        (r"包\s*bill", "bills included"),
        (r"含bill", "bills included"),
        (r"一居室|一室|一房|一卧", "1 bedroom"),
        (r"两居室|二居室|两房", "2 bedroom"),
        (r"三居室|三房", "3 bedroom"),
        (r"四居室|四房", "4 bedroom"),
        (r"工作室|开间", "studio"),
        (r"合租房|合租", "shared house"),
        (r"单间(?!公寓)", "single room"),
        (r"通勤方便|上班方便", "easy commute"),
        (r"离车站近|靠近地铁", "near station"),
        (r"安全一点|安全区", "safer area"),
        (r"安静一点", "quiet area"),
        (r"精装带家具", "furnished"),
    ]
    for pat, repl in replacements:
        t = re.sub(pat, repl, t, flags=re.IGNORECASE)
    return t


def _norm_space(s: str) -> str:
    return " ".join(s.split())


def _extract_budgets(text: str) -> tuple[float | None, float | None, bool]:
    """
    预算解析：返回 (budget_min, budget_max, budget_flexible)。
    单个金额默认作 budget_max（与「上限」语义一致）；左右/around → flexible。
    """
    t = text.lower()
    flexible = bool(
        re.search(
            r"(左右|大约|大概|约|around|approximately|approx\.?|roughly)",
            t,
            re.IGNORECASE,
        )
    )

    # between X and Y / 从 X 到 Y / X 到 Y 镑
    for pattern in (
        r"between\s+£?\s*(\d{2,5})\s+and\s+£?\s*(\d{2,5})",
        r"from\s+£?\s*(\d{2,5})\s+to\s+£?\s*(\d{2,5})",
        r"(\d{2,5})\s*到\s*(\d{2,5})",
        r"(\d{2,5})\s*[-~–]\s*(\d{2,5})",
    ):
        m = re.search(pattern, t, re.IGNORECASE)
        if m:
            a, b = float(m.group(1)), float(m.group(2))
            return min(a, b), max(a, b), flexible

    # min / max 成对
    mmin = re.search(
        r"(?:min|minimum|最低|至少)\s*[：:]?\s*£?\s*(\d{2,5})",
        t,
        re.IGNORECASE,
    )
    mmax = re.search(
        r"(?:max|maximum|最高|最多)\s*[：:]?\s*£?\s*(\d{2,5})",
        t,
        re.IGNORECASE,
    )
    if mmin and mmax:
        a, b = float(mmin.group(1)), float(mmax.group(1))
        return min(a, b), max(a, b), flexible

    # 最低900，最高1200
    m = re.search(
        r"最低\s*(\d{2,5})\s*[,，]?\s*最高\s*(\d{2,5})",
        t,
    )
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        return min(a, b), max(a, b), flexible

    # under / below / 以内 / 不超过 → max
    m = re.search(
        r"(?:under|below|less\s*than|up\s*to|no\s*more\s*than|at\s*most|"
        r"以内|以下|不超过|最多|不高于)\s*[：:£]?\s*(\d{2,5})",
        t,
        re.IGNORECASE,
    )
    if m:
        return None, float(m.group(1)), flexible

    # above / over / min
    m = re.search(
        r"(?:above|over|more\s*than|at\s*least|最低|不少于)\s*[：:£]?\s*(\d{2,5})",
        t,
        re.IGNORECASE,
    )
    if m:
        return float(m.group(1)), None, flexible

    # budget 1300 / 预算 1500
    m = re.search(
        r"(?:budget|预算)\s*[：:£]?\s*(\d{2,5})",
        t,
        re.IGNORECASE,
    )
    if m:
        return None, float(m.group(1)), flexible

    # 裸数字（带 £ 或 pcm）
    nums: list[float] = []
    for m in re.finditer(
        r"(?:£\s*)?(\d{2,5})(?:\s*(?:pcm|per\s*month|/月|镑|磅))?",
        t,
    ):
        try:
            nums.append(float(m.group(1)))
        except ValueError:
            pass

    if not nums:
        return None, None, flexible

    if len(nums) >= 2:
        return min(nums), max(nums), flexible

    # 单数字：默认 max
    return None, nums[0], flexible


def _extract_bedrooms_and_room_type(text: str) -> tuple[int | None, str | None]:
    """卧室数 + room_type（studio/room/shared 等）。"""
    tl = text.lower()
    room_type: str | None = None

    if re.search(r"\bstudio\b|工作室|开间", tl):
        return 0, "studio"

    if re.search(r"shared\s*(?:house|flat)|合租房|合租|house\s*share", tl):
        room_type = "shared"
    if re.search(r"double\s*room|单间(?!公寓)|\broom\b(?!\s*mate)", tl) and "studio" not in tl:
        room_type = room_type or "room"

    if re.search(r"一居室|一室|一房|一卧|1\s*bed(?:room)?s?|1br\b|one\s*bed", tl):
        return 1, room_type
    if re.search(r"两居|二居|两房|2\s*bed(?:room)?s?|2br\b|two\s*bed", tl):
        return 2, room_type
    if re.search(r"三居|三房|3\s*bed(?:room)?s?|3br\b", tl):
        return 3, room_type
    if re.search(r"四居|四房|4\s*bed(?:room)?s?|4br\b|4\+", tl):
        return 4, room_type

    return None, room_type


def _extract_city(text: str) -> str | None:
    tl = text.lower()
    for city in _UK_CITIES_ORDERED:
        if city.lower() in tl:
            return city
    return None


def _extract_area(text: str, city: str | None) -> str | None:
    """已知区域名或「在 X 区」模式。"""
    tl = text.lower()
    for a in sorted(_KNOWN_AREAS, key=len, reverse=True):
        if a.lower() in tl:
            return a
    m = re.search(
        r"(?:在|位于|near)\s*([A-Za-z][A-Za-z\s\-]{2,45}?)(?:\s+(?:附近|区域|一带|区)|[，,。])",
        text,
        re.IGNORECASE,
    )
    if m:
        frag = m.group(1).strip()
        if city and city.lower() in frag.lower():
            return None
        if len(frag) >= 3:
            return frag
    return None


def _extract_postcode(text: str) -> str | None:
    m = _POSTCODE_RE.search(text.upper())
    if m:
        return _norm_space(m.group(1).upper())
    return None


def _extract_property_type(text: str, room_type: str | None) -> str | None:
    tl = text.lower()
    if room_type == "studio":
        return "studio"
    if re.search(r"\bflat\b|公寓(?!楼)", tl):
        return "flat"
    if re.search(r"\bapartment\b|公寓", tl):
        return "flat"
    if re.search(r"\bhouse\b|别墅|独栋", tl):
        return "house"
    if re.search(r"\broom\b|合租|单间", tl) or room_type in ("room", "shared"):
        return "room"
    if re.search(r"\bstudio\b", tl):
        return "studio"
    return None


def _extract_exclusions(text: str) -> tuple[list[str], list[str], list[str]]:
    """否定/排除：写入 excluded_*，供多轮 merge 与筛选（C4）。"""
    ex_pt: list[str] = []
    ex_rt: list[str] = []
    ex_notes: list[str] = []
    tl = text.lower()
    if re.search(r"不要\s*studio|no\s*studio|exclude\s*studio|不要开间", tl):
        ex_pt.append("studio")
    if re.search(r"不要\s*flat|不要\s*apartment|不要公寓", tl):
        ex_pt.append("flat")
    if re.search(r"不要\s*house|不要独栋", tl):
        ex_pt.append("house")
    if re.search(r"不要\s*room|不要单间|不想合租|不要合租|no\s*room\b", tl):
        ex_rt.append("room")
        ex_notes.append("不想合租")
    if re.search(r"不要太远|不想太远|别太远", tl):
        ex_notes.append("不要太远")
    return ex_pt, ex_rt, ex_notes


def parse_user_query(raw: str) -> dict[str, Any]:
    """
    Query Parser v2：将用户一句需求解析为 structured_query；未识别则 None / False / []。
    保持与 ai_recommendation_bridge._apply_structured_to_settings 兼容的键名。
    """
    if raw is None:
        raw = ""
    raw_user_query = str(raw).strip()
    # 规则匹配统一用预处理后的文本
    text = preprocess_user_query(raw_user_query)

    budget_min, budget_max, budget_flexible = _extract_budgets(text)
    bedrooms, room_type = _extract_bedrooms_and_room_type(text)
    city = _extract_city(text)
    postcode = _extract_postcode(raw_user_query)
    area = _extract_area(raw_user_query, city)
    property_type = _extract_property_type(text, room_type)

    bills_included: bool | None = None
    if re.search(
        r"bills?\s*included|包\s*bill|包bill|含bill|包水电|含水电|包费用|包全部账单",
        text,
    ):
        bills_included = True
    elif re.search(r"不包|不含bill|bills?\s*not|excluding\s*bills", text):
        bills_included = False

    furnished: bool | None = None
    if re.search(
        r"\bfurnished\b|fully\s*furnished|带家具|精装修|拎包入住|精装带家具",
        text,
    ):
        furnished = True
    elif re.search(r"\bunfurnished\b|不带家具|空房", text):
        furnished = False

    couple_friendly = bool(
        re.search(
            r"情侣|夫妻|couple|双人|suitable\s*for\s*couples?|couple\s*friendly",
            text,
        )
    )

    commute_preference = bool(
        re.search(
            r"通勤方便|通勤|上班方便|离工作|离公司近|commute|good\s*transport|easy\s*commute",
            text,
        )
    )
    near_station = bool(
        re.search(
            r"离车站近|靠近地铁|近车站|近地铁|near\s*(?:the\s*)?station|close\s*to\s*(?:tube|station)|walk(?:ing)?\s*distance\s*to\s*station",
            text,
        )
    )

    safety_priority = bool(
        re.search(
            r"(?<!不)安全|治安|(?<!not\s)\bsafety\b|\bsafe\b|\bsafer\b|safer\s*area|low\s*crime|安全区",
            text,
        )
    )
    quiet_priority = bool(
        re.search(
            r"安静|quiet|peaceful|quiet\s*area",
            text,
        )
    )

    notes_list: list[str] = []
    if couple_friendly:
        notes_list.append("couple friendly")
    if safety_priority:
        notes_list.append("safety")
    if quiet_priority:
        notes_list.append("quiet")
    if budget_flexible and (budget_min is not None or budget_max is not None):
        notes_list.append("flexible budget")

    ex_pt, ex_rt, ex_notes = _extract_exclusions(text)
    notes_list.extend(ex_notes)

    return {
        "raw_user_query": raw_user_query,
        "city": city,
        "area": area,
        "postcode": postcode,
        "budget_min": budget_min,
        "budget_max": budget_max,
        "budget_flexible": budget_flexible,
        "bedrooms": bedrooms,
        "room_type": room_type,
        "bills_included": bills_included,
        "furnished": furnished,
        "couple_friendly": couple_friendly if couple_friendly else None,
        "near_station": near_station if near_station else None,
        "commute_preference": commute_preference if commute_preference else None,
        "safety_priority": safety_priority if safety_priority else None,
        "quiet_priority": quiet_priority if quiet_priority else None,
        "property_type": property_type,
        "notes": notes_list,
        "excluded_property_types": ex_pt,
        "excluded_room_types": ex_rt,
        "excluded_notes": ex_notes,
    }

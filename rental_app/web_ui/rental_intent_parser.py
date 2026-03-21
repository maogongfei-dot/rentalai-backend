# P5 Phase2: 规则型自然语言 → AgentRentalRequest（无 LLM）
from __future__ import annotations

import re
import unicodedata

from web_ui.rental_intent import AgentRentalRequest

# --- 轻量归一化 helpers（可读优先，便于后续扩展）---


def normalize_fullwidth_and_spaces(text: str) -> str:
    """全角数字 → 半角；折叠多余空白。"""
    if not text:
        return ""
    s = unicodedata.normalize("NFKC", text)
    return " ".join(s.split())


def normalize_property_type(token: str | None) -> str | None:
    if not token:
        return None
    t = token.strip().lower()
    if t in ("apartment", "apt", "flat"):
        return "flat"
    if t in ("house", "studio", "room"):
        return t
    return None


def parse_max_rent(text: str) -> float | None:
    """
    租金/预算上限：中英混合，抓最明显表达；取文档中第一个强匹配（避免过度推断）。
    """
    s = normalize_fullwidth_and_spaces(text)
    low = s.lower()

    patterns: list[tuple[str, int]] = [
        # 中文优先（更具体）
        (r"预算\s*(\d{3,5})", 1),
        (r"不超过\s*(\d{3,5})", 1),
        (r"最多\s*(\d{3,5})", 1),
        (r"(\d{3,5})\s*以内", 1),
        (r"under\s*£?\s*(\d{3,5})\b", 1),
        (r"max\s*£?\s*(\d{3,5})\b", 1),
        (r"budget\s*(?:of|is|:)?\s*£?\s*(\d{3,5})\b", 1),
        (r"£\s*(\d{3,5})\b", 1),
        (r"(\d{3,5})\s*(?:pcm|/month|per\s+month|a\s+month)\b", 1),
    ]
    for pat, g in patterns:
        m = re.search(pat, low, flags=re.IGNORECASE)
        if m:
            try:
                return float(m.group(g))
            except (TypeError, ValueError):
                continue

    # 裸 4–5 位数字（最后手段，需 >=400 减少年份等误报）
    m = re.search(r"(?<!\w)(\d{4,5})(?!\w)", low)
    if m:
        try:
            v = float(m.group(1))
            if v >= 400:
                return v
        except (TypeError, ValueError):
            pass
    return None


def parse_bedrooms(text: str) -> tuple[int | None, bool]:
    """
    返回 (bedrooms, is_studio_hint)。
    studio：bedrooms=0，与 Phase1 一致。
    """
    s = normalize_fullwidth_and_spaces(text)
    low = s.lower()

    if re.search(r"\bstudio\b", low) or re.search(r"开间|单间公寓", s):
        return 0, True

    m = re.search(r"\b(\d+)\s*(?:bed(?:room)?s?|br)\b", low)
    if m:
        return int(m.group(1)), False

    for w, n in (
        ("one bed", 1),
        ("two bed", 2),
        ("three bed", 3),
        ("four bed", 4),
    ):
        if w in low:
            return n, False

    # 中文：一居、两居、一室、2房、一居室
    if re.search(r"一(?:居|室|房|居室)\b", s):
        return 1, False
    if re.search(r"两(?:居|室|房|居室)|二(?:居|室|房)", s):
        return 2, False
    if re.search(r"三(?:居|室|房)", s):
        return 3, False
    if re.search(r"四(?:居|室|房)", s):
        return 4, False
    m = re.search(r"(\d)\s*房", s)
    if m:
        return int(m.group(1)), False

    return None, False


def parse_postcode(text: str) -> str | None:
    """轻量 UK outward / full；postcode X / 靠近 X。"""
    s = normalize_fullwidth_and_spaces(text)
    up = s.upper().replace("  ", " ")

    m = re.search(
        r"\b([A-Z]{1,2}\d[\dA-Z]?\s*\d[A-Z]{2})\b",
        up,
    )
    if m:
        return m.group(1).strip()

    m = re.search(
        r"(?:postcode|post\s*code|邮编|靠近|附近)\s*[：: ]?\s*([A-Z]{1,2}\d[\dA-Z]?)\b",
        up,
        flags=re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()

    # Outward code only（如 MK9、E14），避免匹配无数字的短词
    m = re.search(r"\b([A-Z]{1,2}\d[A-Z0-9]?)\b", up)
    if m:
        return m.group(1).strip()

    return None


def parse_bills_included(text: str) -> bool | None:
    low = normalize_fullwidth_and_spaces(text).lower()
    if re.search(
        r"\b(?:bills\s+included|bills\s*inc|include\s+bills)\b",
        low,
    ):
        return True
    s = normalize_fullwidth_and_spaces(text)
    if re.search(r"包\s*bills?\b|包\s*账单|包bill", s, flags=re.IGNORECASE):
        return True
    return None


def parse_furnished(text: str) -> bool | None:
    low = normalize_fullwidth_and_spaces(text).lower()
    if "unfurnished" in low or re.search(r"不带家具|无家具", text):
        return False
    if re.search(r"\bfurnished\b", low) or re.search(r"带家具|有家具", text):
        return True
    return None


def parse_commute_minutes(text: str) -> int | None:
    s = normalize_fullwidth_and_spaces(text)
    low = s.lower()

    m = re.search(
        r"(?:within|under|max)\s*(\d{1,3})\s*(?:min|mins|minutes)\b",
        low,
    )
    if m:
        return int(m.group(1))

    m = re.search(
        r"\b(\d{1,3})\s*(?:min|mins|minutes)\s+(?:commute|to\s+work)\b",
        low,
    )
    if m:
        return int(m.group(1))

    m = re.search(
        r"(?:commute|travel)\s*(?:time|of)?\s*(?:under|max|<=|<)?\s*(\d{1,3})\s*(?:min|mins|minutes)\b",
        low,
    )
    if m:
        return int(m.group(1))

    m = re.search(r"通勤\s*(\d{1,3})\s*分钟", s)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d{1,3})\s*分钟\s*以内", s)
    if m:
        return int(m.group(1))

    return None


def parse_preferred_area(text: str) -> str | None:
    s = normalize_fullwidth_and_spaces(text)
    low = s.lower()

    # 中文：想在 X、X 附近、伦敦东边
    m = re.search(r"想在\s*([^，,。.\n]{2,40}?)(?:附近|，|,|。|$)", s)
    if m:
        cand = m.group(1).strip()
        if len(cand) >= 2:
            return cand
    m = re.search(r"([^，,。.\n]{2,40}?)附近", s)
    if m:
        cand = m.group(1).strip()
        if len(cand) >= 2 and not re.match(r"^\d+$", cand):
            return cand
    if re.search(r"伦敦东边", s):
        return "East London"

    # 英文：in / near / around X
    m = re.search(
        r"\b(?:in|near|around)\s+([a-z][a-z0-9\s\-]{1,40}?)(?:,|\.|$|\s+(?:with|under|for|and|max|within)\b)",
        low,
    )
    if m:
        cand = m.group(1).strip()
        if len(cand) >= 2 and not re.match(r"^\d+$", cand):
            return cand.title()

    return None


def parse_property_type_keyword(text: str) -> str | None:
    low = normalize_fullwidth_and_spaces(text).lower()
    order = (
        ("studio", "studio"),
        ("apartment", "flat"),
        ("flat", "flat"),
        ("house", "house"),
        ("room", "room"),
    )
    for kw, canonical in order:
        if re.search(rf"\b{re.escape(kw)}\b", low):
            return normalize_property_type(canonical)
    if "公寓" in text and "工作室" not in text:
        return "flat"
    return None


def parse_source_preference(text: str) -> str | None:
    low = normalize_fullwidth_and_spaces(text).lower()
    if re.search(r"\brightmove\b", low):
        return "rightmove"
    if re.search(r"\bzoopla\b", low):
        return "zoopla"
    return None


def _collect_unparsed_cues(text: str) -> str | None:
    """未建模关键词写入 notes（极轻量）。"""
    low = normalize_fullwidth_and_spaces(text).lower()
    cues: list[str] = []
    for pat, label in (
        (r"\bpet(?:s)?\b|宠物", "pets mentioned"),
        (r"\bparking\b|车位|停车", "parking mentioned"),
        (r"\bgarden\b|花园", "garden mentioned"),
        (r"\bgym\b|健身房", "gym mentioned"),
    ):
        if re.search(pat, low):
            cues.append(label)
    if not cues:
        return None
    return "; ".join(cues)


def parse_rental_intent(text: str) -> AgentRentalRequest:
    """
    规则型解析入口（等价产品名 parseRentalIntent）；输出 AgentRentalRequest。
    不完整解析允许；原文完整保留在 raw_query。
    """
    raw = (text or "").strip()
    if not raw:
        return AgentRentalRequest(raw_query="", notes=None)

    req = AgentRentalRequest(raw_query=raw, notes=None)

    req.max_rent = parse_max_rent(raw)

    br, studio = parse_bedrooms(raw)
    req.bedrooms = br
    pt = parse_property_type_keyword(raw)
    if studio:
        req.property_type = pt or "studio"
    elif pt:
        req.property_type = pt

    req.target_postcode = parse_postcode(raw)
    req.preferred_area = parse_preferred_area(raw)
    req.bills_included = parse_bills_included(raw)
    req.furnished = parse_furnished(raw)
    req.max_commute_minutes = parse_commute_minutes(raw)
    req.source_preference = parse_source_preference(raw)

    req.notes = _collect_unparsed_cues(raw)

    return req


def intent_has_key_signals(intent: AgentRentalRequest) -> bool:
    """是否已解析出至少一项关键字段（用于预览区 readiness 提示）；显式 false 也算。"""
    return any(
        [
            intent.max_rent is not None,
            bool(intent.preferred_area and intent.preferred_area.strip()),
            intent.bedrooms is not None,
            bool(intent.property_type and intent.property_type.strip()),
            bool(intent.target_postcode and intent.target_postcode.strip()),
            intent.max_commute_minutes is not None,
            intent.bills_included is not None,
            intent.furnished is not None,
            bool(intent.source_preference and intent.source_preference.strip()),
        ]
    )

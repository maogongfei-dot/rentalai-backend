"""Unified short-term rent search: internal listings plus external mock platforms."""

from backend.services import external_short_rent_service
from backend.services import short_rent_service


def search_all_short_rent(filters: dict = None) -> dict:
    return {
        "internal": short_rent_service.get_recommended_short_rent(filters),
        "external": external_short_rent_service.get_external_short_rent_recommendations(
            filters
        ),
    }


def get_combined_short_rent_results(filters: dict = None) -> list:
    payload = search_all_short_rent(filters)
    out = []
    for item in payload["internal"]:
        out.append({"source_type": "internal", **item})
    for item in payload["external"]:
        out.append({"source_type": "external", **item})
    return out


def _price_per_day_sort_key(row: dict) -> float:
    v = row.get("price_per_day")
    if v is None:
        return 999999.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 999999.0


def get_ranked_short_rent_results(filters: dict = None) -> list:
    rows = get_combined_short_rent_results(filters)
    return sorted(rows, key=_price_per_day_sort_key)


def explain_short_rent_result(result: dict) -> str:
    st = result.get("source_type")
    segments = []
    if st == "internal":
        segments.append("这是平台内短租房源，信息来自房东发布，适合优先查看。")
    elif st == "external":
        segments.append("这是外部平台短租房源，适合作为补充比较，需要跳转原平台查看详情。")

    p = None
    raw = result.get("price_per_day")
    if raw is not None:
        try:
            p = float(raw)
        except (TypeError, ValueError):
            p = None
    if p is not None:
        if p <= 40:
            segments.append("每日价格较低，性价比较高。")
        elif p >= 80:
            segments.append("每日价格偏高，建议结合位置和入住时间再判断。")

    return "".join(segments)


def add_explanations_to_short_rent_results(results: list) -> list:
    return [{**row, "explanation": explain_short_rent_result(row)} for row in results]


def _norm_str(value) -> str:
    if value is None:
        return ""
    return str(value)


def _norm_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return list(value)
    return []


def _norm_price(value):
    if value is None or value == "":
        return ""
    try:
        return float(value)
    except (TypeError, ValueError):
        return ""


def normalize_short_rent_result(result: dict) -> dict:
    st = result.get("source_type")
    if st == "internal":
        raw_src = result.get("source")
        if raw_src is None or str(raw_src).strip() == "":
            src = "RentalAI"
        else:
            src = str(raw_src).strip()
    else:
        src = _norm_str(result.get("source"))

    canonical = {
        "id": _norm_str(result.get("id")),
        "source_type": _norm_str(st),
        "source": src,
        "title": _norm_str(result.get("title")),
        "location": _norm_str(result.get("location")),
        "postcode": _norm_str(result.get("postcode")),
        "price_per_day": _norm_price(result.get("price_per_day")),
        "price_per_week": _norm_price(result.get("price_per_week")),
        "available_from": _norm_str(result.get("available_from")),
        "available_dates": _norm_list(result.get("available_dates")),
        "link": _norm_str(result.get("link")),
        "description": _norm_str(result.get("description")),
        "explanation": _norm_str(result.get("explanation")),
    }
    return {**result, **canonical}


def normalize_short_rent_results(results: list) -> list:
    return [normalize_short_rent_result(row) for row in results]


def get_final_short_rent_recommendations(filters: dict = None) -> list:
    """Rank, attach explanations, normalize — single entry point for short-rent listings."""
    ranked = get_ranked_short_rent_results(filters)
    with_explanations = add_explanations_to_short_rent_results(ranked)
    return normalize_short_rent_results(with_explanations)

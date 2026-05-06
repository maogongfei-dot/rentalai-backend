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

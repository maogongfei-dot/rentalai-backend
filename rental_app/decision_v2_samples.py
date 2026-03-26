# Phase C3：决策引擎 v2 本地快速验证（无 pytest）。
# 运行：python -m decision_v2_samples
from __future__ import annotations

from rental_decision_v2 import build_decision_v2, evaluate_core_match, evaluate_recommendation_risk
from rental_explain_v2 import build_explain_v2
from rental_query_parser import parse_user_query

# 覆盖：推荐、预算边缘+bill、严重超预算、房型不符、数据缺失
SCENARIOS: list[tuple[str, dict, dict]] = [
    (
        "预算内+通勤好+房型匹配 → RECOMMENDED",
        parse_user_query("Milton Keynes 2 bed budget 1300 near station"),
        {
            "rent": 1200.0,
            "bedrooms": 2,
            "city": "Milton Keynes",
            "bills": True,
            "commute_minutes": 22,
            "near_station": True,
            "property_type": "Flat",
            "final_score": 8.2,
        },
    ),
    (
        "预算边缘 + bill 不包 → CAUTION",
        parse_user_query("MK 2 bed max 1200 bills included"),
        {
            "rent": 1180.0,
            "bedrooms": 2,
            "city": "Milton Keynes",
            "bills": False,
            "commute_minutes": 28,
            "final_score": 7.0,
        },
    ),
    (
        "严重超预算 → NOT_RECOMMENDED",
        parse_user_query("London max 900 1 bed"),
        {
            "rent": 1650.0,
            "bedrooms": 1,
            "city": "London",
            "bills": False,
            "commute_minutes": 25,
            "final_score": 6.8,
        },
    ),
    (
        "房型不符（要 Studio 给一居）→ NOT_RECOMMENDED",
        parse_user_query("Milton Keynes studio under 1000"),
        {
            "rent": 950.0,
            "bedrooms": 1,
            "city": "Milton Keynes",
            "property_type": "Flat",
            "bills": False,
            "commute_minutes": 30,
            "final_score": 7.2,
        },
    ),
    (
        "大体符合但数据缺失多 → CAUTION / low confidence",
        parse_user_query("Birmingham 1 bed quiet area"),
        {
            "rent": 800.0,
            "bedrooms": 1,
            "city": "Birmingham",
            "commute_minutes": None,
            "final_score": 7.0,
        },
    ),
]


def _legacy_stub(h: dict) -> dict:
    wg, wn, rk = [], [], []
    if h.get("final_score", 0) >= 7.5:
        wg.append("得分较高")
    if h.get("rent", 0) > 1500:
        wn.append("租金偏高")
    if h.get("bills") is False:
        rk.append("账单可能另计")
    return {"why_good": wg, "why_not": wn, "risks": rk, "explain": "stub"}


def run() -> None:
    for title, sq, house in SCENARIOS:
        leg = _legacy_stub(house)
        ev2 = build_explain_v2(house, sq, base_scores={}, legacy_explain=leg)
        dv2 = build_decision_v2(
            house,
            sq,
            ev2,
            base_scores={},
            risks=leg["risks"],
            why_not=leg["why_not"],
        )
        cm = evaluate_core_match(house, sq, ev2)
        rk = evaluate_recommendation_risk(house, ev2, leg["risks"])
        print("===", title, "===")
        print("decision:", dv2["decision_label"], "| confidence:", dv2["confidence"])
        print("core:", cm["core_match_level"], "| risk:", rk["risk_level"])
        print("summary:", dv2["decision_summary"][:100], "...")
        print("must_check:", dv2["must_check_before_sign"])
        print()


if __name__ == "__main__":
    run()

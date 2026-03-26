# Phase C2：Explain v2 本地快速验证（无 pytest 依赖）。
# 运行：python -m explain_v2_samples
from __future__ import annotations

from rental_explain_v2 import build_explain_v2, build_match_summary, build_recommendation_summary
from rental_query_parser import parse_user_query

# 5+ 场景：预算+通勤、bill、情侣、studio 不匹配、超预算位置好
SCENARIOS: list[tuple[str, dict, dict]] = [
    (
        "预算内且通勤好",
        parse_user_query("Milton Keynes 2 bed budget 1300 near station easy commute"),
        {
            "listing_title": "MK 2-bed",
            "rent": 1200.0,
            "bedrooms": 2,
            "city": "Milton Keynes",
            "bills": False,
            "commute_minutes": 22,
            "near_station": True,
            "property_type": "Flat",
            "final_score": 8.2,
        },
    ),
    (
        "超预算但位置好",
        parse_user_query("London 1 bed max 1100 Westminster"),
        {
            "listing_title": "Westminster flat",
            "rent": 1650.0,
            "bedrooms": 1,
            "city": "London",
            "area": "Westminster",
            "bills": False,
            "commute_minutes": 18,
            "near_station": True,
            "final_score": 7.5,
        },
    ),
    (
        "bill 不匹配",
        parse_user_query("bills included studio Milton Keynes under 950"),
        {
            "listing_title": "No bills flat",
            "rent": 880.0,
            "bedrooms": 0,
            "city": "Milton Keynes",
            "bills": False,
            "property_type": "Studio",
            "commute_minutes": 25,
            "final_score": 7.0,
        },
    ),
    (
        "情侣友好匹配",
        parse_user_query("couple friendly 2 bed Manchester"),
        {
            "listing_title": "Couple OK 2 bed",
            "rent": 1150.0,
            "bedrooms": 2,
            "city": "Manchester",
            "couple_friendly": True,
            "bills": True,
            "commute_minutes": 30,
            "final_score": 8.0,
        },
    ),
    (
        "studio / room_type 不匹配",
        parse_user_query("studio near station MK"),
        {
            "listing_title": "One bed not studio",
            "rent": 1000.0,
            "bedrooms": 1,
            "city": "Milton Keynes",
            "property_type": "Flat",
            "near_station": True,
            "commute_minutes": 20,
            "final_score": 6.5,
        },
    ),
    (
        "安全/安静仅提示核实",
        parse_user_query("quiet area safer neighbourhood Birmingham max 900"),
        {
            "listing_title": "Bham flat",
            "rent": 850.0,
            "bedrooms": 1,
            "city": "Birmingham",
            "commute_minutes": 35,
            "final_score": 6.8,
        },
    ),
]


def _legacy_stub(h: dict) -> dict:
    """模拟 ai_recommendation_bridge._build_legacy_explain_block 的极简版。"""
    wg, wn, rk = [], [], []
    if h.get("final_score", 0) >= 7:
        wg.append("综合得分尚可")
    if h.get("rent", 0) > 1400:
        wn.append("租金偏高")
    if h.get("bills") is False:
        rk.append("账单可能另计")
    return {"why_good": wg, "why_not": wn, "risks": rk, "explain": "stub"}


def run() -> None:
    all_recs: list[dict] = []
    for label, sq, house in SCENARIOS:
        leg = _legacy_stub(house)
        scores = {"price_score": 70.0, "commute_score": 72.0}
        ev2 = build_explain_v2(house, sq, base_scores=scores, legacy_explain=leg)
        decision = "RECOMMENDED"
        um = ev2.get("unmatched_preferences") or []
        if um:
            decision = "NOT_RECOMMENDED" if len(um) >= 2 else "CAUTION"
        elif label == "超预算但位置好":
            decision = "CAUTION"
        ev2["match_summary"] = build_match_summary(ev2, decision)
        print("===", label, "===")
        print("match_summary:", ev2.get("match_summary"))
        print("matched:", ev2.get("matched_preferences"))
        print("partial:", ev2.get("partial_matches"))
        print("unmatched:", ev2.get("unmatched_preferences"))
        print("tradeoffs:", ev2.get("tradeoffs"))
        print()
        all_recs.append({"explain_v2": ev2})

    sq0 = SCENARIOS[0][1]
    print("--- recommendation_summary ---")
    print(build_recommendation_summary(sq0, all_recs[:3]))


if __name__ == "__main__":
    run()

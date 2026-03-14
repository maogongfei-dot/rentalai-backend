from module2_scoring import rank_houses as rank_houses_m2, build_compare_explain, build_decision_hints

def rank_listings(state):
    listings = state["listings"]

    if not listings:
        print("⚠️ 暂无房源可评分/排序")
        return state

    ranked = rank_houses_m2(listings, state["settings"], state["weights"])
    state["ranked_results"] = ranked   # ✅ 评分结果单独放这里
    state["ranked_compare_explain"] = build_compare_explain(ranked)  # B2-B2-B2-B2-A
    state["ranked_decision_hints"] = build_decision_hints(ranked, state.get("ranked_compare_explain") or {})  # B2-B2-B2-B2-B1
    print("✅ 已按评分排序完成")
    return state

def get_top_n(state, n=3):
    state = rank_listings(state)
    ranked = state.get("ranked_results", [])
    return ranked[:n]

def explain_score(house, budget):
    reasons = []

    rent = house.get("rent")
    commute = house.get("commute")

    if rent and rent <= budget:
        reasons.append("价格低于预算")

    if commute and commute <= 30:
        reasons.append("通勤时间合理")

    if house.get("bills"):
        reasons.append("包含 bills")

    return reasons


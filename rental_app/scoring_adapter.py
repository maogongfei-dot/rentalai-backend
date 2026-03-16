from datetime import datetime
from module2_scoring import rank_houses as rank_houses_m2, build_compare_explain, build_decision_hints
from engines.explain_engine import build_explanation, attach_explanation_snapshot, compare_house_results, build_top_house_summary, attach_top_house_summary_to_results

# ---------- A2-B2-B2-B2-A: 输出契约冻结（Module5 API-ready 最终冻结） ----------
# Module5 作为 API-ready baseline 保持冻结；后续如无必要不再修改其输出契约；新开发重点转向 Module3（合同与纠纷风险）。
RANKING_VERSION = "module5_api_ready_v1"

# api_response 顶层契约（固定 4 字段，后续 Web API/UI/Agent 只依赖此结构）
API_RESPONSE_CONTRACT_EXAMPLE = {
    "success": True,
    "status": "ok",
    "message": "Ranking generated successfully.",
    "data": None,  # 内为 ranking_result
}

# ranking_result 顶层契约（固定 14 字段，缺数据时为空结构/空列表）
RANKING_RESULT_CONTRACT_EXAMPLE = {
    "status": "ok",
    "message": "Ranking generated successfully.",
    "metadata": {"generated_at": "", "total_houses": 0, "returned_houses": 0, "ranking_version": RANKING_VERSION},
    "summary": {"top_choice_label": None, "backup_choice_label": None, "total_compared": 0, "preset_used": ""},
    "user_preferences": {"preferred_areas": [], "preferred_postcodes": [], "avoided_areas": [], "weight_preset": ""},
    "weights": {"resolved_weights": {}, "validated_weights": {}, "weight_warnings": []},
    "houses": [],
    "compare_explain": {},
    "comparison_explanation": {},
    "top_house_summary": {},
    "decision_hints": {},
    "preference_switch_hints": [],
    "preference_simulation": [],
    "multi_factor_simulation": [],
    "viewing_checklist": [],
    "action_plan": {},
}

# house 标准导出契约（data.houses[] 每项至少含以下结构）
HOUSE_EXPORT_CONTRACT_EXAMPLE = {
    "rank": 1,
    "house_label": "Rank 1",
    "final_score": None,
    "scores": {"price_score": None, "commute_score": None, "bills_score": None, "bedrooms_score": None, "area_score": None},
    "reasons": {"area_score_reason": None},
    "explain": {"recommendation_summary": None, "top_positive_factors": [], "top_negative_factors": [], "weighted_breakdown": {}},
}

# ---------- A2-B2-B2-B2-B1: Module5 最终验收清单 ----------
# 推荐 Git 快照名: Module5_API_Ready_v1
MODULE5_READINESS = {
    "module_name": "Module5",
    "ranking_version": RANKING_VERSION,
    "api_ready": True,
    "cli_ready": True,
    "json_safe_ready": True,
    "contract_frozen": True,
    "demo_ready": True,
    "checklist": {
        "unified_ranking_result": True,
        "json_safe_export": True,
        "api_response_envelope": True,
        "generate_ranking_api_response": True,
        "cli_reads_standard_structure": True,
        "empty_result_stable": True,
        "demo_or_example_available": True,
        "ranking_contract_frozen": True,
    },
    "notes": [
        "ranking_result/build_api_response/generate_ranking_api_response 已收口；CLI 优先读 ranking_result；空结果返回完整结构；契约见 API_RESPONSE_CONTRACT_EXAMPLE / RANKING_RESULT_CONTRACT_EXAMPLE / HOUSE_EXPORT_CONTRACT_EXAMPLE。",
    ],
}


def print_module5_readiness(ranking_result=None):
    """轻量验收输出：打印 Module5 readiness 摘要，便于检查是否可冻结。不影响主 CLI。"""
    r = (ranking_result or {}).get("metadata") or {}
    readiness = r.get("readiness") or MODULE5_READINESS
    print("--- Module5 readiness ---")
    print("  module_name:", readiness.get("module_name"), "  ranking_version:", readiness.get("ranking_version"))
    print("  api_ready:", readiness.get("api_ready"), "  cli_ready:", readiness.get("cli_ready"), "  contract_frozen:", readiness.get("contract_frozen"))
    print("  checklist:", readiness.get("checklist"))
    if readiness.get("notes"):
        n = (readiness.get("notes") or [""])[0]
        print("  notes:", n[:80] + "..." if len(n) > 80 else n)
    print("---")


# ---------- A2-B2-A: JSON-safe 导出版（供 Web API 直接返回） ----------
# 统一导出链路（A2-B2-B2-B1 验证）:
#   1. 排序与解释逻辑    rank_listings(state) 内: rank_houses_m2, build_compare_explain, build_decision_hints
#   2. build_ranking_result   rank_listings 内完成，写入 state["ranking_result"]
#   3. to_json_safe_ranking_result(ranking_result)
#   4. build_api_response(json_safe_result)
#   5. 总入口 generate_ranking_api_response(state) 串联 1~4，正常/空结果均稳定返回 api_response

def _to_json_safe_value(val):
    """递归将任意值转为 JSON 可序列化类型。datetime->ISO 字符串，set/tuple->list，其他不可序列化->str 兜底。"""
    if val is None:
        return None
    if isinstance(val, (str, int, float, bool)):
        return val
    if hasattr(val, "isoformat") and callable(getattr(val, "isoformat", None)):
        return val.isoformat()
    if isinstance(val, (set, tuple)):
        return [_to_json_safe_value(x) for x in val]
    if isinstance(val, dict):
        return {str(k): _to_json_safe_value(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_to_json_safe_value(x) for x in val]
    return str(val)


def to_json_safe_ranking_result(ranking_result):
    """
    将标准 ranking_result 转为可安全 JSON 序列化的 dict。
    输入: build_ranking_result(state) 或任意 ranking_result dict
    输出: 递归处理后的 dict，可直接 json.dumps(..., ensure_ascii=False)。
    """
    if ranking_result is None:
        return None
    return _to_json_safe_value(ranking_result)


# ---------- A2-B2-B1: 标准 API response envelope ----------

def build_api_response(ranking_result):
    """
    将 ranking_result 包装为标准 API response envelope。顶层契约固定: success, status, message, data（见 API_RESPONSE_CONTRACT_EXAMPLE）。
    空结果 (status=="empty") 仍返回 success=true，结构稳定。
    """
    if ranking_result is None:
        return {
            "success": True,
            "status": "empty",
            "message": "No ranking result available.",
            "data": None,
        }
    status = ranking_result.get("status") or "ok"
    message = ranking_result.get("message") or "Ranking generated successfully."
    success = status in ("ok", "empty")
    return {
        "success": success,
        "status": status,
        "message": message,
        "data": ranking_result,
    }


# ---------- A2-B2-B2-A: 统一导出链路 + API-ready 总入口 ----------

def generate_ranking_api_response(state):
    """
    统一导出链路总入口：排序 -> 标准 ranking_result -> JSON-safe -> API response。
    与 CLI 共用同一套底层生成逻辑（rank_listings / build_ranking_result）。

    输入: state（含 listings, settings, weights），与 init_state / CLI 结构一致
    输出: 可直接用于 Web API 返回的 api_response dict（success, status, message, data）

    内部链路:
      1. rank_listings(state)           # 排序 + 解释，写入 state["ranking_result"]
      2. build_ranking_result 已在其内完成
      3. to_json_safe_ranking_result(state["ranking_result"])
      4. build_api_response(...)
    """
    rank_listings(state)
    ranking_result = state.get("ranking_result")
    json_safe_result = to_json_safe_ranking_result(ranking_result)
    return build_api_response(json_safe_result)


def _standard_house_from_result(r, rank):
    """从单条 rank_houses 结果整理为标准导出，符合 HOUSE_EXPORT_CONTRACT_EXAMPLE；兼容用保留 house 原始。"""
    h = r.get("house") or {}
    ex = r.get("explain") or {}
    scores = {
        "price_score": r.get("price_score"),
        "commute_score": r.get("commute_score"),
        "bills_score": r.get("bills_score"),
        "bedrooms_score": r.get("bedrooms_score"),
        "area_score": r.get("area_score"),
    }
    reasons = {"area_score_reason": r.get("area_score_reason")}
    explain_export = {
        "recommendation_summary": ex.get("recommendation_summary"),
        "top_positive_factors": ex.get("top_positive_factors") or [],
        "top_negative_factors": ex.get("top_negative_factors") or [],
        "weighted_breakdown": ex.get("weighted_breakdown") or {},
    }
    return {
        "rank": rank,
        "house_label": f"Rank {rank}",
        "final_score": r.get("final_score"),
        "scores": scores,
        "reasons": reasons,
        "explain": explain_export,
        "house": h,
    }


def _empty_ranking_result(state):
    """空结果时返回结构完整、可预测的 ranking_result，API 友好。"""
    settings = state.get("settings") or {}
    now = datetime.now()
    return {
        "status": "empty",
        "message": "No houses available for ranking.",
        "metadata": {
            "generated_at": now.isoformat() if hasattr(now, "isoformat") else str(now),
            "total_houses": 0,
            "returned_houses": 0,
            "ranking_version": RANKING_VERSION,
            "readiness": MODULE5_READINESS,
        },
        "summary": {
            "top_choice_label": None,
            "backup_choice_label": None,
            "total_compared": 0,
            "preset_used": settings.get("weight_preset") or "balanced",
        },
        "user_preferences": {
            "preferred_areas": settings.get("preferred_areas") or [],
            "preferred_postcodes": settings.get("preferred_postcodes") or [],
            "avoided_areas": settings.get("avoided_areas") or [],
            "weight_preset": settings.get("weight_preset") or "balanced",
        },
        "weights": {"resolved_weights": {}, "validated_weights": {}, "weight_warnings": []},
        "houses": [],
        "compare_explain": {},
        "comparison_explanation": {},
        "top_house_summary": {},
        "decision_hints": {},
        "preference_switch_hints": [],
        "preference_simulation": [],
        "multi_factor_simulation": [],
        "viewing_checklist": [],
        "action_plan": {},
    }


def build_ranking_result(state):
    """
    统一收口：排序结果 → 标准 ranking_result。顶层契约固定 14 字段（见 RANKING_RESULT_CONTRACT_EXAMPLE）。
    houses[] 每项符合 HOUSE_EXPORT_CONTRACT_EXAMPLE。缺数据时为空结构，不报错。
    """
    ranked = state.get("ranked_results") or []
    compare_explain = state.get("ranked_compare_explain") or {}
    decision_hints = state.get("ranked_decision_hints") or {}
    settings = state.get("settings") or {}

    total = len(ranked)
    if total == 0:
        return _empty_ranking_result(state)

    first = ranked[0]
    resolved = first.get("resolved_weights") or {}
    validated = first.get("validated_weights") or {}
    weight_warnings = first.get("weight_warnings") or []

    now = datetime.now()
    metadata = {
        "generated_at": now.isoformat() if hasattr(now, "isoformat") else str(now),
        "total_houses": total,
        "returned_houses": total,
        "ranking_version": RANKING_VERSION,
        "readiness": MODULE5_READINESS,
    }
    user_preferences = {
        "preferred_areas": settings.get("preferred_areas") or [],
        "preferred_postcodes": settings.get("preferred_postcodes") or [],
        "avoided_areas": settings.get("avoided_areas") or [],
        "weight_preset": settings.get("weight_preset") or "balanced",
    }
    weights_block = {
        "resolved_weights": resolved,
        "validated_weights": validated,
        "weight_warnings": weight_warnings,
    }
    houses = [_standard_house_from_result(r, i + 1) for i, r in enumerate(ranked)]

    # Module7 Explain Engine: 为每个房源追加 explanation
    _FAILED_EXPLANATION = {
        "summary": "Explanation generation failed.",
        "recommended": None,
        "positive_reasons": [],
        "not_recommended_reasons": [],
        "neutral_notes": [],
        "next_actions": [],
    }
    for i, h in enumerate(houses):
        try:
            r = ranked[i]
            h["explanation"] = build_explanation(r, "house")
        except Exception:
            h["explanation"] = _FAILED_EXPLANATION.copy()
        attach_explanation_snapshot(h)

    primary = decision_hints.get("primary_recommendation") or {}
    backup = decision_hints.get("backup_option") or {}
    summary = {
        "top_choice_label": (houses[0].get("house_label") if houses else None) or primary.get("house_label"),
        "backup_choice_label": (houses[1].get("house_label") if len(houses) > 1 else None) or backup.get("house_label"),
        "total_compared": total,
        "preset_used": user_preferences.get("weight_preset") or "balanced",
    }

    # Phase3-A2: 为 Top2 生成 comparison_explanation
    comparison_explanation = {}
    if len(houses) >= 2:
        try:
            comparison_explanation = compare_house_results(
                houses[0], houses[1],
                primary_label=houses[0].get("house_label") or "Rank 1",
                secondary_label=houses[1].get("house_label") or "Rank 2",
            )
        except Exception:
            comparison_explanation = {}

    # Phase3-A3: TopN 推荐理由汇总，并为每个房源附加 rank / ranking_explanation / ranking_role
    top_house_summary = {}
    if houses:
        try:
            labels = [h.get("house_label") or f"Rank {i+1}" for i, h in enumerate(houses)]
            top_house_summary = build_top_house_summary(houses, labels=labels, top_n=min(3, len(houses)))
            houses = attach_top_house_summary_to_results(houses, top_house_summary)
        except Exception:
            top_house_summary = {}

    return {
        "status": "ok",
        "message": "Ranking generated successfully.",
        "metadata": metadata,
        "summary": summary,
        "user_preferences": user_preferences,
        "weights": weights_block,
        "houses": houses,
        "compare_explain": compare_explain,
        "comparison_explanation": comparison_explanation,
        "top_house_summary": top_house_summary,
        "decision_hints": decision_hints,
        "preference_switch_hints": decision_hints.get("preference_switch_hints") or [],
        "preference_simulation": decision_hints.get("preference_simulation") or [],
        "multi_factor_simulation": decision_hints.get("multi_factor_simulation") or [],
        "viewing_checklist": decision_hints.get("viewing_checklist") or [],
        "action_plan": decision_hints.get("action_plan") or {},
    }


def rank_listings(state):
    listings = state.get("listings") or []

    if not listings:
        print("⚠️ 暂无房源可评分/排序")
        state["ranked_results"] = []
        state["ranked_compare_explain"] = {}
        state["ranked_decision_hints"] = {}
        state["ranking_result"] = build_ranking_result(state)  # 空结果也返回完整结构
        return state

    ranked = rank_houses_m2(listings, state["settings"], state["weights"])
    state["ranked_results"] = ranked   # ✅ 评分结果单独放这里
    state["ranked_compare_explain"] = build_compare_explain(ranked)  # B2-B2-B2-B2-A
    state["ranked_decision_hints"] = build_decision_hints(ranked, state.get("ranked_compare_explain") or {})  # B2-B2-B2-B2-B1
    state["ranking_result"] = build_ranking_result(state)  # A1: 标准收口，供 API/UI
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


# ---------- 未来 Web API 接入占位（不引入 FastAPI/Flask） ----------
# 接入时可直接复用总入口，例如：
#
#   from scoring_adapter import generate_ranking_api_response
#
#   def ranking_route_handler(state: dict):
#       return generate_ranking_api_response(state)
#
# FastAPI: return 上述返回值即可；Flask: return jsonify(...)。
#
# Explain Engine 展示层格式化（Phase2-A4）:
#   - CLI 用: from engines.explain_engine import format_explanation_for_cli
#   - API 用: from engines.explain_engine import format_explanation_for_api
#   - Agent 用: from engines.explain_engine import format_explanation_for_agent


# ---------- A2-B2-B2-B1: 导出链路验证 demo ----------

def demo_api_response_flow():
    """
    最小可运行演示：正常有房源 / 空房源 两种情况下整条导出链路均返回标准 api_response。
    运行: 在 rental_app 目录下执行 python scoring_adapter.py
          或在上一级执行 python -m rental_app.scoring_adapter（需 PYTHONPATH 含项目根）
    """
    from state import init_state

    state = init_state()
    demo_listings = [
        {"rent": 900, "area": "bedford", "bills": False, "postcode": "MK41", "commute": 20, "bedrooms": 1},
        {"rent": 1200, "area": "bedford", "bills": True, "postcode": "MK40", "commute": 30, "bedrooms": 1},
    ]

    print("=== 1) 正常有房源 ===")
    state["listings"] = demo_listings.copy()
    resp = generate_ranking_api_response(state)
    print("  success:", resp.get("success"), " status:", resp.get("status"), " message:", (resp.get("message") or "")[:50])
    data = resp.get("data") or {}
    print("  data.houses 数量:", len(data.get("houses") or []))
    print("  data.summary.top_choice_label:", (data.get("summary") or {}).get("top_choice_label"))

    print("\n=== 2) 空房源 ===")
    state["listings"] = []
    resp_empty = generate_ranking_api_response(state)
    print("  success:", resp_empty.get("success"), " status:", resp_empty.get("status"))
    data_empty = resp_empty.get("data") or {}
    print("  data.houses 数量:", len(data_empty.get("houses") or []))
    print("  data 结构完整:", "metadata" in data_empty and "houses" in data_empty)

    print("\n=== Module5 readiness 摘要 ===")
    print_module5_readiness(resp.get("data"))
    print("（推荐 Git 快照名: Module5_API_Ready_v1）")
    print("\n--- demo_api_response_flow 结束 ---")


if __name__ == "__main__":
    demo_api_response_flow()


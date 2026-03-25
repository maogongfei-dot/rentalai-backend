# Phase1 AI：结构化字段 → state.settings + listings → scoring_adapter（Module5 排序引擎）
from __future__ import annotations

import io
import json
import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from data.storage.listing_storage import export_listings_as_dicts
from module2_scoring import get_area_from_postcode
from rental_query_parser import parse_user_query
from scoring_adapter import generate_ranking_api_response
from state import init_state
from web_bridge import listing_dict_to_engine_house

_TOP_N = 15
_MAX_POOL = 80


def _demo_listings_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "ai_demo_listings.json"


def _load_demo_listings() -> list[dict[str, Any]]:
    p = _demo_listings_path()
    if not p.is_file():
        return []
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        return [x for x in raw if isinstance(x, dict)]
    except (OSError, json.JSONDecodeError):
        return []


def _blob(row: dict[str, Any]) -> str:
    parts = [
        row.get("title"),
        row.get("address"),
        row.get("area_name"),
        row.get("city"),
        row.get("summary"),
    ]
    return " ".join(str(p) for p in parts if p).lower()


def _apply_structured_to_settings(sq: dict[str, Any]) -> dict[str, Any]:
    """解析结果 → init_state()['settings'] 可合并片段。"""
    base = init_state()["settings"]
    st: dict[str, Any] = deepcopy(base)

    bmax = sq.get("budget_max")
    bmin = sq.get("budget_min")
    if bmax is not None:
        st["budget"] = float(bmax)
    elif bmin is not None:
        st["budget"] = float(bmin) * 1.15
    else:
        st["budget"] = float(os.environ.get("RENTALAI_AI_DEFAULT_BUDGET", "2000"))

    br = sq.get("bedrooms")
    if br is not None:
        st["min_bedrooms"] = int(br)

    prefs_area: list[str] = []
    if sq.get("city"):
        prefs_area.append(str(sq["city"]).strip().lower())
    if sq.get("area"):
        prefs_area.append(str(sq["area"]).strip().lower())
    st["preferred_areas"] = prefs_area

    ppc: list[str] = []
    if sq.get("postcode"):
        ppc.append(str(sq["postcode"]).strip().upper())
    st["preferred_postcodes"] = ppc

    # 通勤 / 车站 → 更严的 commute_target
    commute_or_station = bool(sq.get("commute_preference")) or bool(sq.get("near_station"))
    st["commute_target"] = 30 if commute_or_station else 45

    if sq.get("safety_priority"):
        st["weight_preset"] = "area_first"
    elif commute_or_station:
        st["weight_preset"] = "commute_first"
    else:
        st["weight_preset"] = st.get("weight_preset") or "balanced"

    return st


def _passes_filters(row: dict[str, Any], sq: dict[str, Any], *, require_city: bool) -> bool:
    rent = row.get("rent_pcm")
    if rent is None:
        return False
    try:
        r = float(rent)
    except (TypeError, ValueError):
        return False

    bmax = sq.get("budget_max")
    if bmax is not None and r > float(bmax) * 1.25:
        return False
    bmin = sq.get("budget_min")
    if bmin is not None and r < float(bmin) * 0.7:
        return False

    br_need = sq.get("bedrooms")
    if br_need is not None and br_need > 0:
        lb = row.get("bedrooms")
        if lb is not None:
            try:
                if int(float(lb)) < int(br_need):
                    return False
            except (TypeError, ValueError):
                pass
    elif br_need == 0:
        lb = row.get("bedrooms")
        pt = (row.get("property_type") or "").lower()
        if lb is not None:
            try:
                if int(float(lb)) > 1:
                    return False
            except (TypeError, ValueError):
                pass
        elif "studio" not in pt and "studio" not in _blob(row):
            return False

    if sq.get("bills_included") is True:
        if row.get("bills_included") is False:
            return False

    city = sq.get("city")
    if require_city and city:
        if city.lower() not in _blob(row):
            return False

    return True


def _filter_pool(rows: list[dict[str, Any]], sq: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    """返回 (候选列表, 是否放宽了城市/预算等过滤)。"""
    strict = [r for r in rows if _passes_filters(r, sq, require_city=True)]
    if strict:
        return strict, False
    loose = [r for r in rows if _passes_filters(r, sq, require_city=False)]
    if loose:
        return loose, True
    # 预算/卧室过严时：保留有租金的房源交给排序引擎按预算打分
    any_rent = [r for r in rows if r.get("rent_pcm") is not None]
    return any_rent, True


def _merge_demo_for_city(pool: list[dict[str, Any]], sq: dict[str, Any]) -> list[dict[str, Any]]:
    """主库无匹配城市时，合并 ai_demo_listings 中同城样本（去重）。"""
    city = (sq.get("city") or "").strip().lower()
    if not city:
        return pool
    if any(city in _blob(r) for r in pool):
        return pool
    seen = {str(r.get("listing_id")) for r in pool if r.get("listing_id")}
    extra: list[dict[str, Any]] = []
    for r in _load_demo_listings():
        lid = r.get("listing_id")
        if lid and str(lid) in seen:
            continue
        if city in _blob(r):
            extra.append(r)
            if lid:
                seen.add(str(lid))
    return pool + extra


def _property_type_ok(row: dict[str, Any], want: str | None) -> bool:
    if not want:
        return True
    pt = (row.get("property_type") or "").lower()
    if want == "studio":
        return "studio" in pt
    if want == "flat":
        return any(x in pt for x in ("flat", "apartment", "maisonette"))
    if want == "house":
        return "house" in pt
    if want == "room":
        return "room" in pt or "house share" in pt
    return True


def _build_houses_from_listings(
    listings: list[dict[str, Any]],
    settings: dict[str, Any],
) -> list[dict[str, Any]]:
    budget = settings.get("budget")
    tp = (settings.get("preferred_postcodes") or [None])[0]
    target_postcode = str(tp).strip() if tp else None

    out: list[dict[str, Any]] = []
    for row in listings[:_MAX_POOL]:
        h = listing_dict_to_engine_house(
            row,
            budget=budget,
            target_postcode=target_postcode,
        )
        if not h:
            continue
        # 展示用元数据
        meta = {
            "listing_title": row.get("title") or row.get("address") or "",
            "listing_id": row.get("listing_id"),
            "source_url": row.get("source_url"),
        }
        merged = {**h, **{k: v for k, v in meta.items() if v is not None}}
        if not merged.get("area") and row.get("postcode"):
            merged["area"] = get_area_from_postcode(row.get("postcode"))
        out.append(merged)
    return out


def _build_explain_v2(house: dict) -> dict:
    why_good = []
    why_not = []
    risks = []

    rent = house.get("rent")
    score = house.get("final_score")
    commute = house.get("commute_minutes")
    bills = house.get("bills")
    bedrooms = house.get("bedrooms")

    # 性价比
    if score is not None:
        if score >= 8:
            why_good.append("整体性价比高")
        elif score < 6:
            why_not.append("综合评分较低")

    # 租金
    if rent is not None:
        if rent <= 1200:
            why_good.append("租金较低")
        elif rent > 1800:
            why_not.append("租金偏高")

    # 通勤
    if commute is not None:
        if commute <= 30:
            why_good.append("通勤方便")
        else:
            why_not.append("通勤时间较长")

    # bills
    if bills is False:
        risks.append("不包bill，实际每月支出可能增加£200-£400")

    # 户型
    if bedrooms is not None:
        if bedrooms == 0:
            risks.append("Studio空间较小")

    # 押金风险（简单模拟）
    deposit = house.get("deposit")
    if deposit is not None:
        if rent is not None and deposit > rent * 5:
            risks.append("押金偏高，注意是否合理")

    # 租金压力
    if rent is not None:
        if rent > 1800:
            risks.append("租金较高，长期负担较大")

    # 区域风险（简单规则）
    area = house.get("area")
    if area:
        if "unknown" in area.lower():
            risks.append("区域信息不明确，建议实地查看")

    # 通勤风险
    if commute is not None:
        if commute > 45:
            risks.append("通勤时间较长，可能影响生活质量")

    explain = "，".join(why_good[:2] + why_not[:1]) if (why_good or why_not) else "综合表现一般"

    return {
        "explain": explain,
        "why_good": why_good,
        "why_not": why_not,
        "risks": risks,
    }


def _build_decision(house: dict, explain_block: dict) -> dict:
    score = house.get("final_score", 0)
    risks = explain_block.get("risks", [])

    # 基础规则
    if score >= 8 and len(risks) <= 1:
        decision = "RECOMMENDED"
        reason = "整体表现优秀，风险较低，可以优先考虑"
    elif score >= 6:
        decision = "CAUTION"
        reason = "整体还可以，但存在一些需要注意的点"
    else:
        decision = "NOT_RECOMMENDED"
        reason = "评分较低或风险较多，不建议选择"

    return {
        "decision": decision,
        "decision_reason": reason,
    }


def _simplify_recommendations(ranking_data: dict[str, Any]) -> list[dict[str, Any]]:
    houses = ranking_data.get("houses") or []
    rec: list[dict[str, Any]] = []
    for h in houses[:_TOP_N]:
        house = h.get("house") or {}
        house = {
            **house,
            "final_score": h.get("final_score"),
            "commute_minutes": house.get("commute_minutes")
            if house.get("commute_minutes") is not None
            else house.get("commute_mins"),
        }
        exp = _build_explain_v2(house)
        dec = _build_decision(house, exp)
        rec.append(
            {
                "rank": h.get("rank"),
                "house_label": h.get("house_label"),
                "final_score": h.get("final_score"),
                "title": house.get("listing_title") or house.get("house_label"),
                "rent": house.get("rent"),
                "bedrooms": house.get("bedrooms"),
                "area": house.get("area"),
                "postcode": house.get("postcode"),
                "bills": house.get("bills"),
                "listing_id": house.get("listing_id"),
                "source_url": house.get("source_url"),
                "scores": h.get("scores") if isinstance(h.get("scores"), dict) else {},
                "explain": exp["explain"],
                "why_good": exp["why_good"],
                "why_not": exp["why_not"],
                "risks": exp["risks"],
                "decision": dec["decision"],
                "decision_reason": dec["decision_reason"],
            }
        )
    return rec


def run_ai_analyze(raw_user_query: str) -> dict[str, Any]:
    """
    单入口：原始 query → 解析 → 候选房源 → generate_ranking_api_response。
    返回统一 JSON（供 /api/ai-analyze 与前端使用）。
    """
    structured = parse_user_query(raw_user_query)

    main_rows = export_listings_as_dicts()
    pool, relaxed_city = _filter_pool(main_rows, structured)
    pool = _merge_demo_for_city(pool, structured)

    used_demo = False
    if not pool:
        demo = _load_demo_listings()
        pool, relaxed_city = _filter_pool(demo, structured)
        used_demo = bool(pool)

    if not pool:
        # 最简兜底：demo 全量（仅租金有效）
        pool = [r for r in _load_demo_listings() if r.get("rent_pcm") is not None]
        used_demo = bool(pool)

    want_pt = structured.get("property_type")
    if want_pt:
        pool = [r for r in pool if _property_type_ok(r, want_pt)] or pool

    settings = _apply_structured_to_settings(structured)
    houses = _build_houses_from_listings(pool, settings)

    total_candidates = len(houses)

    state = init_state()
    state["listings"] = houses
    state["settings"] = {**state["settings"], **settings}

    _old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        api_resp = generate_ranking_api_response(state)
    finally:
        sys.stdout = _old_stdout

    ranking_data = api_resp.get("data") or {}
    recommendations = _simplify_recommendations(ranking_data)

    return {
        "success": bool(api_resp.get("success")),
        "message": api_resp.get("message") or "",
        "raw_user_query": structured.get("raw_user_query") or raw_user_query.strip(),
        "structured_query": structured,
        "recommendations": recommendations,
        "summary": {
            "total_candidates": total_candidates,
            "top_count": len(recommendations),
            "used_demo_listings": used_demo,
            "city_filter_relaxed": relaxed_city,
        },
        "_ranking_full": ranking_data,
    }


def public_response_payload(result: dict[str, Any]) -> dict[str, Any]:
    """去掉内部大字段，仅返回前端与契约需要的键。"""
    return {
        "success": result.get("success"),
        "message": result.get("message"),
        "raw_user_query": result.get("raw_user_query"),
        "structured_query": result.get("structured_query"),
        "recommendations": result.get("recommendations"),
        "summary": result.get("summary"),
    }

# Phase1 AI：结构化字段 → state.settings + listings → scoring_adapter（Module5 排序引擎）
from __future__ import annotations

import io
import os
import sys
from copy import deepcopy
from typing import Any

from utils.listing_availability import filter_available_listings
from data.storage.listing_storage import export_listings_as_dicts
from landlord.landlord_listing_service import prepare_landlord_listing_for_save  # noqa: F401
from house_candidate_loader import get_last_candidate_load_meta, load_candidate_houses
from house_canonical import canonical_records_to_listing_rows, canonical_to_listing_row
from house_samples_loader import load_house_samples
from house_source_adapters import clean_and_normalize_house_record
from module2_scoring import get_area_from_postcode
from ai.llm_adapter import (
    llm_generate_decision,
    llm_generate_explain,
    llm_parse_query,
)
from rental_decision_v2 import build_top_decision_summary
from rental_explain_v2 import (
    build_match_summary,
    build_recommendation_summary,
)
from rental_multiturn import (
    CONVERSATION_STORE,
    build_conversation_payload,
    detect_followup_intent,
    merge_structured_query,
    update_conversation_store,
    _ensure_conversation_id,
)
from scoring_adapter import generate_ranking_api_response
from state import init_state
from web_bridge import listing_dict_to_engine_house

_TOP_N = 15
_MAX_POOL = 80


def _normalize_pool(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Phase A1/A3：先按 source 清洗（clean_*）再 canonical → 引擎兼容扁平 dict。
    """
    out: list[dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        src = str(r.get("source") or "unknown")
        canon = clean_and_normalize_house_record(r, source=src)
        out.append(canonical_to_listing_row(canon))
    return out


def _maybe_prepend_multisource(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Phase A3：设 RENTALAI_AI_APPEND_MULTISOURCE_SAMPLES=1 时在主库前插入多来源原始样本（再走 _normalize_pool）。"""
    if os.environ.get("RENTALAI_AI_APPEND_MULTISOURCE_SAMPLES", "0").lower() not in (
        "1",
        "true",
        "yes",
    ):
        return rows
    from house_samples_loader import load_multi_source_house_samples_raw

    return load_multi_source_house_samples_raw() + rows


def _use_realistic_samples() -> bool:
    """推荐链路切换点：默认启用 Phase A2 realistic 样本；设 RENTALAI_AI_USE_REALISTIC_SAMPLES=0 则回退为仅 demo。"""
    return os.environ.get("RENTALAI_AI_USE_REALISTIC_SAMPLES", "1").lower() not in (
        "0",
        "false",
        "no",
    )


def _load_demo_listings() -> list[dict[str, Any]]:
    """兼容旧名：等价于 load_house_samples('demo')。"""
    return load_house_samples("demo")


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

    if not _passes_exclusion_filters(row, sq):
        return False

    return True


def _passes_exclusion_filters(row: dict[str, Any], sq: dict[str, Any]) -> bool:
    """C4：排除 studio / room / flat 等（与 structured_query.excluded_* 对齐）。"""
    ex_pt = [str(x).lower() for x in (sq.get("excluded_property_types") or [])]
    ex_rt = [str(x).lower() for x in (sq.get("excluded_room_types") or [])]
    if not ex_pt and not ex_rt:
        return True
    pt = (row.get("property_type") or "").lower()
    blob = _blob(row)
    if "studio" in ex_pt and ("studio" in pt or "studio" in blob):
        return False
    if "flat" in ex_pt and any(x in pt for x in ("flat", "apartment", "maisonette")):
        return False
    if "house" in ex_pt and "house" in pt:
        return False
    if "room" in ex_rt and (
        "room" in pt or "share" in blob or "house share" in blob
    ):
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


def _merge_auxiliary_for_city(pool: list[dict[str, Any]], sq: dict[str, Any]) -> list[dict[str, Any]]:
    """
    主库无匹配城市时，先合并 realistic_house_samples（Phase A2），再合并原 demo（去重）。
    realistic 样本数据入口见 house_samples_loader.load_house_samples('realistic')。
    """
    city = (sq.get("city") or "").strip().lower()
    if not city:
        return pool
    if any(city in _blob(r) for r in pool):
        return pool
    seen = {str(r.get("listing_id")) for r in pool if r.get("listing_id")}
    extra: list[dict[str, Any]] = []

    batches: list[list[dict[str, Any]]] = []
    if _use_realistic_samples():
        batches.append(load_house_samples("realistic"))
    batches.append(load_house_samples("demo"))

    for batch in batches:
        for r in _normalize_pool(batch):
            lid = r.get("listing_id")
            if lid and str(lid) in seen:
                continue
            if city in _blob(r):
                extra.append(r)
                if lid:
                    seen.add(str(lid))
    return pool + extra


def inject_landlord_listings(pool: list[dict]) -> list[dict]:
    """
    Inject landlord listings into recommendation pool (mock version)
    """

    mock_landlord_listings = [
        {
            "id": "landlord_101",
            "landlord_id": "landlord_001",
            "title": "2 Bedroom Flat - Landlord Direct",
            "location": "London",
            "listing_mode": "long_rent",
            "monthly_price": 1750,
            "availability_status": "available",
            "source_type": "platform",
        },
        {
            "id": "landlord_102",
            "landlord_id": "landlord_002",
            "title": "Short Stay Studio",
            "location": "Manchester",
            "listing_mode": "short_rent",
            "price_per_night": 60,
            "min_stay_nights": 2,
            "availability_status": "available",
            "source_type": "platform",
        },
    ]

    return mock_landlord_listings + pool


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
        # 展示用元数据（Phase A5：优先 canonical 风格字段 listing_title）
        meta = {
            "listing_title": row.get("title")
            or row.get("listing_title")
            or row.get("address")
            or "",
            "listing_id": row.get("listing_id"),
            "source_url": row.get("source_url"),
        }
        for key in (
            "city",
            "bathrooms",
            "deposit",
            "property_type",
            "couple_friendly",
            "near_station",
            "features",
            "scores",
            "source",
            "final_score",
            "notes",
        ):
            if key in row and row[key] is not None:
                meta[key] = row[key]
        merged = {**h, **{k: v for k, v in meta.items() if v is not None}}
        if not merged.get("area") and row.get("postcode"):
            merged["area"] = get_area_from_postcode(row.get("postcode"))
        out.append(merged)
    return out


def _build_legacy_explain_block(house: dict) -> dict:
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


def _simplify_recommendations(
    ranking_data: dict[str, Any],
    structured_query: dict[str, Any],
) -> list[dict[str, Any]]:
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
        exp = _build_legacy_explain_block(house)
        dec = _build_decision(house, exp)
        scores = h.get("scores") if isinstance(h.get("scores"), dict) else {}
        if not scores and isinstance(house.get("scores"), dict):
            scores = house.get("scores") or {}
        # Phase C2 / C5：经 llm_adapter（默认规则）生成 explain_v2 与 decision_v2
        ev2_core = llm_generate_explain(
            house,
            structured_query,
            base_scores=scores,
            legacy_explain=exp,
        )
        decision_v2 = llm_generate_decision(
            house,
            structured_query,
            ev2_core,
            base_scores=scores,
            legacy_explain=exp,
        )
        label = decision_v2.get("decision_label") or dec["decision"]
        explain_v2 = {
            **ev2_core,
            "match_summary": build_match_summary(ev2_core, label),
        }
        rec.append(
            {
                "rank": h.get("rank"),
                "house_label": h.get("house_label"),
                "final_score": h.get("final_score"),
                "title": house.get("listing_title") or house.get("house_label"),
                "rent": house.get("rent"),
                "bedrooms": house.get("bedrooms"),
                "bathrooms": house.get("bathrooms"),
                "area": house.get("area"),
                "city": house.get("city"),
                "postcode": house.get("postcode"),
                "bills": house.get("bills"),
                "deposit": house.get("deposit"),
                "furnished": house.get("furnished"),
                "property_type": house.get("property_type"),
                "couple_friendly": house.get("couple_friendly"),
                "near_station": house.get("near_station"),
                "features": house.get("features"),
                "notes": house.get("notes"),
                "listing_id": house.get("listing_id"),
                "source": house.get("source"),
                "source_url": house.get("source_url"),
                "scores": scores,
                "explain": exp["explain"],
                "why_good": exp["why_good"],
                "why_not": exp["why_not"],
                "risks": exp["risks"],
                "decision": label,
                "decision_reason": decision_v2.get("decision_summary") or dec["decision_reason"],
                "explain_v2": explain_v2,
                "decision_v2": decision_v2,
            }
        )
    return rec


def normalize_listing_for_display(listing: dict) -> dict:
    """
    Normalize listing to frontend display format
    """
    if not isinstance(listing, dict):
        listing = {}

    location = listing.get("location")
    if not location:
        location = ", ".join(
            str(p) for p in (listing.get("area"), listing.get("city")) if p
        ) or None

    listing_mode = listing.get("listing_mode")
    if not listing_mode:
        listing_mode = (
            "short_rent"
            if listing.get("price_per_night") is not None
            else "long_rent"
        )

    source_type = listing.get("source_type") or listing.get("source")
    if source_type is None or (isinstance(source_type, str) and not str(source_type).strip()):
        source_type = "unknown"

    image_urls = listing.get("image_urls", [])
    if not isinstance(image_urls, list):
        image_urls = []

    listing_id = listing.get("id")
    if listing_id is None:
        listing_id = listing.get("listing_id")

    normalized = {
        "id": listing_id,
        "title": listing.get("title"),
        "location": location,
        "listing_mode": listing_mode,
        "source_type": str(source_type),
        "price": listing.get("monthly_price")
        or listing.get("price")
        or listing.get("rent"),
        "price_per_night": listing.get("price_per_night"),
        "image_urls": image_urls,
        "availability_status": listing.get("availability_status"),
        "final_score": listing.get("final_score"),
        "explain_summary": listing.get("explain_summary") or listing.get("explain"),
    }

    return normalized


def _rank_from_pool(
    raw_user_query: str,
    structured: dict[str, Any],
    pool: list[dict[str, Any]],
    *,
    sample_source: str,
    used_demo: bool,
    multisource_prepended: bool,
    relaxed_city: bool,
    dataset_used: str | None = None,
) -> dict[str, Any]:
    """候选 listing 行 pool → 评分排序 → recommendations（Phase A5 共用）。"""
    pool = inject_landlord_listings(pool)
    availability_before_count = len(pool)
    pool = filter_available_listings(pool)
    availability_after_count = len(pool)

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
    recommendations = _simplify_recommendations(ranking_data, structured)
    recommendation_summary = build_recommendation_summary(structured, recommendations)
    top_decision_block = build_top_decision_summary(recommendations, structured)

    recommendations = [
        normalize_listing_for_display(x) for x in recommendations
    ]

    summ: dict[str, Any] = {
        "total_candidates": total_candidates,
        "top_count": len(recommendations),
        "used_demo_listings": used_demo,
        "sample_source": sample_source or "unknown",
        "multisource_samples_prepended": multisource_prepended,
        "city_filter_relaxed": relaxed_city,
        "availability_before_count": availability_before_count,
        "availability_after_count": availability_after_count,
        "availability_filtered_count": availability_before_count - availability_after_count,
    }
    if dataset_used:
        summ["dataset"] = dataset_used

    return {
        "success": bool(api_resp.get("success")),
        "message": api_resp.get("message") or "",
        "raw_user_query": structured.get("raw_user_query") or raw_user_query.strip(),
        "structured_query": structured,
        "recommendations": recommendations,
        "recommendation_summary": recommendation_summary,
        "decision_summary": top_decision_block,
        "summary": summ,
        "_ranking_full": ranking_data,
    }


def run_ai_analyze_with_structured(
    raw_user_query: str,
    structured: dict[str, Any],
    dataset: str | None = None,
) -> dict[str, Any]:
    """
    已解析的 structured_query → 与 run_ai_analyze 相同候选池与排序（C4 多轮 merge 后复用）。
    dataset=zoopla|rightmove|market_combined 时 structured_query 传入 load_candidate_houses → 抓取 → cleaner → normalize。
    """
    structured = dict(structured) if structured else {}

    multisource_prepended = os.environ.get(
        "RENTALAI_AI_APPEND_MULTISOURCE_SAMPLES", "0"
    ).lower() in ("1", "true", "yes")

    dataset_key = (dataset or "").strip().lower() or None
    used_demo = False
    relaxed_city = False

    # dataset 切换：统一从 load_candidate_houses 取 canonical → listing 行（zoopla/rightmove 与 SQLite 池共享排序）
    if dataset_key in ("demo", "realistic", "multi_source"):
        canon = load_candidate_houses(dataset_key)
        main_rows = canonical_records_to_listing_rows(canon)
    elif dataset_key == "zoopla":
        # Phase D2：fetch_zoopla → cleaner → normalize
        canon = load_candidate_houses("zoopla", structured_query=structured)
        main_rows = canonical_records_to_listing_rows(canon)
    elif dataset_key == "rightmove":
        # Phase D5：fetch_rightmove → 同一套 cleaner → normalize
        canon = load_candidate_houses("rightmove", structured_query=structured)
        main_rows = canonical_records_to_listing_rows(canon)
    elif dataset_key == "market_combined":
        # 预留：zoopla + rightmove 合并去重后再推荐
        canon = load_candidate_houses("market_combined", structured_query=structured)
        main_rows = canonical_records_to_listing_rows(canon)
    else:
        main_rows = _normalize_pool(_maybe_prepend_multisource(export_listings_as_dicts()))

    filtered_main, relaxed_city = _filter_pool(main_rows, structured)
    pool = _merge_auxiliary_for_city(filtered_main, structured)

    if dataset_key in ("demo", "realistic", "multi_source"):
        if filtered_main:
            sample_source = "dataset_%s" % dataset_key
        elif pool:
            sample_source = "auxiliary_merge"
        else:
            sample_source = None
    elif dataset_key == "zoopla":
        if filtered_main:
            sample_source = "dataset_zoopla"
        elif pool:
            sample_source = "auxiliary_merge"
        else:
            sample_source = None
    elif dataset_key == "rightmove":
        if filtered_main:
            sample_source = "dataset_rightmove"
        elif pool:
            sample_source = "auxiliary_merge"
        else:
            sample_source = None
    elif dataset_key == "market_combined":
        if filtered_main:
            sample_source = "dataset_market_combined"
        elif pool:
            sample_source = "auxiliary_merge"
        else:
            sample_source = None
    else:
        if filtered_main:
            sample_source = "main"
        elif pool:
            sample_source = "auxiliary_merge"
        else:
            sample_source = None

    if not pool and _use_realistic_samples():
        realistic = _normalize_pool(load_house_samples("realistic"))
        pool, relaxed_city = _filter_pool(realistic, structured)
        if pool:
            sample_source = "realistic"

    if not pool:
        demo = _normalize_pool(load_house_samples("demo"))
        pool, relaxed_city = _filter_pool(demo, structured)
        if pool:
            sample_source = "demo"
            used_demo = True

    if not pool:
        pool = [r for r in _normalize_pool(load_house_samples("demo")) if r.get("rent_pcm") is not None]
        if pool:
            sample_source = "demo_rent_only"
            used_demo = True

    out = _rank_from_pool(
        raw_user_query,
        structured,
        pool,
        sample_source=sample_source or "unknown",
        used_demo=used_demo,
        multisource_prepended=multisource_prepended,
        relaxed_city=relaxed_city,
        dataset_used=dataset_key,
    )
    # Phase D2+D4+D5：抓取模式与清洗统计写入 summary（Zoopla / Rightmove / market_combined）
    if dataset_key in ("zoopla", "rightmove", "market_combined"):
        meta = get_last_candidate_load_meta()
        summ = out.setdefault("summary", {})
        if dataset_key == "zoopla":
            sm = meta.get("zoopla_source_mode")
            if sm:
                summ["source_mode"] = sm
            if sm == "zoopla_mock_fallback":
                note = "Zoopla live fetch unavailable or empty; using built-in mock listings."
                summ["note"] = (summ.get("note") + " " if summ.get("note") else "") + note
            elif sm == "zoopla_realistic_fallback":
                note = "Zoopla pool unavailable or empty after normalize; using realistic sample pool."
                summ["note"] = (summ.get("note") + " " if summ.get("note") else "") + note
        elif dataset_key == "rightmove":
            sm = meta.get("rightmove_source_mode")
            if sm:
                summ["source_mode"] = sm
            if sm == "rightmove_mock_fallback":
                note = "Rightmove live fetch unavailable or empty; using built-in mock listings."
                summ["note"] = (summ.get("note") + " " if summ.get("note") else "") + note
            elif sm == "rightmove_realistic_fallback":
                note = "Rightmove pool unavailable or empty after normalize; using realistic sample pool."
                summ["note"] = (summ.get("note") + " " if summ.get("note") else "") + note
        else:
            summ["source_mode"] = {
                "zoopla": meta.get("zoopla_source_mode"),
                "rightmove": meta.get("rightmove_source_mode"),
            }
        scs = meta.get("scrape_clean_stats")
        if isinstance(scs, dict) and scs:
            summ["scrape_clean_stats"] = scs
    return out


def run_ai_analyze(
    raw_user_query: str,
    dataset: str | None = None,
) -> dict[str, Any]:
    """
    单入口：原始 query → 解析 → 候选房源 → generate_ranking_api_response。
    Phase A5：dataset 为 demo|realistic|multi_source 时，候选池以对应本地样本为主（canonical 加载）；
    Phase D2/D5：dataset=zoopla|rightmove|market_combined 时走对应 fetch → cleaner → normalize → ranking；
    未传 dataset 时保持原行为（SQLite + 可选 multisource 前置 + 合并 + 回退）。
    """
    return run_ai_analyze_with_structured(
        raw_user_query,
        llm_parse_query(raw_user_query),
        dataset=dataset,
    )


def run_ai_analyze_zoopla(raw_user_query: str) -> dict[str, Any]:
    """Phase D2：单测入口 — 固定 dataset=zoopla，跑完整推荐链路。"""
    return run_ai_analyze(raw_user_query, dataset="zoopla")


def run_ai_analyze_rightmove(raw_user_query: str) -> dict[str, Any]:
    """Phase D5：单测入口 — 固定 dataset=rightmove。"""
    return run_ai_analyze(raw_user_query, dataset="rightmove")


def run_ai_analyze_multiturn(
    raw_user_query: str,
    previous_structured_query: dict[str, Any] | None = None,
    conversation_id: str | None = None,
    dataset: str | None = None,
) -> dict[str, Any]:
    """
    C4：多轮 — 解析当前句 → follow-up 意图 → merge → 推荐。
    previous_structured_query 与 conversation_id 可组合；可从内存 store 恢复上一轮 merged_query。
    """
    current_sq = llm_parse_query(raw_user_query)
    followup = detect_followup_intent(raw_user_query)
    intent = str(followup.get("intent") or "generic_followup")

    prev = previous_structured_query if previous_structured_query else None
    if prev is None and conversation_id:
        cid = _ensure_conversation_id(conversation_id)
        st = CONVERSATION_STORE.get(cid)
        if st and isinstance(st.get("merged_query"), dict):
            prev = deepcopy(st["merged_query"])

    # single_turn vs multi_turn：有上下文合并，或「重新来」且存在上一轮
    if intent == "restart_search":
        merged_sq = deepcopy(current_sq)
        turn_mode = "multi_turn" if prev is not None else "single_turn"
    elif prev is not None:
        merged_sq = merge_structured_query(prev, current_sq)
        turn_mode = "multi_turn"
    else:
        merged_sq = deepcopy(current_sq)
        turn_mode = "single_turn"

    base = run_ai_analyze_with_structured(raw_user_query, merged_sq, dataset=dataset)

    # 多轮入口每次写入内存 store，保证首轮也能返回 conversation_id 供下一轮只带 id 调用
    cid_out = _ensure_conversation_id(conversation_id)
    turn_idx, history = update_conversation_store(
        cid_out,
        raw_user_query=raw_user_query,
        structured_query=current_sq,
        merged_query=merged_sq,
    )

    conversation = build_conversation_payload(
        conversation_id=cid_out,
        turn_index=turn_idx,
        history=history,
        current_structured_query=current_sq,
        merged_query=merged_sq,
    )

    out = dict(base)
    out["current_structured_query"] = current_sq
    out["merged_query"] = merged_sq
    out["followup_intent"] = followup
    out["turn_mode"] = turn_mode
    out["conversation_id"] = cid_out
    out["conversation"] = conversation
    out["structured_query"] = merged_sq
    out["raw_user_query"] = raw_user_query.strip()
    return out


def run_ai_analyze_with_records(
    raw_user_query: str,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Phase A5：已标准化 canonical 记录（与 A4 import 全量 records 一致）→ 推荐。
    池为空或过滤后为空时，仍按全局 realistic/demo 回退，避免无结果。
    """
    structured = llm_parse_query(raw_user_query)
    multisource_prepended = False
    used_demo = False
    relaxed_city = False

    pool = canonical_records_to_listing_rows(records)
    filtered_main, relaxed_city = _filter_pool(pool, structured)
    pool = _merge_auxiliary_for_city(filtered_main, structured)
    sample_source = "imported"

    if filtered_main:
        sample_source = "imported"
    elif pool:
        sample_source = "auxiliary_merge"

    if not pool and _use_realistic_samples():
        realistic = _normalize_pool(load_house_samples("realistic"))
        pool, relaxed_city = _filter_pool(realistic, structured)
        if pool:
            sample_source = "realistic_fallback"

    if not pool:
        demo = _normalize_pool(load_house_samples("demo"))
        pool, relaxed_city = _filter_pool(demo, structured)
        if pool:
            sample_source = "demo_fallback"
            used_demo = True

    if not pool:
        pool = [r for r in _normalize_pool(load_house_samples("demo")) if r.get("rent_pcm") is not None]
        if pool:
            sample_source = "demo_rent_only"
            used_demo = True

    return _rank_from_pool(
        raw_user_query,
        structured,
        pool,
        sample_source=sample_source,
        used_demo=used_demo,
        multisource_prepended=multisource_prepended,
        relaxed_city=relaxed_city,
        dataset_used="imported",
    )


def public_response_payload(result: dict[str, Any]) -> dict[str, Any]:
    """去掉内部大字段，仅返回前端与契约需要的键。"""
    payload: dict[str, Any] = {
        "success": result.get("success"),
        "message": result.get("message"),
        "raw_user_query": result.get("raw_user_query"),
        "structured_query": result.get("structured_query"),
        "recommendations": result.get("recommendations"),
        "recommendation_summary": result.get("recommendation_summary"),
        "decision_summary": result.get("decision_summary"),
        "summary": result.get("summary"),
    }
    # C4 多轮：单轮 analyze 无这些键时为 None
    for k in (
        "current_structured_query",
        "merged_query",
        "followup_intent",
        "turn_mode",
        "conversation_id",
        "conversation",
    ):
        payload[k] = result.get(k)
    return payload

# Phase C2：Explain Engine v2 — 用户需求 vs 房源字段对照，无 LLM。
from __future__ import annotations

import re
from typing import Any

# --- 房源字段归一（listing / engine house 混用）---------------------------------


def _house_rent(h: dict[str, Any]) -> float | None:
    for k in ("rent", "rent_pcm"):
        v = h.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return None


def _house_bills_included(h: dict[str, Any]) -> bool | None:
    """True/False/None（未知）。"""
    b = h.get("bills")
    if b is True:
        return True
    if b is False:
        return False
    if isinstance(b, str):
        s = b.lower()
        if "includ" in s:
            return True
        if "exclud" in s:
            return False
    return None


def _house_commute(h: dict[str, Any]) -> int | None:
    for k in ("commute_minutes", "commute_mins"):
        v = h.get(k)
        if v is not None:
            try:
                return int(float(v))
            except (TypeError, ValueError):
                pass
    return None


def _house_bedrooms(h: dict[str, Any]) -> int | None:
    v = h.get("bedrooms")
    if v is None:
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _house_furnished(h: dict[str, Any]) -> bool | None:
    v = h.get("furnished")
    if v is True:
        return True
    if v is False:
        return False
    return None


def _house_near_station(h: dict[str, Any]) -> bool | None:
    v = h.get("near_station")
    if v is True:
        return True
    if v is False:
        return False
    return None


def _house_couple_friendly(h: dict[str, Any]) -> bool | None:
    v = h.get("couple_friendly")
    if v is True:
        return True
    if v is False:
        return False
    return None


def _blob_lower(h: dict[str, Any]) -> str:
    parts = [
        h.get("listing_title"),
        h.get("address"),
        h.get("area"),
        h.get("area_name"),
        h.get("city"),
        h.get("postcode"),
        h.get("summary"),
    ]
    return " ".join(str(p) for p in parts if p).lower()


def _postcode_norm(pc: str) -> str:
    return re.sub(r"\s+", " ", str(pc).strip().upper())


def _postcode_match(h: dict[str, Any], want: str) -> bool:
    hp = h.get("postcode")
    if not hp or not want:
        return False
    return _postcode_norm(str(hp)) == _postcode_norm(want)


def _city_match(sq: dict[str, Any], h: dict[str, Any]) -> bool:
    c = (sq.get("city") or "").strip().lower()
    if not c:
        return False
    blob = _blob_lower(h)
    return c in blob or c.replace(" ", "") in blob.replace(" ", "")


def _area_match(sq: dict[str, Any], h: dict[str, Any]) -> bool:
    a = (sq.get("area") or "").strip().lower()
    if not a:
        return False
    blob = _blob_lower(h)
    return a in blob


def _property_type_lower(h: dict[str, Any]) -> str:
    return " ".join(str(h.get("property_type") or "").lower().split())


def _is_studio_house(h: dict[str, Any]) -> bool:
    pt = _property_type_lower(h)
    if "studio" in pt:
        return True
    br = _house_bedrooms(h)
    return br == 0 and "studio" in _blob_lower(h)


# --- 分项：用户需求 vs 房源 ---------------------------------------------------


def _explain_budget(
    sq: dict[str, Any], h: dict[str, Any], rent: float | None
) -> tuple[list[str], list[str], list[str]]:
    matched: list[str] = []
    partial: list[str] = []
    unmatched: list[str] = []
    bmin = sq.get("budget_min")
    bmax = sq.get("budget_max")
    flex = bool(sq.get("budget_flexible"))
    if rent is None:
        return matched, partial, unmatched
    if bmin is None and bmax is None:
        return matched, partial, unmatched

    tol_hi = 1.12 if flex else 1.08
    tol_lo = 0.92 if flex else 0.95

    if bmax is not None and bmin is not None:
        lo = float(bmin) * tol_lo
        hi = float(bmax) * tol_hi
        if lo <= rent <= float(bmax):
            matched.append("租金在预算区间内")
        elif rent <= float(bmax) * tol_hi:
            partial.append("租金略高于预算上限，但在可接受浮动范围内")
        elif rent > float(bmax) * 1.15:
            unmatched.append("租金明显高于预算上限")
        elif rent < lo:
            partial.append("租金低于预算下限（请确认房型与位置是否符合预期）")
    elif bmax is not None:
        cap = float(bmax) * tol_hi
        if rent <= float(bmax):
            matched.append("租金在预算上限内")
        elif rent <= cap:
            partial.append("租金略高于预算上限")
        else:
            unmatched.append("租金超出预算上限较多")
    elif bmin is not None:
        if rent >= float(bmin):
            matched.append("租金达到或高于期望最低预算")
        else:
            partial.append("租金低于最低预算（可核对是否附带条件）")

    return matched, partial, unmatched


def _explain_bedrooms_and_type(
    sq: dict[str, Any], h: dict[str, Any]
) -> tuple[list[str], list[str], list[str]]:
    matched: list[str] = []
    partial: list[str] = []
    unmatched: list[str] = []

    want_br = sq.get("bedrooms")
    want_rt = (sq.get("room_type") or "").strip().lower()
    want_pt = (sq.get("property_type") or "").strip().lower()
    # 解析器可能只填 property_type=studio
    if want_pt == "studio" and not want_rt:
        want_rt = "studio"

    hbr = _house_bedrooms(h)
    hpt = _property_type_lower(h)
    studio_h = _is_studio_house(h)

    # Studio / room_type 优先于卧室数
    if want_rt == "studio":
        if studio_h:
            matched.append("房型为 Studio，符合需求")
        else:
            unmatched.append("需求为 Studio，当前房源类型不完全一致")

    if want_br is not None and int(want_br) > 0:
        need = int(want_br)
        if hbr is None:
            partial.append("卧室数量在样本中未明确，建议核对户型")
        elif hbr >= need:
            matched.append("卧室数量满足要求（至少 %s 间）" % need)
        elif hbr == need - 1:
            partial.append("卧室少一间，可能需妥协或改需求")
        else:
            unmatched.append("卧室数量低于需求")

    if want_pt:
        # studio 已在 room_type 分支处理，避免重复文案
        if want_pt == "studio" and studio_h and want_rt != "studio":
            matched.append("物业类型与 Studio 需求一致")
        elif want_pt == "flat" and any(x in hpt for x in ("flat", "apartment", "maisonette")):
            matched.append("物业类型为 Flat/Apartment，符合偏好")
        elif want_pt == "house" and "house" in hpt:
            matched.append("物业类型为 House，符合偏好")
        elif want_pt == "room" and ("room" in hpt or "share" in hpt):
            matched.append("房源类型与单间/合租偏好一致")
        elif want_pt and hpt:
            if want_pt not in hpt and not (
                want_pt == "flat" and "apartment" in hpt
            ):
                partial.append("物业类型与用户偏好仅部分一致")

    if want_rt in ("shared", "room") and ("share" in hpt or "room" in hpt):
        matched.append("合租房/单间类房源，符合 room 类需求")

    return matched, partial, unmatched


def _explain_location(sq: dict[str, Any], h: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    matched: list[str] = []
    partial: list[str] = []
    unmatched: list[str] = []

    pc = (sq.get("postcode") or "").strip()
    if pc and _postcode_match(h, pc):
        matched.append("邮编与期望一致")
    elif pc:
        unmatched.append("邮编与期望不一致")

    ar = (sq.get("area") or "").strip()
    if ar:
        if _area_match(sq, h):
            matched.append("区域与期望一致或包含期望区域名")
        elif _city_match(sq, h):
            partial.append("城市符合，但细分区域与期望不完全一致")
        else:
            partial.append("区域偏好仅部分匹配（请核对地址）")

    ct = (sq.get("city") or "").strip()
    if ct and not pc and not ar:
        if _city_match(sq, h):
            matched.append("城市符合搜索范围")
        else:
            unmatched.append("城市与期望不一致")

    return matched, partial, unmatched


def _explain_bills_furnished_couple(
    sq: dict[str, Any], h: dict[str, Any]
) -> tuple[list[str], list[str], list[str]]:
    matched: list[str] = []
    partial: list[str] = []
    unmatched: list[str] = []

    if sq.get("bills_included") is True:
        hb = _house_bills_included(h)
        if hb is True:
            matched.append("包 Bill / 账单包含在租金内")
        elif hb is False:
            unmatched.append("不包 Bill，与「包 bill」需求不一致")
        else:
            partial.append("是否包 Bill 在样本中未标明，建议向中介核实")

    if sq.get("bills_included") is False:
        hb = _house_bills_included(h)
        if hb is False:
            matched.append("租金不含 Bill（与「不强制包 bill」类需求兼容）")

    if sq.get("furnished") is True:
        hf = _house_furnished(h)
        if hf is True:
            matched.append("带家具 / 配置与 furnished 需求一致")
        elif hf is False:
            unmatched.append("未标明带家具，与 furnished 需求可能不一致")
        else:
            partial.append("是否带家具未在样本中标明")

    if sq.get("furnished") is False:
        hf = _house_furnished(h)
        if hf is False:
            matched.append("未配家具或未强调精装，与 unfurnished 偏好一致")

    if sq.get("couple_friendly") is True:
        cf = _house_couple_friendly(h)
        if cf is True:
            matched.append("房源标注适合情侣 / couple friendly")
        elif cf is False:
            unmatched.append("标注可能不适合情侣，与需求不一致")
        else:
            partial.append("是否适合情侣未在样本中标明，建议确认房东政策")

    return matched, partial, unmatched


def _explain_commute_station(
    sq: dict[str, Any], h: dict[str, Any]
) -> tuple[list[str], list[str], list[str]]:
    matched: list[str] = []
    partial: list[str] = []
    unmatched: list[str] = []

    want_commute = bool(sq.get("commute_preference"))
    want_station = bool(sq.get("near_station"))
    if not want_commute and not want_station:
        return matched, partial, unmatched

    cm = _house_commute(h)
    ns = _house_near_station(h)

    if want_station:
        if ns is True:
            matched.append("靠近车站 / 交通便利（标注）")
        elif ns is False:
            partial.append("离车站较远或与「近车站」偏好不完全一致")
        else:
            partial.append("是否近车站在样本中未明确")

    if want_commute:
        if cm is not None:
            if cm <= 28:
                matched.append("通勤时间较短（约 %s 分钟）" % cm)
            elif cm <= 42:
                partial.append("通勤时间中等（约 %s 分钟）" % cm)
            else:
                unmatched.append("通勤时间较长（约 %s 分钟），与「通勤方便」偏好有差距" % cm)
        else:
            partial.append("通勤时间未在样本中提供，建议用地图自行测算")

    return matched, partial, unmatched


def _explain_safety_quiet(sq: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    """无房源侧可靠字段时不编造；仅输出「需核实」类说明。"""
    matched: list[str] = []
    partial: list[str] = []
    unmatched: list[str] = []

    if sq.get("safety_priority"):
        partial.append(
            "当前样本缺少独立「安全评分」字段，建议查犯罪率/实地看房"
        )
    if sq.get("quiet_priority"):
        partial.append(
            "安静程度在样本中通常无直接字段，建议看房时段与邻居情况自行确认"
        )
    return matched, partial, unmatched


def _dedupe_preserve(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in seq:
        x = str(x).strip()
        if not x or x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def _pick_strengths(
    matched: list[str],
    legacy_good: list[str],
    scores: dict[str, Any] | None,
) -> list[str]:
    out: list[str] = []
    out.extend(matched[:3])
    for g in legacy_good or []:
        if len(out) >= 3:
            break
        out.append(g)
    if len(out) < 2 and scores:
        ps = scores.get("price_score")
        cs = scores.get("commute_score")
        if isinstance(ps, (int, float)) and ps >= 75:
            out.append("价格维度得分较高")
        if isinstance(cs, (int, float)) and cs >= 75 and len(out) < 3:
            out.append("通勤维度得分较高")
    return _dedupe_preserve(out)[:3]


def _pick_tradeoffs(
    partial: list[str],
    unmatched: list[str],
    legacy_not: list[str],
    risks: list[str],
) -> list[str]:
    pool = list(unmatched) + list(partial) + list(legacy_not or []) + list(risks or [])
    return _dedupe_preserve(pool)[:3]


def _pick_focus(
    sq: dict[str, Any],
    partial: list[str],
    unmatched: list[str],
    h: dict[str, Any],
) -> list[str]:
    focus: list[str] = []
    if sq.get("bills_included") is True and _house_bills_included(h) is None:
        focus.append("核对租金是否包含水电与市政等账单")
    if sq.get("commute_preference") or sq.get("near_station"):
        focus.append("用地图核对高峰时段通勤时间")
    dep = h.get("deposit")
    rent = _house_rent(h)
    if dep is not None and rent is not None:
        try:
            if float(dep) > float(rent) * 5:
                focus.append("核对押金金额与退还条件")
        except (TypeError, ValueError):
            pass
    if sq.get("couple_friendly") and _house_couple_friendly(h) is None:
        focus.append("向房东或平台确认是否允许情侣同住")
    for u in unmatched[:2]:
        if u not in focus and len(focus) < 3:
            focus.append("跟进：%s" % u[:60])
    for p in partial[:2]:
        if "样本" in p or "核实" in p or "未" in p:
            if p not in focus and len(focus) < 3:
                focus.append(p[:80])
    return _dedupe_preserve(focus)[:3]


def build_explain_v2(
    house: dict[str, Any],
    structured_query: dict[str, Any],
    base_scores: dict[str, Any] | None = None,
    legacy_explain: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    用户需求 vs 房源属性 → explain_v2（对照 structured_query 逐项解释，不单独依赖 final_score）。
    legacy_explain: 可选，含 why_good / why_not / risks，用于补充 strengths / tradeoffs。
    """
    sq = structured_query or {}
    h = house or {}
    rent = _house_rent(h)

    m1, p1, u1 = _explain_budget(sq, h, rent)
    m2, p2, u2 = _explain_bedrooms_and_type(sq, h)
    m3, p3, u3 = _explain_location(sq, h)
    m4, p4, u4 = _explain_bills_furnished_couple(sq, h)
    m5, p5, u5 = _explain_commute_station(sq, h)
    m6, p6, u6 = _explain_safety_quiet(sq)

    matched = _dedupe_preserve(m1 + m2 + m3 + m4 + m5 + m6)
    partial = _dedupe_preserve(p1 + p2 + p3 + p4 + p5 + p6)
    unmatched = _dedupe_preserve(u1 + u2 + u3 + u4 + u5 + u6)

    leg = legacy_explain or {}
    why_good = list(leg.get("why_good") or [])
    why_not = list(leg.get("why_not") or [])
    risks = list(leg.get("risks") or [])

    strengths = _pick_strengths(matched, why_good, base_scores)
    tradeoffs = _pick_tradeoffs(partial, unmatched, why_not, risks)
    focus = _pick_focus(sq, partial, unmatched, h)

    return {
        "matched_preferences": matched,
        "partial_matches": partial,
        "unmatched_preferences": unmatched,
        "top_strengths": strengths,
        "tradeoffs": tradeoffs,
        "user_focus_points": focus,
    }


def build_match_summary(explain_v2: dict[str, Any], decision: str) -> str:
    """
    根据 matched / partial / unmatched / tradeoffs 与 decision 拼一段短摘要（适合直接展示）。
    """
    d = (decision or "").strip().upper()
    matched = explain_v2.get("matched_preferences") or []
    partial = explain_v2.get("partial_matches") or []
    unmatched = explain_v2.get("unmatched_preferences") or []
    tradeoffs = explain_v2.get("tradeoffs") or []

    m0 = matched[0] if matched else ""
    t0 = tradeoffs[0] if tradeoffs else (partial[0] if partial else "")
    u0 = unmatched[0] if unmatched else ""

    if d == "RECOMMENDED":
        core = "整体较符合你的检索条件"
        if m0:
            core = "该房源在「%s」等方面匹配较好" % m0[:40]
        tail = ""
        if t0:
            tail = "；需注意：%s" % t0[:50]
        elif partial and not tradeoffs:
            tail = "；部分维度建议进一步确认"
        return (core + tail + "。")[:220]

    if d == "CAUTION":
        base = "该房源部分满足需求，但存在需要权衡或核实的点"
        if u0:
            base = "与部分核心条件存在差距（如：%s）" % u0[:45]
        if t0:
            base += "；主要妥协在：%s" % t0[:45]
        return (base + "，建议看房前再确认细节。")[:220]

    base = "该房源与当前输入条件的匹配度偏低"
    if u0:
        base = "在「%s」等方面与需求差距较大" % u0[:45]
    return (base + "，不建议作为首选。")[:220]


def build_recommendation_summary(
    structured_query: dict[str, Any],
    recommendations: list[dict[str, Any]],
) -> dict[str, Any]:
    """整体层最小说明：便于 /api/ai-analyze 顶层展示。"""
    sq = structured_query or {}
    parts: list[str] = []
    if sq.get("budget_max") or sq.get("budget_min"):
        parts.append("预算")
    if sq.get("bedrooms") is not None or sq.get("room_type"):
        parts.append("房型")
    if sq.get("city") or sq.get("area") or sq.get("postcode"):
        parts.append("位置")
    if sq.get("commute_preference") or sq.get("near_station"):
        parts.append("通勤")
    query_summary = (
        "已根据%s等条件进行匹配。" % "、".join(parts)
        if parts
        else "已根据自然语言解析结果进行房源排序与解释。"
    )

    top_reason = "当前列表按综合得分排序，请结合 explain_v2 查看逐条说明。"
    main_tradeoff = "部分样本可能缺少 bill/通勤等字段，以下单条解释中的「需核实」为准。"

    if recommendations:
        first = recommendations[0]
        ev2 = first.get("explain_v2") if isinstance(first.get("explain_v2"), dict) else {}
        mp = ev2.get("matched_preferences") or []
        if mp:
            top_reason = "排名靠前房源主要在「%s」等维度表现较好。" % mp[0][:50]
        tr = ev2.get("tradeoffs") or []
        if tr:
            main_tradeoff = "常见妥协点：%s" % tr[0][:80]

    return {
        "query_summary": query_summary,
        "top_match_reason": top_reason,
        "main_tradeoff": main_tradeoff,
    }

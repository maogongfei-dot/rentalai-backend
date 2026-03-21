# P4 Phase3: 房源推荐详情 / Explain 展开（字段兼容层 + Streamlit expander）
from __future__ import annotations

from typing import Any


def _as_dict(v: Any) -> dict[str, Any]:
    return v if isinstance(v, dict) else {}


def _as_list_str(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        s = v.strip()
        return [s] if s else []
    if isinstance(v, list):
        out: list[str] = []
        for x in v:
            if x is None:
                continue
            s = str(x).strip()
            if s:
                out.append(s)
        return out
    return []


def _first_str(*vals: Any) -> str:
    for v in vals:
        if v is None:
            continue
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _fmt_score(v: Any) -> str:
    if v is None:
        return "—"
    try:
        return "%.2f" % float(v)
    except (TypeError, ValueError):
        s = str(v).strip()
        return s if s else "—"


def _score_components_from_top_export(th: dict[str, Any]) -> list[tuple[str, str]]:
    lines: list[tuple[str, str]] = []
    scores = th.get("scores") if isinstance(th.get("scores"), dict) else {}
    for k, v in scores.items():
        label = str(k).replace("_", " ").title()
        if isinstance(v, (int, float)):
            lines.append((label, _fmt_score(v)))
        elif isinstance(v, dict):
            lines.append((label, str(v)))
        else:
            s = str(v).strip()
            if s:
                lines.append((label, s))
    reasons = th.get("reasons") if isinstance(th.get("reasons"), dict) else {}
    for k, v in reasons.items():
        label = str(k).replace("_", " ").title() + " (note)"
        for line in _as_list_str(v):
            lines.append((label, line))
            break
    return lines


def _weighted_lines_from_explain(explain: dict[str, Any]) -> list[tuple[str, str]]:
    wb = explain.get("weighted_breakdown") if isinstance(explain.get("weighted_breakdown"), dict) else {}
    out: list[tuple[str, str]] = []
    for dim, entry in wb.items():
        label = str(dim).replace("_", " ").title()
        if isinstance(entry, dict):
            parts = []
            for key in ("score", "weight", "weighted_value", "weighted_score"):
                if entry.get(key) is not None:
                    parts.append("%s=%s" % (key, entry.get(key)))
            r = entry.get("reason") or entry.get("note")
            if r:
                parts.append(str(r))
            out.append((label, "; ".join(parts) if parts else str(entry)))
        else:
            out.append((label, str(entry)))
    return out


def _collect_explain_bullets(
    expl: dict[str, Any],
    explanation: dict[str, Any],
    analysis: dict[str, Any],
    uf: dict[str, Any],
    final_rec: dict[str, Any],
    extra_lists: list[list[str]] | None = None,
) -> tuple[str, list[str]]:
    summary = _first_str(
        expl.get("summary"),
        expl.get("explain_summary"),
        expl.get("recommendation_summary"),
        explanation.get("summary"),
        explanation.get("recommendation_summary"),
        final_rec.get("summary") if isinstance(final_rec.get("summary"), str) else None,
    )
    bullets: list[str] = []
    for key in (
        "key_positives",
        "top_positive_reasons",
        "why_recommend",
        "top_reasons",
        "recommendation_reason",
    ):
        bullets.extend(_as_list_str(expl.get(key)))
    bullets.extend(_as_list_str(explanation.get("reason")))
    bullets.extend(_as_list_str(analysis.get("supporting_reasons")))
    bullets.extend(_as_list_str(uf.get("reason")))
    pr = final_rec.get("primary_recommendation")
    if isinstance(pr, dict) and pr.get("reason"):
        bullets.extend(_as_list_str(pr.get("reason")))
    if extra_lists:
        for lst in extra_lists:
            bullets.extend(lst)
    # 去重保序
    seen: set[str] = set()
    uniq: list[str] = []
    for b in bullets:
        k = b.lower()
        if k not in seen:
            seen.add(k)
            uniq.append(b)
    return summary, uniq


def _collect_risk_lines(
    expl: dict[str, Any],
    explanation: dict[str, Any],
    analysis: dict[str, Any],
    uf: dict[str, Any],
    trace: dict[str, Any],
    extra: list[str] | None = None,
) -> list[str]:
    lines: list[str] = []
    for key in ("key_risks", "top_risk_reasons", "warnings", "negatives"):
        lines.extend(_as_list_str(expl.get(key)))
    lines.extend(_as_list_str(explanation.get("risk_note")))
    lines.extend(_as_list_str(uf.get("risk_note")))
    lines.extend(_as_list_str(analysis.get("primary_blockers")))
    lines.extend(_as_list_str(analysis.get("missing_information")))
    lines.extend(_as_list_str(trace.get("blocker_trace")))
    lines.extend(_as_list_str(trace.get("risk_trace_reasons")))
    if extra:
        lines.extend(extra)
    seen: set[str] = set()
    out: list[str] = []
    for x in lines:
        k = x.lower()
        if k not in seen:
            seen.add(k)
            out.append(x)
    return out


def build_analyze_detail_bundle(result: dict[str, Any], listing_context: dict[str, Any] | None) -> dict[str, Any]:
    result = _as_dict(result)
    ctx = _as_dict(listing_context)
    payload = result.get("unified_decision_payload") or {}
    if not payload and isinstance(result.get("unified_decision"), dict):
        ud = result["unified_decision"]
        status = {
            "overall_recommendation": ud.get("overall_recommendation"),
            "decision_confidence": ud.get("decision_confidence"),
        }
        decision = {
            "final_summary": ud.get("final_summary"),
        }
        analysis = {
            "supporting_reasons": ud.get("supporting_reasons") or [],
            "primary_blockers": ud.get("primary_blockers") or [],
            "missing_information": ud.get("missing_information") or [],
        }
        uf = {
            "summary": ud.get("user_facing_summary"),
            "reason": ud.get("user_facing_reason") or [],
            "risk_note": ud.get("user_facing_risk_note") or [],
        }
        trace = {
            "blocker_trace": ud.get("blocker_trace") or [],
            "risk_trace_reasons": [],
        }
        expl = _as_dict(result.get("explanation_summary"))
        explanation = _as_dict(result.get("explanation"))
    else:
        status = _as_dict(payload.get("status"))
        decision = _as_dict(payload.get("decision"))
        analysis = _as_dict(payload.get("analysis"))
        uf = _as_dict(payload.get("user_facing"))
        trace = _as_dict(payload.get("trace"))
        expl = _as_dict(result.get("explanation_summary"))
        explanation = _as_dict(result.get("explanation"))

    final_rec = _as_dict(result.get("final_recommendation"))
    th = _as_dict(result.get("top_house_export"))
    explain_block = _as_dict(th.get("explain"))

    title = _first_str(
        ctx.get("title"),
        ctx.get("listing_title"),
        uf.get("summary"),
    )
    if not title:
        if ctx.get("postcode"):
            title = "Listing · %s" % str(ctx["postcode"]).strip()
        elif ctx.get("area"):
            title = "Listing · %s" % str(ctx["area"]).strip()
        else:
            title = "Untitled Listing"

    rec_label = _first_str(status.get("overall_recommendation"), decision.get("final_summary")) or "—"
    summ, bullets = _collect_explain_bullets(expl, explanation, analysis, uf, final_rec)
    neg_factors = _as_list_str(explain_block.get("top_negative_factors"))
    risk_lines = _collect_risk_lines(
        expl, explanation, analysis, uf, trace, extra=neg_factors
    )

    score_components = _score_components_from_top_export(th)
    weighted = _weighted_lines_from_explain(explain_block)
    if not weighted and isinstance(expl.get("weighted_breakdown"), dict):
        weighted = _weighted_lines_from_explain({"weighted_breakdown": expl["weighted_breakdown"]})

    return {
        "ok": bool(result.get("success")),
        "error_message": _first_str(result.get("message")) or None,
        "overview": {
            "title": title,
            "rent_pcm": ctx.get("rent"),
            "bedrooms": ctx.get("bedrooms"),
            "postcode": ctx.get("postcode") or ctx.get("area"),
            "property_type": ctx.get("property_type"),
            "final_score": result.get("property_score"),
            "total_score": result.get("property_score"),
            "recommendation_label": rec_label,
        },
        "explain_summary_text": summ,
        "explain_bullets": bullets,
        "score_component_lines": score_components,
        "weighted_lines": weighted,
        "risk_lines": risk_lines,
        "source_block": {
            "source": ctx.get("source"),
            "listing_id": ctx.get("listing_id"),
            "source_url": ctx.get("source_url"),
        },
    }


def build_batch_detail_bundle(row: dict[str, Any]) -> dict[str, Any]:
    row = _as_dict(row)
    im = _as_dict(row.get("input_meta"))
    if not row.get("success"):
        return {
            "ok": False,
            "error_message": _first_str(_as_dict(row.get("error")).get("message"), str(row.get("error") or "")),
            "overview": {
                "title": "Listing #%s" % row.get("index", "?"),
                "rent_pcm": im.get("rent"),
                "bedrooms": im.get("bedrooms"),
                "postcode": im.get("postcode") or im.get("area"),
                "property_type": im.get("property_type"),
                "final_score": None,
                "total_score": None,
                "recommendation_label": "Failed",
            },
            "explain_summary_text": "",
            "explain_bullets": [],
            "score_component_lines": [],
            "weighted_lines": [],
            "risk_lines": [],
            "source_block": {
                "source": im.get("source"),
                "listing_id": im.get("listing_id"),
                "source_url": im.get("source_url"),
            },
        }

    status_block = _as_dict(row.get("status"))
    dec = _as_dict(row.get("decision"))
    analysis = _as_dict(row.get("analysis"))
    uf = _as_dict(row.get("user_facing"))
    trace = _as_dict(row.get("trace"))
    expl = _as_dict(row.get("explanation_summary"))
    explanation = {}
    final_rec = {}
    th = _as_dict(row.get("top_house_export"))
    explain_block = _as_dict(th.get("explain"))

    title = "Listing #%s" % row.get("index", "?")
    if uf.get("summary"):
        title = "%s · %s" % (title, str(uf["summary"]).strip()[:60])

    summ, bullets = _collect_explain_bullets(
        expl,
        explanation,
        analysis,
        uf,
        final_rec,
        extra_lists=[row.get("recommended_reasons") or []],
    )
    risk_extra = _as_list_str(row.get("concerns")) + _as_list_str(row.get("risks"))
    risk_lines = _collect_risk_lines(expl, explanation, analysis, uf, trace, extra=risk_extra)
    risk_lines.extend(_as_list_str(explain_block.get("top_negative_factors")))

    score_components = _score_components_from_top_export(th)
    weighted = _weighted_lines_from_explain(explain_block)
    if not weighted and isinstance(expl.get("weighted_breakdown"), dict):
        weighted = _weighted_lines_from_explain({"weighted_breakdown": expl["weighted_breakdown"]})

    rec_label = _first_str(status_block.get("overall_recommendation"), dec.get("final_summary"))
    if not rec_label:
        rec_label = str(row.get("decision_code") or "—")

    return {
        "ok": True,
        "error_message": None,
        "overview": {
            "title": title,
            "rent_pcm": im.get("rent"),
            "bedrooms": im.get("bedrooms"),
            "postcode": im.get("postcode") or im.get("area"),
            "property_type": im.get("property_type"),
            "final_score": row.get("score"),
            "total_score": row.get("score"),
            "recommendation_label": rec_label,
        },
        "explain_summary_text": summ,
        "explain_bullets": bullets,
        "score_component_lines": score_components,
        "weighted_lines": weighted,
        "risk_lines": risk_lines,
        "source_block": {
            "source": im.get("source"),
            "listing_id": im.get("listing_id"),
            "source_url": im.get("source_url"),
        },
    }


def render_listing_detail_expander(
    st: Any,
    bundle: dict[str, Any],
    *,
    expander_key: str,
    title: str | None = None,
) -> None:
    """在卡片内展示可折叠详情（Streamlit expander = 轻量详情面板，兼容 1.28）。"""
    from web_ui.product_copy import (
        DETAIL_LINK_LISTING,
        DETAIL_NO_EXPLAIN_SUMMARY,
        DETAIL_NO_REASONS,
        DETAIL_NO_RISKS,
        DETAIL_NO_SCORE_COMPONENTS,
        DETAIL_SECTION_EXPLAIN,
        DETAIL_SECTION_OVERVIEW,
        DETAIL_SECTION_RISK,
        DETAIL_SECTION_SCORE,
        DETAIL_SECTION_SOURCE,
        DETAIL_WEIGHTED,
        VIEW_DETAILS,
    )

    _title = VIEW_DETAILS if not title else title
    b = bundle if isinstance(bundle, dict) else {}
    try:
        exp_ctx = st.expander(_title, expanded=False, key=expander_key)
    except TypeError:
        exp_ctx = st.expander(_title, expanded=False)
    with exp_ctx:
        if not b.get("ok") and b.get("error_message"):
            st.error(b["error_message"])

        st.markdown("### %s" % DETAIL_SECTION_OVERVIEW)
        ov = _as_dict(b.get("overview"))
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Title**")
            st.write(ov.get("title") or "—")
            st.markdown("**Rent / month**")
            try:
                r = ov.get("rent_pcm")
                st.write("£{:,.0f}".format(float(r)) if r is not None else "—")
            except (TypeError, ValueError):
                st.write("—")
            st.markdown("**Bedrooms**")
            st.write(ov.get("bedrooms") if ov.get("bedrooms") is not None else "—")
        with c2:
            st.markdown("**Postcode**")
            st.write(ov.get("postcode") or "—")
            st.markdown("**Property type**")
            st.write(ov.get("property_type") or "—")
            st.markdown("**Total score**")
            st.write(_fmt_score(ov.get("final_score") or ov.get("total_score")))
        st.markdown("**Recommendation**")
        st.info(ov.get("recommendation_label") or "—")

        st.markdown("### %s" % DETAIL_SECTION_EXPLAIN)
        es = _first_str(b.get("explain_summary_text"))
        if es:
            st.markdown(es)
        else:
            st.caption(DETAIL_NO_EXPLAIN_SUMMARY)
        bl = b.get("explain_bullets") if isinstance(b.get("explain_bullets"), list) else []
        if bl:
            for line in bl:
                st.markdown("- %s" % line)
        elif not es:
            st.caption(DETAIL_NO_REASONS)

        st.markdown("### %s" % DETAIL_SECTION_SCORE)
        sc_lines = b.get("score_component_lines") if isinstance(b.get("score_component_lines"), list) else []
        wt_lines = b.get("weighted_lines") if isinstance(b.get("weighted_lines"), list) else []
        if sc_lines:
            for lab, val in sc_lines:
                st.markdown("- **%s:** %s" % (lab, val))
        else:
            st.caption(DETAIL_NO_SCORE_COMPONENTS)
        if wt_lines:
            st.markdown("**%s**" % DETAIL_WEIGHTED)
            for lab, val in wt_lines:
                st.markdown("- **%s:** %s" % (lab, val))

        st.markdown("### %s" % DETAIL_SECTION_RISK)
        risks = b.get("risk_lines") if isinstance(b.get("risk_lines"), list) else []
        if risks:
            for line in risks:
                st.markdown("- %s" % line)
        else:
            st.success(DETAIL_NO_RISKS)

        st.markdown("### %s" % DETAIL_SECTION_SOURCE)
        src = _as_dict(b.get("source_block"))
        st.markdown("**Source:** %s" % (src.get("source") or "—"))
        st.markdown("**Listing ID:** %s" % (src.get("listing_id") or "—"))
        url = src.get("source_url")
        if isinstance(url, str) and url.strip():
            st.markdown("[%s](%s)" % (DETAIL_LINK_LISTING, url.strip()))

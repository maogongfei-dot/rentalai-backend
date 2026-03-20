# P4 Phase1: 统一房源结果卡片（Streamlit）— 兼容 /analyze 与 /analyze-batch 行结构
from __future__ import annotations

from typing import Any


def _clean_str(v: Any, *, max_len: int | None = None) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    if not s:
        return ""
    if max_len is not None and len(s) > max_len:
        return s[: max_len - 1] + "…"
    return s


def _fmt_money(v: Any) -> str:
    if v is None:
        return "—"
    try:
        return "£{:,.0f}".format(float(v))
    except (TypeError, ValueError):
        return _clean_str(v) or "—"


def _fmt_scalar(v: Any, empty: str = "—") -> str:
    if v is None:
        return empty
    if isinstance(v, bool):
        return "Yes" if v else "No"
    s = str(v).strip()
    return s if s else empty


def _first_summary(*candidates: Any) -> str:
    for c in candidates:
        if c is None:
            continue
        if isinstance(c, str):
            t = c.strip()
            if t:
                return t
        if isinstance(c, list) and c:
            s = _clean_str(c[0])
            if s:
                return s
    return ""


def _recommendation_tier(status: dict, decision: dict) -> tuple[str, str]:
    """(展示标签, 内部种类: recommended | not_recommended | uncertain)"""
    text = ""
    if isinstance(status, dict):
        text = _clean_str(status.get("overall_recommendation"))
    if not text and isinstance(decision, dict):
        text = _clean_str(decision.get("final_summary"), max_len=400) or ""
    t = text.lower()
    if any(
        w in t
        for w in (
            "recommend",
            "proceed",
            "strong",
            "good fit",
            "positive",
        )
    ):
        return "Recommended", "recommended"
    if any(w in t for w in ("avoid", "not recommend", "reject", "unsafe", "high risk")):
        return "Not recommended", "not_recommended"
    return "Review", "uncertain"


def _badge_markdown(label: str, kind: str) -> str:
    if kind == "recommended":
        return f":green[**{label}**]"
    if kind == "not_recommended":
        return f":red[**{label}**]"
    if kind == "error":
        return f":red[**{label}**]"
    return f":orange[**{label}**]"


def build_analyze_card_model(
    result: dict,
    listing_context: dict | None = None,
) -> dict[str, Any]:
    """
    从 app_web 使用的 legacy `result` + 表单规范化后的 listing_context 构建卡片模型。
    不假设引擎返回 title/rent（租金等来自用户输入上下文）。
    """
    result = result if isinstance(result, dict) else {}
    ctx = listing_context if isinstance(listing_context, dict) else {}

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
        user_facing = {
            "summary": ud.get("user_facing_summary"),
        }
        _ex = result.get("explanation_summary")
        expl = _ex if isinstance(_ex, dict) else {}
    else:
        status = payload.get("status") if isinstance(payload.get("status"), dict) else {}
        decision = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
        user_facing = (
            payload.get("user_facing") if isinstance(payload.get("user_facing"), dict) else {}
        )
        expl = result.get("explanation_summary") if isinstance(result.get("explanation_summary"), dict) else {}

    pc = _clean_str(ctx.get("postcode"))
    area = _clean_str(ctx.get("area"))
    title = _first_summary(
        ctx.get("title"),
        ctx.get("listing_title"),
        user_facing.get("summary"),
    )
    if not title:
        if pc:
            title = "Listing · %s" % pc
        elif area:
            title = "Listing · %s" % area
        else:
            title = "Untitled Listing"

    label, kind = _recommendation_tier(status, decision)
    expl_text = _first_summary(
        expl.get("summary"),
        expl.get("recommendation_summary"),
        user_facing.get("summary"),
        decision.get("final_summary"),
    )

    score = result.get("property_score")
    score_v: str
    try:
        score_v = "%.2f" % float(score) if score is not None else "—"
    except (TypeError, ValueError):
        score_v = _fmt_scalar(score)

    return {
        "title": title,
        "rent_pcm": ctx.get("rent"),
        "bedrooms": ctx.get("bedrooms"),
        "postcode": pc or area or None,
        "property_type": ctx.get("property_type"),
        "final_score": score_v,
        "badge_label": label,
        "badge_kind": kind,
        "explain_summary": expl_text,
        "bills_included": ctx.get("bills_included"),
        "furnished": ctx.get("furnished"),
        "source": ctx.get("source"),
        "source_url": ctx.get("source_url"),
        "highlight_top": False,
        "ok": bool(result.get("success")),
        "error_line": _clean_str(result.get("message")) or None,
    }


def build_batch_row_card_model(row: dict, *, highlight_top: bool = False) -> dict[str, Any]:
    """analyze-batch 的 results[] 或 top_1 行 → 卡片模型。"""
    row = row if isinstance(row, dict) else {}
    im = row.get("input_meta") if isinstance(row.get("input_meta"), dict) else {}
    idx = row.get("index")

    if not row.get("success"):
        err = row.get("error")
        msg = ""
        if isinstance(err, dict):
            msg = _clean_str(err.get("message"))
        elif err is not None:
            msg = _clean_str(err)
        return {
            "title": "Listing #%s — analysis failed" % idx if idx is not None else "Listing — analysis failed",
            "rent_pcm": im.get("rent"),
            "bedrooms": im.get("bedrooms"),
            "postcode": None,
            "property_type": None,
            "final_score": "—",
            "badge_label": "Failed",
            "badge_kind": "error",
            "explain_summary": msg or "This property could not be scored.",
            "bills_included": im.get("bills_included"),
            "furnished": None,
            "source": im.get("source"),
            "source_url": im.get("source_url"),
            "highlight_top": highlight_top,
            "ok": False,
            "error_line": msg or None,
        }

    status_block = row.get("status") if isinstance(row.get("status"), dict) else {}
    dec = row.get("decision") if isinstance(row.get("decision"), dict) else {}
    uf = row.get("user_facing") if isinstance(row.get("user_facing"), dict) else {}
    expl = row.get("explanation_summary") if isinstance(row.get("explanation_summary"), dict) else {}

    code = _clean_str(row.get("decision_code")) or "uncertain"
    label_map = {
        "recommended": "Recommended",
        "not_recommended": "Not recommended",
        "uncertain": "Review",
        "N/A": "Review",
    }
    label = label_map.get(code, "Review")
    kind = code if code in ("recommended", "not_recommended") else "uncertain"
    if code == "N/A":
        kind = "uncertain"

    expl_text = _first_summary(
        expl.get("summary"),
        expl.get("recommendation_summary"),
        uf.get("summary"),
        dec.get("final_summary"),
        (row.get("recommended_reasons") or [None])[0],
    )

    score = row.get("score")
    try:
        score_v = "%.2f" % float(score) if score is not None else "—"
    except (TypeError, ValueError):
        score_v = _fmt_scalar(score)

    title = "Listing #%s" % idx if idx is not None else "Listing"
    short = _clean_str(uf.get("summary"), max_len=48)
    if short:
        title = "%s · %s" % (title, short)

    return {
        "title": title,
        "rent_pcm": im.get("rent"),
        "bedrooms": im.get("bedrooms"),
        "postcode": im.get("postcode") or im.get("area"),
        "property_type": im.get("property_type"),
        "final_score": score_v,
        "badge_label": label,
        "badge_kind": kind,
        "explain_summary": expl_text,
        "bills_included": im.get("bills_included"),
        "furnished": im.get("furnished"),
        "source": im.get("source"),
        "source_url": im.get("source_url"),
        "highlight_top": highlight_top,
        "ok": True,
        "error_line": None,
    }


def render_listing_result_card(model: dict[str, Any]) -> None:
    """根据卡片模型渲染一块结果卡片（缺失字段安全降级）。"""
    import streamlit as st

    def _card_outer():
        """Streamlit ≥1.29 支持 border；旧版回退为普通 container。"""
        try:
            return st.container(border=True)
        except TypeError:
            return st.container()

    m = model if isinstance(model, dict) else {}
    title = _clean_str(m.get("title")) or "Untitled Listing"
    highlight = bool(m.get("highlight_top"))
    score_show = _fmt_scalar(m.get("final_score") or m.get("total_score"), "—")

    with _card_outer():
        if highlight:
            st.success("Top recommendation in this batch")

        top_l, top_r = st.columns([4, 1])
        with top_l:
            st.markdown("### %s" % title)
        with top_r:
            st.markdown(
                _badge_markdown(
                    str(m.get("badge_label") or "Review"),
                    str(m.get("badge_kind") or "uncertain"),
                )
            )

        if not m.get("ok") and m.get("error_line"):
            st.caption(":warning: %s" % m["error_line"])

        mid1, mid2, mid3, mid4 = st.columns(4)
        with mid1:
            st.markdown("**Rent / month**")
            st.markdown(_fmt_money(m.get("rent_pcm")))
        with mid2:
            st.markdown("**Bedrooms**")
            st.markdown(_fmt_scalar(m.get("bedrooms")))
        with mid3:
            st.markdown("**Postcode**")
            st.markdown(_fmt_scalar(m.get("postcode")))
        with mid4:
            st.markdown("**Property type**")
            st.markdown(_fmt_scalar(m.get("property_type")))

        st.markdown("---")
        sc1, sc2 = st.columns([1, 2])
        with sc1:
            st.markdown("**Total score**")
            st.markdown("### %s" % score_show)
        with sc2:
            st.markdown("**Summary**")
            summ = _clean_str(m.get("explain_summary"))
            if summ:
                st.markdown(summ)
            else:
                st.caption("No explanation summary for this run.")

        st.markdown("---")
        ft1, ft2, ft3 = st.columns(3)
        with ft1:
            st.markdown("**Bills included**")
            st.markdown(_fmt_scalar(m.get("bills_included"), "—"))
        with ft2:
            st.markdown("**Furnished**")
            st.markdown(_fmt_scalar(m.get("furnished"), "—"))
        with ft3:
            st.markdown("**Source**")
            st.markdown(_fmt_scalar(m.get("source"), "—"))

        url = _clean_str(m.get("source_url"))
        if url:
            st.markdown("[Open listing link](%s)" % url)

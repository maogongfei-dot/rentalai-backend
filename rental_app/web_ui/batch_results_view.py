# P4 Phase4: analyze-batch 结果分区、Top Picks、统计摘要（Streamlit）
from __future__ import annotations

from typing import Any

from web_ui.listing_detail_panel import build_batch_detail_bundle
from web_ui.listing_result_card import build_batch_row_card_model, render_listing_result_card
from web_ui.result_ui import card_spacing, section_header


def _safe_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _index(r: dict[str, Any]) -> Any:
    return r.get("index")


def _rows_by_index(displayed: list[dict[str, Any]]) -> dict[Any, dict[str, Any]]:
    out: dict[Any, dict[str, Any]] = {}
    for r in displayed:
        if isinstance(r, dict):
            out[r.get("index")] = r
    return out


def _api_top_candidates(batch_data: dict[str, Any]) -> list[dict[str, Any]]:
    """兼容 top_3 / recommended_listings / top_recommendations（列表项为完整行或仅 index）。"""
    bd = batch_data if isinstance(batch_data, dict) else {}
    for key in ("top_3_recommendations", "recommended_listings", "top_recommendations"):
        v = bd.get(key)
        if isinstance(v, list) and v:
            return [x for x in v if isinstance(x, dict)]
    t1 = bd.get("top_1_recommendation")
    if isinstance(t1, dict) and t1.get("success"):
        return [t1]
    return []


def select_top_picks_from_batch(
    displayed: list[dict[str, Any]],
    batch_data: dict[str, Any],
    *,
    limit: int = 3,
) -> tuple[list[dict[str, Any]], set[Any]]:
    """
    在「当前筛选+排序」后的列表中选出最多 limit 条 Top。
    优先顺序：API 的 top_3 / recommended 列表中且仍出现在 displayed 中的项 → 不足则按 displayed 顺序补齐。
    """
    disp = [r for r in displayed if isinstance(r, dict)]
    by_idx = _rows_by_index(disp)
    picked: list[dict[str, Any]] = []
    chosen: set[Any] = set()

    for cand in _api_top_candidates(batch_data):
        if len(picked) >= limit:
            break
        idx = cand.get("index")
        if idx in by_idx:
            row = by_idx[idx]
            picked.append(row)
            chosen.add(idx)
        elif cand.get("success") and ("input_meta" in cand or "decision_code" in cand):
            # 完整行但未在 displayed（被筛掉）则跳过
            continue

    if len(picked) < limit:
        for r in disp:
            if len(picked) >= limit:
                break
            if not r.get("success"):
                continue
            ix = _index(r)
            if ix in chosen:
                continue
            picked.append(r)
            chosen.add(ix)

    return picked[:limit], chosen


def partition_remaining_for_batch(
    remaining: list[dict[str, Any]],
    *,
    score_mid_threshold: float = 55.0,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Other good matches vs review needed。
    recommended → good；not_recommended / 失败 → review；uncertain/N/A 按分数阈值。
    """
    good: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    for r in remaining:
        if not isinstance(r, dict):
            continue
        if not r.get("success"):
            review.append(r)
            continue
        code = str(r.get("decision_code") or "").strip().lower()
        if code == "recommended":
            good.append(r)
        elif code == "not_recommended":
            review.append(r)
        else:
            sc = _safe_float(r.get("score"))
            if sc is not None and sc >= score_mid_threshold:
                good.append(r)
            else:
                review.append(r)
    return good, review


def render_batch_stats_row(st: Any, stats: dict[str, Any], lab: dict[str, str]) -> None:
    section_header(st, lab.get("p4_batch_stats_title", "Result summary"), level=4)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric(lab.get("p4_stat_total", "Total analyzed"), int(stats.get("total", 0)))
    with c2:
        st.metric(lab.get("p4_stat_succeeded", "Succeeded"), int(stats.get("succeeded", 0)))
    with c3:
        st.metric(lab.get("p4_stat_top", "Top picks (view)"), int(stats.get("top_n", 0)))
    with c4:
        st.metric(lab.get("p4_stat_good", "Other good matches"), int(stats.get("good", 0)))
    with c5:
        st.metric(lab.get("p4_stat_review", "Review needed"), int(stats.get("review", 0)))
    st.caption(
        lab.get("p4_stat_showing_caption", "Showing %d of %d after filters")
        % (int(stats.get("shown", 0)), int(stats.get("total", 0))),
    )


def render_top_picks_section(
    st: Any,
    top_rows: list[dict[str, Any]],
    *,
    lab: dict[str, str],
    detail_key_prefix: str = "p4_detail_batch",
) -> None:
    section_header(
        st,
        lab.get("p4_batch_top_picks_title", "Top picks"),
        level=3,
        caption=lab.get("p4_batch_top_picks_caption", ""),
    )
    if not top_rows:
        st.info(lab.get("p4_batch_top_picks_empty", "No listings to highlight in this view."))
        return
    n = len(top_rows)
    cols = st.columns(n)
    for i, row in enumerate(top_rows):
        with cols[i]:
            render_listing_result_card(
                build_batch_row_card_model(row, highlight_top=True),
                detail_bundle=build_batch_detail_bundle(row),
                detail_expander_key="%s_top_%s" % (detail_key_prefix, row.get("index", i)),
                top_rank=i + 1,
                visual_tier="top_pick",
            )


def render_tier_listing_cards(
    st: Any,
    title: str,
    rows: list[dict[str, Any]],
    *,
    lab: dict[str, str],
    empty_msg: str,
    detail_key_prefix: str = "p4_detail_batch",
    show_debug_expander: bool = True,
    debug_display_text_fn=None,
) -> None:
    section_header(st, title, level=3)
    if not rows:
        st.caption(empty_msg)
        return
    clean = [r for r in rows if isinstance(r, dict)]
    for i, row in enumerate(clean):
        render_listing_result_card(
            build_batch_row_card_model(row, highlight_top=False),
            detail_bundle=build_batch_detail_bundle(row),
            detail_expander_key="%s_%s" % (detail_key_prefix, row.get("index", "x")),
            visual_tier="default",
        )
        if show_debug_expander and row.get("success") and debug_display_text_fn is not None:
            with st.expander(
                lab.get("p4_batch_debug_bullets", "Listing #%s — bullets (debug)")
                % (row.get("index", "?")),
                expanded=False,
            ):
                st.markdown("**decision_code:** `%s`" % (row.get("decision_code") or "N/A"))
                st.markdown("**Recommended**")
                for _ln in (row.get("recommended_reasons") or [])[:8]:
                    st.markdown("- %s" % debug_display_text_fn(_ln, ""))
                st.markdown("**Concerns**")
                for _ln in (row.get("concerns") or [])[:6]:
                    st.markdown("- %s" % debug_display_text_fn(_ln, ""))
        if i < len(clean) - 1:
            card_spacing(st)


def render_batch_partitioned_listings(
    st: Any,
    *,
    lab: dict[str, str],
    batch_data: dict[str, Any],
    rows_raw: list[dict[str, Any]],
    displayed: list[dict[str, Any]],
    debug_display_text_fn,
    detail_key_prefix: str = "p4_detail_batch",
) -> None:
    """Top 分区 + Good + Review；依赖当前 displayed 顺序/筛选结果。"""
    top_rows, top_ix = select_top_picks_from_batch(displayed, batch_data, limit=3)
    remaining = [r for r in displayed if isinstance(r, dict) and _index(r) not in top_ix]
    good_rows, review_rows = partition_remaining_for_batch(remaining)

    stats = {
        "total": len(rows_raw),
        "shown": len(displayed),
        "succeeded": sum(1 for r in rows_raw if isinstance(r, dict) and r.get("success")),
        "top_n": len(top_rows),
        "good": len(good_rows),
        "review": len(review_rows),
    }
    render_batch_stats_row(st, stats, lab)

    render_top_picks_section(st, top_rows, lab=lab, detail_key_prefix=detail_key_prefix)

    st.divider()
    render_tier_listing_cards(
        st,
        lab.get("p4_tier_good", "Other good matches"),
        good_rows,
        lab=lab,
        empty_msg=lab.get("p4_tier_good_empty", "No listings in this tier for the current filters."),
        detail_key_prefix=detail_key_prefix,
        show_debug_expander=True,
        debug_display_text_fn=debug_display_text_fn,
    )
    st.divider()
    render_tier_listing_cards(
        st,
        lab.get("p4_tier_review", "Review needed"),
        review_rows,
        lab=lab,
        empty_msg=lab.get("p4_tier_review_empty", "No listings in this tier — great if intentional."),
        detail_key_prefix=detail_key_prefix,
        show_debug_expander=True,
        debug_display_text_fn=debug_display_text_fn,
    )

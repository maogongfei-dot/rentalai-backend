# P5 Phase4：规则型 Agent 解释摘要（无 LLM）
from __future__ import annotations

from typing import Any

from web_ui.agent_refinement import get_missing_intent_fields
from web_ui.batch_results_view import _api_top_candidates
from web_ui.rental_intent import AgentRentalRequest


def resolve_intent_for_insights(
    st_session: Any,
    *,
    normalized_form: dict[str, Any] | None = None,
    batch_request: dict[str, Any] | None = None,
) -> AgentRentalRequest:
    """
    优先使用上次 NL 解析的 `p5_agent_last_intent`；否则 batch 首条 property；否则单条表单规范化结果。
    """
    raw = st_session.get("p5_agent_last_intent")
    if isinstance(raw, dict):
        if (raw.get("raw_query") or "").strip():
            return AgentRentalRequest.from_dict(raw)
        if any(
            raw.get(k) is not None
            for k in (
                "max_rent",
                "target_postcode",
                "preferred_area",
                "bedrooms",
                "property_type",
                "bills_included",
                "furnished",
                "max_commute_minutes",
            )
        ):
            return AgentRentalRequest.from_dict(raw)
    if batch_request is not None:
        props = batch_request.get("properties") if isinstance(batch_request, dict) else None
        if isinstance(props, list) and len(props) > 0:
            return AgentRentalRequest.from_batch_first_property(batch_request)
    if normalized_form is not None:
        return AgentRentalRequest.from_normalized_analyze_form(normalized_form)
    return AgentRentalRequest()


def build_agent_insight_bundle(
    intent: AgentRentalRequest,
    *,
    mode: str,
    single_result: dict[str, Any] | None = None,
    batch_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    输出：headline, short_summary, insight_bullets, caution_items, missing_fields_count
    """
    bullets: list[str] = []
    cautions: list[str] = []
    missing = get_missing_intent_fields(intent)
    n_miss = len(missing)

    # --- 依据了哪些条件 ---
    if intent.max_rent is not None:
        bullets.append(
            "Your **rent ceiling** (~£%s/mo) shaped how tight the budget fit is."
            % (int(intent.max_rent) if intent.max_rent == int(intent.max_rent) else intent.max_rent)
        )
    loc = (intent.preferred_area or "").strip() or (intent.target_postcode or "").strip()
    if loc:
        bullets.append("**Location focus** (%s) was carried into the scenario we scored." % loc)
    if intent.bedrooms is not None:
        bullets.append("**Bedrooms** (%s) were included in the listing assumptions." % intent.bedrooms)
    if intent.property_type:
        bullets.append("**Property type** preference (%s) is noted (metadata may sit in the area line for API rows)." % intent.property_type)
    if intent.max_commute_minutes is not None:
        bullets.append("**Commute cap** (~%s min) was part of the commute input." % intent.max_commute_minutes)
    if intent.bills_included is True:
        bullets.append("You asked for **bills included** — reflected in the bills flag.")
    elif intent.bills_included is False:
        bullets.append("**Bills not included** was set for the scenario.")
    if intent.furnished is True:
        bullets.append("**Furnished** preference is captured in the text/metadata we pass with the area field.")
    elif intent.furnished is False:
        bullets.append("**Unfurnished** preference is captured similarly.")
    if not bullets:
        bullets.append(
            "Few explicit preferences were parsed — we still ran the engine using **safe numeric defaults**."
        )

    headline = "Assistant overview"
    short_summary = ""

    if mode == "single" and isinstance(single_result, dict):
        ok = bool(single_result.get("success"))
        sc = single_result.get("property_score")
        short_summary = (
            "Single-property **/analyze** run — one scenario scored against your form criteria."
        )
        if ok and sc is not None:
            try:
                sf = float(sc)
                headline = "How this listing scored for you"
                short_summary += " Property score **%.1f** — see **Decision** and **View details** below for the full breakdown." % sf
                if sf < 50:
                    cautions.append("Score is on the low side — budget, commute, or location assumptions may be stretching.")
            except (TypeError, ValueError):
                pass
        elif not ok:
            headline = "Analysis completed with issues"
            cautions.append(
                _safe_msg(single_result.get("message"))
                or "The engine flagged issues — check the error message and adjust inputs."
            )

    elif mode == "batch" and isinstance(batch_data, dict):
        rows = batch_data.get("results")
        rows = rows if isinstance(rows, list) else []
        ok_rows = [r for r in rows if isinstance(r, dict) and r.get("success")]
        failed = len(rows) - len(ok_rows)
        scores: list[float] = []
        for r in ok_rows:
            v = r.get("score")
            if v is not None:
                try:
                    scores.append(float(v))
                except (TypeError, ValueError):
                    pass

        if len(rows) == 0:
            headline = "No rows to compare"
            short_summary = "No strong matches were found based on the current constraints — the batch returned **no listing rows**."
            cautions.append("Check the batch request JSON or re-run **Continue to analysis** from the Agent box.")
        else:
            headline = "How we picked what to highlight"
            short_summary = (
                "Compared **%d** listing scenario(s); **%d** scored successfully."
                % (len(rows), len(ok_rows))
            )
            if failed:
                cautions.append("%d row(s) failed validation or the engine — see cards marked as failed." % failed)
            if len(rows) == 1:
                cautions.append(
                    "Only **one** scenario was analyzed — add more properties in a batch JSON for richer comparison."
                )
            if scores:
                mx = max(scores)
                mn = min(scores)
                short_summary += " Scores ranged from **%.1f** to **%.1f**." % (mn, mx)
                if mx < 55:
                    cautions.append(
                        "Top scores are **moderate** — criteria may be tight, or the synthetic scenarios are marginal vs your budget/commute."
                    )
                if mx - mn < 5 and len(scores) > 1:
                    cautions.append("Scores are very close — small input changes may reorder rankings.")

        tops = _api_top_candidates(batch_data)
        if tops:
            bullets.append(
                "**Top recommendation(s)** below mirror the API’s strongest successful rows — use **View details** on each card."
            )

    else:
        short_summary = "No result context attached — showing intent-based notes only."

    if n_miss >= 4:
        cautions.append(
            "Several key preferences are still **unspecified** — refine below or edit the **AI Agent** box, then **Parse** again."
        )
    elif n_miss >= 2:
        cautions.append("Some preferences are missing — adding them usually tightens how useful the summary feels.")

    if (intent.raw_query or "").strip():
        bullets.insert(0, "Original request (NL): kept for traceability; structured fields drive the engine.")

    return {
        "headline": headline,
        "short_summary": short_summary.strip(),
        "insight_bullets": bullets[:8],
        "caution_items": cautions[:6],
        "missing_fields_count": n_miss,
    }


def _safe_msg(v: Any) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    return s[:280] + ("…" if len(s) > 280 else "")

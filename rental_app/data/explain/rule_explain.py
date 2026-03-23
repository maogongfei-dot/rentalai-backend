"""
P10 Phase2 — Rule-based Explain Engine (no LLM).

Aligns score bands with module2_scoring._EXPLAIN_SCORE_STRONG / _EXPLAIN_SCORE_WEAK (80 / 50).
Input: analyze-batch result row and/or multi-source analysis aggregate result.
Output: explain_summary, pros, cons, risk_flags (user-facing English).
"""

from __future__ import annotations

from typing import Any

# Match module2_scoring thresholds for listing-level dimension scores (0–100)
_STRONG = 80.0
_WEAK = 50.0
_TOP_N = 3


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _scores_from_row(row: dict[str, Any]) -> dict[str, float | None]:
    """Normalize dimension scores from batch row (top_house_export.scores or legacy)."""
    row = row if isinstance(row, dict) else {}
    th = row.get("top_house_export") if isinstance(row.get("top_house_export"), dict) else {}
    sc = th.get("scores") if isinstance(th.get("scores"), dict) else {}
    if not sc and isinstance(row.get("scores"), dict):
        sc = row["scores"]
    out: dict[str, float | None] = {
        "price": _to_float(sc.get("price_score")),
        "commute": _to_float(sc.get("commute_score")),
        "bills": _to_float(sc.get("bills_score")),
        "bedrooms": _to_float(sc.get("bedrooms_score")),
        "area": _to_float(sc.get("area_score")),
    }
    return out


_PROS = {
    "price": "Rent looks relatively competitive versus similar listings (price dimension scores well).",
    "commute": "Commute looks relatively workable (commute dimension scores well).",
    "bills": "Bills-related signals look reasonable (bills dimension scores well).",
    "bedrooms": "Bedrooms / layout alignment looks solid versus typical needs.",
    "area": "Area / location fit looks relatively strong.",
}
_CONS = {
    "price": "Rent pressure may be high (price dimension scores on the low side).",
    "commute": "Commute may be a concern (commute dimension scores on the low side).",
    "bills": "Bills-related signals are weaker — confirm what is included.",
    "bedrooms": "Bedrooms / layout match is only moderate.",
    "area": "Area / location fit is only moderate.",
}


def build_p10_explain_for_batch_row(row: dict[str, Any]) -> dict[str, Any]:
    """
    Build explain from a single analyze-batch result row (success or failure).

    Returns:
        explain_summary: str
        pros: list[str]
        cons: list[str]
        risk_flags: list[str]
        dimensions: dict (optional debug: raw scores used)
    """
    row = row if isinstance(row, dict) else {}
    if not row.get("success"):
        return {
            "explain_summary": "This row did not analyze successfully, so we cannot generate a recommendation summary.",
            "pros": [],
            "cons": [],
            "risk_flags": ["Analysis failed or data was insufficient — retry or adjust your search."],
            "dimensions": {},
        }

    scores = _scores_from_row(row)
    pros: list[str] = []
    cons: list[str] = []
    for dim in ("price", "commute", "bills", "bedrooms", "area"):
        s = scores.get(dim)
        if s is None:
            continue
        if s >= _STRONG and len(pros) < _TOP_N:
            pros.append(_PROS[dim])
        elif s <= _WEAK and len(cons) < _TOP_N:
            cons.append(_CONS[dim])

    risk_flags: list[str] = []
    im = row.get("input_meta") if isinstance(row.get("input_meta"), dict) else {}
    if im.get("bills_included") is False:
        risk_flags.append(
            "Bills are not included: budget for utilities and council tax separately and confirm with the agent/landlord."
        )
    pc = im.get("postcode") or im.get("area")
    if isinstance(pc, str) and pc.strip() and (scores.get("area") is not None and scores.get("area", 100) <= _WEAK):
        risk_flags.append(
            "Area fit scores on the low side — double-check transport, amenities, and how the neighbourhood feels for you."
        )
    if scores.get("price") is not None and scores.get("price", 100) <= _WEAK:
        risk_flags.append("Rent looks relatively expensive versus the model — confirm it still fits your monthly budget.")
    if scores.get("commute") is not None and scores.get("commute", 100) <= _WEAK:
        risk_flags.append("Commute scores on the low side — test realistic peak-time travel before you commit.")

    dc = str(row.get("decision_code") or "").strip().lower()
    if dc == "not_recommended":
        risk_flags.append("Overall decision leans cautious — view in person and validate details before proceeding.")

    fs = _to_float(row.get("score"))
    # One-line summary
    if pros and not cons:
        summary = "Overall tilt is positive: %s" % pros[0]
    elif cons and not pros:
        summary = "Main watch-out: %s" % cons[0]
    elif pros and cons:
        summary = "There is a strength around “%s”, but “%s” needs attention." % (
            pros[0][:40],
            cons[0][:40],
        )
    else:
        summary = "Scores are middling across dimensions — decide based on your personal priorities and a real viewing."

    if fs is not None:
        if fs >= 80:
            summary = "Final score is relatively high. " + summary
        elif fs <= 55:
            summary = "Final score is on the low side. " + summary

    return {
        "explain_summary": summary[:500],
        "pros": pros[:_TOP_N],
        "cons": cons[:_TOP_N],
        "risk_flags": risk_flags[:5],
        "dimensions": {k: v for k, v in scores.items() if v is not None},
    }


def _best_success_row_from_msa(msa: dict[str, Any]) -> dict[str, Any] | None:
    env = msa.get("analysis_envelope") if isinstance(msa.get("analysis_envelope"), dict) else {}
    data = env.get("data") if isinstance(env.get("data"), dict) else {}
    results = data.get("results")
    if not isinstance(results, list):
        return None
    best: dict[str, Any] | None = None
    best_score = -1.0
    for r in results:
        if not isinstance(r, dict) or not r.get("success"):
            continue
        fv = _to_float(r.get("score"))
        if fv is None:
            continue
        if fv > best_score:
            best_score = fv
            best = r
    return best


def get_representative_batch_row(msa: dict[str, Any]) -> dict[str, Any] | None:
    """Highest-scoring successful analyze-batch row for UI / summaries (same basis as P10 explain)."""
    return _best_success_row_from_msa(msa)


def build_p10_explain_from_msa_result(msa: dict[str, Any]) -> dict[str, Any]:
    """
    Build a run-level explain for a multi-source analysis result dict
    (uses the highest-scoring successful batch row as representative).
    """
    msa = msa if isinstance(msa, dict) else {}
    row = _best_success_row_from_msa(msa)
    if row is None:
        return {
            "explain_summary": "No successful scored listings in this run — widen the search or retry.",
            "pros": [],
            "cons": [],
            "risk_flags": ["Check scrape results or narrow filters, then try again."],
            "dimensions": {},
        }
    ex = build_p10_explain_for_batch_row(row)
    ex["explain_summary"] = "Top match: " + ex.get("explain_summary", "")
    return ex

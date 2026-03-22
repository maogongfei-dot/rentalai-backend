"""
P10 Phase2 — Rule-based Explain Engine (no LLM).

Aligns score bands with module2_scoring._EXPLAIN_SCORE_STRONG / _EXPLAIN_SCORE_WEAK (80 / 50).
Input: analyze-batch result row and/or multi-source analysis aggregate result.
Output: explain_summary, pros, cons, risk_flags (user-facing Chinese).
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
    "price": "租金维度得分较高，价格相对更有竞争力",
    "commute": "通勤维度得分较高，通勤时间相对更理想",
    "bills": "账单相关维度得分较好",
    "bedrooms": "卧室/户型维度与需求匹配较好",
    "area": "区域/地段匹配度较好",
}
_CONS = {
    "price": "租金维度得分偏低，租金压力可能较大",
    "commute": "通勤维度得分偏低，通勤时间可能偏长",
    "bills": "账单相关维度得分偏低",
    "bedrooms": "卧室/户型匹配度一般",
    "area": "区域/地段匹配度一般",
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
            "explain_summary": "该条分析未成功，暂无法生成推荐理由。",
            "pros": [],
            "cons": [],
            "risk_flags": ["分析失败或数据不足，请重试或调整条件。"],
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
        risk_flags.append("未勾选包账单：可能存在水电煤等额外支出，需自行核实。")
    pc = im.get("postcode") or im.get("area")
    if isinstance(pc, str) and pc.strip() and (scores.get("area") is not None and scores.get("area", 100) <= _WEAK):
        risk_flags.append("区域匹配得分偏低：建议结合治安、交通与生活配套自行核实。")
    if scores.get("price") is not None and scores.get("price", 100) <= _WEAK:
        risk_flags.append("租金维度偏弱：注意是否超出预算或需压缩其他开支。")
    if scores.get("commute") is not None and scores.get("commute", 100) <= _WEAK:
        risk_flags.append("通勤维度偏弱：建议用地图实测高峰通勤时间。")

    dc = str(row.get("decision_code") or "").strip().lower()
    if dc == "not_recommended":
        risk_flags.append("综合决策倾向谨慎：建议结合线下看房与其它信息再决定。")

    fs = _to_float(row.get("score"))
    # One-line summary (Chinese)
    if pros and not cons:
        summary = "整体表现偏积极：%s。" % pros[0]
    elif cons and not pros:
        summary = "需重点关注：%s。" % cons[0]
    elif pros and cons:
        summary = "该房源在「%s」方面较有优势，但「%s」需留意。" % (
            pros[0][:20],
            cons[0][:20],
        )
    else:
        summary = "各维度得分中等，无明显短板也无突出亮点，建议结合个人偏好判断。"

    if fs is not None:
        if fs >= 80:
            summary = "综合分较高。" + summary
        elif fs <= 55:
            summary = "综合分偏低。" + summary

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


def build_p10_explain_from_msa_result(msa: dict[str, Any]) -> dict[str, Any]:
    """
    Build a run-level explain for a multi-source analysis result dict
    (uses the highest-scoring successful batch row as representative).
    """
    msa = msa if isinstance(msa, dict) else {}
    row = _best_success_row_from_msa(msa)
    if row is None:
        return {
            "explain_summary": "本轮分析无成功条目或缺少评分，暂无法生成汇总推荐理由。",
            "pros": [],
            "cons": [],
            "risk_flags": ["请检查抓取结果或缩小筛选条件后重试。"],
            "dimensions": {},
        }
    ex = build_p10_explain_for_batch_row(row)
    ex["explain_summary"] = "【本轮优选条目】 " + ex.get("explain_summary", "")
    return ex

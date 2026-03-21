# P4 Phase2: 分析/搜索条件摘要（纯数据，不含 Streamlit）
from __future__ import annotations

from typing import Any


def _fmt_num(v: Any) -> str:
    if v is None:
        return "—"
    try:
        if float(v) == int(float(v)):
            return str(int(float(v)))
        return str(v)
    except (TypeError, ValueError):
        return str(v).strip() or "—"


def _fmt_bool_pref(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "Yes" if v else "No"
    s = str(v).strip().lower()
    if s in ("yes", "y", "true", "1", "包", "包含"):
        return "Yes"
    if s in ("no", "n", "false", "0"):
        return "No"
    return "—"


def summarize_analyze_context(ctx: dict[str, Any] | None) -> list[tuple[str, str]]:
    """单条 analyze 用的规范化表单上下文 → (标签, 值) 列表。"""
    ctx = ctx if isinstance(ctx, dict) else {}
    out: list[tuple[str, str]] = []
    if ctx.get("budget") is not None:
        out.append(("Budget (£/month)", _fmt_num(ctx.get("budget"))))
    if ctx.get("rent") is not None:
        out.append(("Listing rent (£/month)", _fmt_num(ctx.get("rent"))))
    if ctx.get("target_postcode"):
        out.append(("Target postcode", str(ctx["target_postcode"]).strip()))
    if ctx.get("postcode"):
        out.append(("Listing postcode", str(ctx["postcode"]).strip()))
    if ctx.get("area"):
        out.append(("Area", str(ctx["area"]).strip()))
    if ctx.get("bedrooms") is not None:
        out.append(("Bedrooms", _fmt_num(ctx.get("bedrooms"))))
    if ctx.get("commute_minutes") is not None:
        out.append(("Commute (minutes)", _fmt_num(ctx.get("commute_minutes"))))
    bi = ctx.get("bills_included")
    if bi is not None:
        out.append(("Bills included", _fmt_bool_pref(bi)))
    if ctx.get("furnished") is not None:
        out.append(("Furnished", _fmt_bool_pref(ctx.get("furnished"))))
    if ctx.get("property_type"):
        out.append(("Property type", str(ctx["property_type"]).strip()))
    if ctx.get("source"):
        out.append(("Source", str(ctx["source"]).strip()))
    return out


def summarize_batch_request(request_body: dict[str, Any] | None) -> list[tuple[str, str]]:
    """最近一次 batch 请求 JSON 的轻量摘要。"""
    if not isinstance(request_body, dict):
        return [("Batch", "—")]
    props = request_body.get("properties")
    if not isinstance(props, list):
        return [("Properties", "—")]
    n = len(props)
    out: list[tuple[str, str]] = [("Listings in request", str(n))]
    if n == 0:
        return out
    first = props[0] if isinstance(props[0], dict) else {}
    if first.get("budget") is not None:
        out.append(("Sample budget (£/mo)", _fmt_num(first.get("budget"))))
    if first.get("target_postcode"):
        out.append(("Sample target postcode", str(first["target_postcode"]).strip()))
    if first.get("bedrooms") is not None:
        out.append(("Sample bedrooms", _fmt_num(first.get("bedrooms"))))
    if first.get("bills_included") is not None:
        out.append(("Sample bills included", _fmt_bool_pref(first.get("bills_included"))))
    if first.get("furnished") is not None:
        out.append(("Sample furnished", _fmt_bool_pref(first.get("furnished"))))
    if first.get("property_type"):
        out.append(("Sample property type", str(first["property_type"]).strip()))
    if first.get("source"):
        out.append(("Sample source", str(first["source"]).strip()))
    return out

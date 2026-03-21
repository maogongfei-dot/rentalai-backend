# P4 Phase2: batch 结果前端本地筛选（不含 Streamlit）
from __future__ import annotations

from typing import Any


def collect_top_indices(batch_data: dict[str, Any] | None) -> set[int]:
    """从 batch 响应 data 块收集 Top1 + Top3 的 index。"""
    out: set[int] = set()
    if not isinstance(batch_data, dict):
        return out
    t1 = batch_data.get("top_1_recommendation")
    if isinstance(t1, dict) and t1.get("index") is not None:
        try:
            out.add(int(t1["index"]))
        except (TypeError, ValueError):
            pass
    for x in batch_data.get("top_3_recommendations") or []:
        if isinstance(x, dict) and x.get("index") is not None:
            try:
                out.add(int(x["index"]))
            except (TypeError, ValueError):
                pass
    return out


def collect_source_values(rows: list[dict[str, Any]]) -> list[str]:
    """用于 source 下拉：实际出现过的值；无则返回常用占位列表。"""
    seen: set[str] = set()
    for r in rows:
        if not isinstance(r, dict):
            continue
        im = r.get("input_meta") if isinstance(r.get("input_meta"), dict) else {}
        s = im.get("source")
        if s is None or str(s).strip() == "":
            continue
        seen.add(str(s).strip().lower())
    if not seen:
        return ["manual", "api", "rightmove", "zoopla", "unknown"]
    return sorted(seen)


def _input_meta(row: dict[str, Any]) -> dict[str, Any]:
    im = row.get("input_meta")
    return im if isinstance(im, dict) else {}


def _norm_ptype(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip().lower()


def _decision_code(row: dict[str, Any]) -> str:
    c = row.get("decision_code")
    if c is None:
        return ""
    return str(c).strip().lower()


def _is_review_code(code: str) -> bool:
    return code in ("uncertain", "n/a", "")


def _is_recommended_code(code: str) -> bool:
    return code == "recommended"


def filter_batch_rows(
    rows: list[dict[str, Any]],
    *,
    recommendation: str,
    top_indices: set[int],
    bills: str,
    furnished: str,
    property_type: str,
    source: str,
) -> list[dict[str, Any]]:
    """
    recommendation: all | top_only | recommended_only | review_only
    bills: all | included_only
    furnished: all | furnished_only
    property_type: all | flat | house | studio | room
    source: all | <source string>
    """
    rec = (recommendation or "all").strip().lower()
    bills_f = (bills or "all").strip().lower()
    fur_f = (furnished or "all").strip().lower()
    pt = (property_type or "all").strip().lower()
    src_f = (source or "all").strip().lower()

    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue

        idx = row.get("index")
        try:
            idx_int = int(idx) if idx is not None else -1
        except (TypeError, ValueError):
            idx_int = -1

        code = _decision_code(row)

        if rec == "top_only":
            if idx_int not in top_indices:
                continue
        elif rec == "recommended_only":
            if not row.get("success") or not _is_recommended_code(code):
                continue
        elif rec == "review_only":
            if row.get("success"):
                if _is_recommended_code(code) or code == "not_recommended":
                    continue
            # 失败行视为需关注，保留在 review_only

        if bills_f == "included_only":
            im = _input_meta(row)
            if im.get("bills_included") is not True:
                continue

        if fur_f == "furnished_only":
            im = _input_meta(row)
            if im.get("furnished") is not True:
                continue

        if pt != "all":
            im = _input_meta(row)
            if _norm_ptype(im.get("property_type")) != pt:
                continue

        if src_f != "all":
            im = _input_meta(row)
            sv = _norm_ptype(im.get("source"))
            if sv != src_f:
                continue

        out.append(row)
    return out

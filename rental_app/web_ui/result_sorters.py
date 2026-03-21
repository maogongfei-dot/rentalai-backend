# P4 Phase2: batch 结果前端本地排序（返回新列表，不修改入参）
from __future__ import annotations

from typing import Any


def _input_meta(row: dict[str, Any]) -> dict[str, Any]:
    im = row.get("input_meta")
    return im if isinstance(im, dict) else {}


def _float_key(v: Any, *, nan_replace: float = float("nan")) -> float:
    if v is None:
        return nan_replace
    try:
        return float(v)
    except (TypeError, ValueError):
        return nan_replace


def _row_title(row: dict[str, Any]) -> str:
    uf = row.get("user_facing") if isinstance(row.get("user_facing"), dict) else {}
    s = uf.get("summary")
    if isinstance(s, str) and s.strip():
        return s.strip().lower()
    return "listing %s" % row.get("index", "")


def _row_postcode(row: dict[str, Any]) -> str:
    im = _input_meta(row)
    p = im.get("postcode") or im.get("area") or ""
    return str(p).strip().lower()


def _idx(row: dict[str, Any]) -> Any:
    return row.get("index", 0)


def _key_score_desc(r: dict[str, Any]) -> tuple:
    s = _float_key(r.get("score"))
    if s != s:  # NaN
        return (1, 0.0, _idx(r))
    return (0, -s, _idx(r))


def sort_batch_rows(rows: list[dict[str, Any]], sort_key: str) -> list[dict[str, Any]]:
    sk = (sort_key or "score_desc").strip().lower()
    out = [r for r in rows if isinstance(r, dict)]

    if sk == "score_desc":
        out.sort(key=_key_score_desc)
    elif sk == "rent_asc":
        out.sort(
            key=lambda r: (
                _float_key(_input_meta(r).get("rent"), nan_replace=float("inf")),
                _idx(r),
            )
        )
    elif sk == "rent_desc":
        out.sort(
            key=lambda r: (
                -_float_key(_input_meta(r).get("rent"), nan_replace=float("-inf")),
                _idx(r),
            )
        )
    elif sk == "bedrooms_desc":
        out.sort(
            key=lambda r: (
                -_float_key(_input_meta(r).get("bedrooms"), nan_replace=float("-inf")),
                _idx(r),
            )
        )
    elif sk == "title_asc":
        out.sort(key=lambda r: (_row_title(r), _idx(r)))
    elif sk == "postcode_asc":
        out.sort(key=lambda r: ((_row_postcode(r) or "zzz"), _idx(r)))
    else:
        out.sort(key=_key_score_desc)
    return out

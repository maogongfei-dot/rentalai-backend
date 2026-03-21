# P4 Phase2: filter/sort 纯函数烟测
from __future__ import annotations

from web_ui.result_filters import collect_top_indices, filter_batch_rows
from web_ui.result_sorters import sort_batch_rows


def _row(idx, *, score, rent, code="recommended", bills=True, success=True):
    return {
        "index": idx,
        "success": success,
        "score": score,
        "decision_code": code,
        "input_meta": {"rent": rent, "bills_included": bills},
    }


def test_top_filter():
    rows = [_row(0, score=10, rent=100), _row(1, score=20, rent=200)]
    bd = {"top_3_recommendations": [{"index": 1}]}
    top = collect_top_indices(bd)
    out = filter_batch_rows(rows, recommendation="top_only", top_indices=top, bills="all", furnished="all", property_type="all", source="all")
    assert len(out) == 1 and out[0]["index"] == 1


def test_recommended_only():
    rows = [_row(0, score=1, rent=1, code="recommended"), _row(1, score=2, rent=2, code="uncertain")]
    out = filter_batch_rows(
        rows,
        recommendation="recommended_only",
        top_indices=set(),
        bills="all",
        furnished="all",
        property_type="all",
        source="all",
    )
    assert len(out) == 1


def test_sort_rent_asc():
    rows = [_row(0, score=99, rent=500), _row(1, score=99, rent=100)]
    s = sort_batch_rows(rows, "rent_asc")
    assert [r["index"] for r in s] == [1, 0]


def test_sort_score_desc():
    rows = [_row(0, score=10, rent=1), _row(1, score=30, rent=1), _row(2, score=20, rent=1)]
    s = sort_batch_rows(rows, "score_desc")
    assert [r["index"] for r in s] == [1, 2, 0]


if __name__ == "__main__":
    test_top_filter()
    test_recommended_only()
    test_sort_rent_asc()
    test_sort_score_desc()
    print("test_result_filters_sort: all ok")

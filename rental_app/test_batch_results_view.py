# P4 Phase4: batch 分区逻辑烟测
from __future__ import annotations

from web_ui.batch_results_view import (
    partition_remaining_for_batch,
    select_top_picks_from_batch,
)


def test_select_top_prefers_api_order():
    rows = [
        {"index": 0, "success": True, "score": 10, "decision_code": "recommended"},
        {"index": 1, "success": True, "score": 99, "decision_code": "recommended"},
        {"index": 2, "success": True, "score": 50, "decision_code": "recommended"},
    ]
    bd = {"top_3_recommendations": [{"index": 2, "success": True}, {"index": 0, "success": True}]}
    picked, ix = select_top_picks_from_batch(rows, bd, limit=3)
    assert [r["index"] for r in picked[:2]] == [2, 0]
    assert 1 in ix or len(picked) >= 2


def test_partition():
    rem = [
        {"index": 3, "success": True, "decision_code": "recommended"},
        {"index": 4, "success": True, "decision_code": "uncertain", "score": 60},
        {"index": 5, "success": True, "decision_code": "uncertain", "score": 40},
        {"index": 6, "success": False},
    ]
    g, r = partition_remaining_for_batch(rem, score_mid_threshold=55.0)
    assert len(g) == 2
    assert len(r) == 2


if __name__ == "__main__":
    test_select_top_prefers_api_order()
    test_partition()
    print("test_batch_results_view: all ok")

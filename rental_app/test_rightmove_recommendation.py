# Phase D5：Rightmove 推荐链路单测（在 rental_app 下: python test_rightmove_recommendation.py）
from __future__ import annotations

from ai_recommendation_bridge import run_ai_analyze


def test_fetch_rightmove_mock_has_five_plus():
    from scraper.rightmove_scraper import _mock_listings, fetch_rightmove_listings

    m = _mock_listings({})
    assert len(m) >= 5
    cities = {x.get("city") for x in m}
    assert "Milton Keynes" in cities
    assert "London" in cities
    assert "Manchester" in cities
    rows = fetch_rightmove_listings({"budget_max": 5000})
    assert len(rows) >= 5
    assert rows[0].get("source") == "rightmove"


def test_load_candidate_rightmove():
    from house_candidate_loader import load_candidate_houses

    canon = load_candidate_houses("rightmove", structured_query={"city": "London", "budget_max": 2000})
    assert isinstance(canon, list)
    assert len(canon) >= 1
    assert all("listing_title" in c or c.get("rent") is not None for c in canon)


def test_run_ai_rightmove_recommendations():
    out = run_ai_analyze("1 bed in Milton Keynes under 1200 pcm", dataset="rightmove")
    assert out.get("success") is not False
    recs = out.get("recommendations") or []
    assert isinstance(recs, list)
    assert len(recs) >= 1
    first = recs[0]
    assert "explain_v2" in first
    assert "decision_v2" in first
    summ = out.get("summary") or {}
    assert summ.get("source_mode") or summ.get("scrape_clean_stats")


def test_run_ai_london_studio_bills():
    out = run_ai_analyze("London studio bills included under 1500", dataset="rightmove")
    assert out.get("recommendations")


def test_run_ai_manchester_commute():
    out = run_ai_analyze("Manchester 2 bed near transport", dataset="rightmove")
    assert out.get("recommendations")


def test_market_combined_smoke():
    out = run_ai_analyze("flat in London under 2000", dataset="market_combined")
    assert out.get("recommendations")
    sm = (out.get("summary") or {}).get("source_mode")
    assert isinstance(sm, dict) or sm


if __name__ == "__main__":
    test_fetch_rightmove_mock_has_five_plus()
    test_load_candidate_rightmove()
    test_run_ai_rightmove_recommendations()
    test_run_ai_london_studio_bills()
    test_run_ai_manchester_commute()
    test_market_combined_smoke()
    print("test_rightmove_recommendation: all ok")

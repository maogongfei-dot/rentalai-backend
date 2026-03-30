# Phase D9：explain_engine 单测（rental_app: python test_explain_engine.py）
from __future__ import annotations

import json

from services.deal_engine import rank_deals
from services.explain_engine import (
    build_listing_explanation,
    build_market_recommendation_report,
    build_star_final_verdict,
    build_top_deals_explanations,
    compose_market_analysis_display_zh,
    generate_followup_questions,
)


def _insight():
    return {
        "location": "TestCity",
        "stats": {
            "average_price_pcm": 1200.0,
            "total_listings": 4,
        },
        "bedroom_price_map": {
            "2": {"count": 2, "avg_price": 1300.0, "min_price": 1200.0, "max_price": 1400.0},
        },
        "overall_analysis": {
            "market_price_level": "medium",
            "supply_level": "medium",
            "bedroom_focus": "2",
        },
    }


def test_build_listing_explanation_keys():
    ins = _insight()
    listing = {
        "title": "Test flat",
        "price_pcm": 1000.0,
        "bedrooms": 2,
        "postcode": "E1 1AA",
        "address": "1 Road",
        "image_url": "http://i",
        "listing_url": "http://l",
    }
    out = build_listing_explanation(listing, ins)
    required = {
        "title",
        "deal_score",
        "deal_tag",
        "decision",
        "risk_level",
        "headline",
        "why_recommended",
        "why_not_recommended",
        "risk_flags",
        "price_position",
        "bedroom_position",
        "data_quality",
        "action_suggestion",
        "star_rating",
        "star_reasons",
        "one_line_suggestion",
        "analysis_sections",
        "formatted_analysis_zh",
    }
    assert required <= set(out.keys())
    assert 2 <= len(out["action_suggestion"]) <= 4
    json.dumps(out)


def test_build_top_deals_explanations():
    ins = _insight()
    listings = [
        {
            "title": "A",
            "price_pcm": 2000,
            "bedrooms": 2,
            "postcode": "SW1",
            "address": "x",
            "image_url": "u",
            "listing_url": "http://a",
            "source": "zoopla",
        },
        {
            "title": "B",
            "price_pcm": 900,
            "bedrooms": 2,
            "postcode": "E1",
            "address": "y",
            "image_url": "u",
            "listing_url": "http://b",
            "source": "rightmove",
            "matched_sources": [{"source": "rightmove"}],
        },
    ]
    bundle = build_top_deals_explanations(listings, ins, top_n=2)
    assert bundle["count"] == 2
    assert len(bundle["items"]) == 2
    for it in bundle["items"]:
        assert "star_rating" in it and isinstance(it.get("star_reasons"), list)
        assert 1.0 <= float(it["star_rating"]) <= 5.0
        json.dumps(it)


def test_build_top_deals_with_ranked_deals():
    ins = _insight()
    listings = [
        {"title": "A", "price_pcm": 1100, "bedrooms": 2, "postcode": "E1", "listing_url": "http://x", "image_url": "i"},
    ]
    ranked = rank_deals(listings, ins, top_n=5)
    b2 = build_top_deals_explanations(listings, ins, top_n=5, ranked_deals=ranked)
    assert b2["count"] == 1
    assert b2["items"][0]["title"] == "A"


def test_generate_followup_questions_dynamic_and_default():
    q_high = generate_followup_questions(
        {"final_score": 4.5, "price_score": 1.0, "risk_flag": True, "has_multiple_options": True}
    )
    assert any("中介" in x for x in q_high)
    assert any("bill" in x for x in q_high)
    assert any("砍价" in x for x in q_high)
    assert any("合同" in x for x in q_high)
    assert any("对比" in x for x in q_high)

    q_default = generate_followup_questions({"final_score": 2.0, "price_score": 4.0, "risk_flag": False})
    assert len(q_default) == 1
    assert "继续筛选" in q_default[0]


def test_recommendation_report_empty_listings():
    insight = {
        "location": "Nowhere",
        "stats": {"total_listings": 0},
        "overall_analysis": {
            "market_price_level": "medium",
            "supply_level": "low",
            "bedroom_focus": None,
        },
        "bedroom_price_map": {},
    }
    ranked = rank_deals([], insight, top_n=5)
    r = build_market_recommendation_report("Nowhere", insight, ranked)
    assert r["location"] == "Nowhere"
    assert "summary_sentence" in r
    assert "market_positioning" in r
    assert "market_snapshot_zh" in r and r["market_snapshot_zh"]
    json.dumps(r)


def test_recommendation_report_with_ranked():
    ins = _insight()
    listings = [
        {
            "title": "Cheap",
            "price_pcm": 900,
            "bedrooms": 2,
            "postcode": "E1",
            "address": "1 St",
            "image_url": "u",
            "listing_url": "http://l",
        },
        {
            "title": "High",
            "price_pcm": 2000,
            "bedrooms": 2,
            "postcode": "SW1",
            "address": "2 Rd",
            "image_url": "u",
            "listing_url": "http://h",
        },
    ]
    ranked = rank_deals(listings, ins, top_n=5)
    r = build_market_recommendation_report("TestCity", ins, ranked)
    assert r["overall_recommendation"]
    assert r["best_opportunities"]
    assert len(r["what_to_do_next"]) >= 3
    assert r.get("market_snapshot_zh")
    assert r.get("display_context") and r["display_context"].get("top_n") == 2
    expl = build_top_deals_explanations(listings, ins, top_n=5, ranked_deals=ranked)
    verdict = build_star_final_verdict(expl["items"], ranked["top_deals"], ins, "TestCity")
    assert verdict["best_overall"] and verdict["best_overall"]["title"]
    assert verdict["overall_advice"]
    json.dumps(r)

    txt = compose_market_analysis_display_zh(
        location="TestCity",
        report=r,
        explanations=expl,
        star_final_verdict=verdict,
        ranked_deals=ranked,
        market_insight=ins,
    )
    assert "【结论】" in txt and "【原因】" in txt and "【建议】" in txt and "【下一步】" in txt
    assert "最佳房源推荐" in txt


def _demo_synthetic_top3():
    """Print top 3 headline / decision / why_recommended and summary_sentence (no network)."""
    ins = _insight()
    listings = [
        {
            "title": "Flat A",
            "price_pcm": 950,
            "bedrooms": 2,
            "postcode": "E1",
            "address": "a",
            "image_url": "u",
            "listing_url": "http://a",
        },
        {
            "title": "Flat B",
            "price_pcm": 1150,
            "bedrooms": 2,
            "postcode": "E2",
            "address": "b",
            "image_url": "u",
            "listing_url": "http://b",
        },
        {
            "title": "Flat C",
            "price_pcm": 1800,
            "bedrooms": 2,
            "postcode": "SW1",
            "address": "c",
            "image_url": "u",
            "listing_url": "http://c",
        },
    ]
    ranked = rank_deals(listings, ins, top_n=3)
    expl = build_top_deals_explanations(listings, ins, top_n=3, ranked_deals=ranked)
    rep = build_market_recommendation_report("TestCity", ins, ranked)

    print("--- Top 3: star / reasons ---")
    for it in expl["items"][:3]:
        print(f"  title={it.get('title')!r}")
        print(f"    star_rating: {it.get('star_rating')}")
        print(f"    star_reasons: {it.get('star_reasons')}")
        print(f"    one_line_suggestion: {it.get('one_line_suggestion')}")
    print("--- recommendation_report.summary_sentence ---")
    print(f"  {rep.get('summary_sentence')}")


if __name__ == "__main__":
    test_build_listing_explanation_keys()
    test_build_top_deals_explanations()
    test_build_top_deals_with_ranked_deals()
    test_generate_followup_questions_dynamic_and_default()
    test_recommendation_report_empty_listings()
    test_recommendation_report_with_ranked()
    print("test_explain_engine: all ok")
    _demo_synthetic_top3()

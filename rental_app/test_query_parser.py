# Phase D10：query_parser 单测（rental_app: python test_query_parser.py）
from __future__ import annotations

import json

from services.query_parser import normalize_search_filters, parse_user_housing_query


def test_examples_from_spec():
    q1 = parse_user_housing_query("我想找 Milton Keynes 1000 到 1500 的两居室")
    assert q1.get("min_price") == 1000 and q1.get("max_price") == 1500
    assert q1.get("min_bedrooms") == 2 and q1.get("max_bedrooms") == 2
    assert q1.get("location") == "Milton Keynes"

    q2 = parse_user_housing_query("帮我看看 Nottingham 便宜一点的一居室")
    assert q2.get("flags", {}).get("cheap_preference") is True
    assert q2.get("min_bedrooms") == 1
    assert "Nottingham" in (q2.get("location") or "")

    q3 = parse_user_housing_query("找一下伦敦西北区 2000 以下、2到3居、最好有图")
    assert q3.get("max_price") == 2000
    assert q3.get("min_bedrooms") == 2 and q3.get("max_bedrooms") == 3
    assert q3.get("flags", {}).get("image_required") is True
    assert q3.get("location") == "London"
    assert q3.get("area") == "North West London"

    q4 = parse_user_housing_query("我想看看 DE1 附近的出租房，预算 1200 左右")
    assert q4.get("postcode") == "DE1"
    assert q4.get("target_price") == 1200
    assert q4.get("location") is None


def test_normalize_target_price_band():
    p = parse_user_housing_query("预算 1200 左右")
    n = normalize_search_filters(p)
    assert n["min_price"] is not None and n["max_price"] is not None
    assert n["min_price"] < 1200 < n["max_price"]


def test_cheap_sort():
    p = parse_user_housing_query("便宜 划算 London")
    n = normalize_search_filters(p)
    assert n["sort_by"] == "price_asc"


def test_preference_flags():
    s = parse_user_housing_query("伦敦 2bed 要安全安静 通勤方便 生活便利")
    f = s.get("flags") or {}
    assert f.get("safety_preference") is True
    assert f.get("commute_preference") is True
    assert f.get("lifestyle_preference") is True
    n = normalize_search_filters(s)
    fl = n.get("filters") or {}
    assert fl.get("safety_preference") is True
    assert fl.get("commute_preference") is True
    assert fl.get("lifestyle_preference") is True


def test_empty_safe():
    p = parse_user_housing_query("")
    assert p["intent"] == "market_search"
    json.dumps(p)
    json.dumps(normalize_search_filters(p))


if __name__ == "__main__":
    test_examples_from_spec()
    test_normalize_target_price_band()
    test_cheap_sort()
    test_preference_flags()
    test_empty_safe()
    print("test_query_parser: all ok")

    demos = [
        "我想找 Milton Keynes 1000 到 1500 的两居室",
        "帮我看看 Nottingham 便宜一点的一居室",
        "找一下伦敦西北区 2000 以下、2到3居、最好有图",
        "我想看看 DE1 附近的出租房，预算 1200 左右",
    ]
    for s in demos:
        print("---")
        print(s)
        print(json.dumps(parse_user_housing_query(s), ensure_ascii=False, indent=2))
        print(json.dumps(normalize_search_filters(parse_user_housing_query(s)), ensure_ascii=False, indent=2))

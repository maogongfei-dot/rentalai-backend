# P3 Phase2: 轻量 normalizer 烟测（在 rental_app 下: python test_listing_normalizer.py）
from __future__ import annotations

from data.normalizer.listing_normalizer import (
    normalize_listing_batch,
    normalize_listing_payload,
    to_analyze_payload,
)
from data.schema.listing_schema import is_valid_listing_payload


def test_manual_style():
    d = {
        "source": "manual",
        "rent": 1100,
        "bedrooms": 2,
        "postcode": "sw1a 1aa",
        "bills": "yes",
    }
    L = normalize_listing_payload(d)
    assert L.source == "manual"
    assert L.rent_pcm == 1100.0
    assert L.bedrooms == 2.0
    assert L.postcode == "SW1A 1AA"
    assert L.bills_included is True
    assert L.raw_data is not None
    assert L.normalized_at


def test_api_style():
    d = {
        "price": "£1,250 pcm",
        "bed": "1",
        "post_code": "e2 7nx",
        "commute_minutes": "30",
        "url": "https://example.com/l/1",
    }
    L = normalize_listing_payload(d, source="api")
    assert L.source == "api"
    assert L.rent_pcm == 1250.0
    assert L.bedrooms == 1.0
    assert L.postcode == "E2 7NX"
    assert L.commute_minutes == 30
    assert "example.com" in (L.source_url or "")


def test_rightmove_style():
    d = {
        "source": "rightmove",
        "monthly_rent": 950,
        "displayAddress": "10 Test Street, London",
        "listingId": "rm-999",
        "beds": 1,
    }
    L = normalize_listing_payload(d)
    assert L.source == "rightmove"
    assert L.rent_pcm == 950.0
    assert L.address and "Test Street" in L.address
    assert L.listing_id == "rm-999"


def test_zoopla_style():
    d = {
        "source": "zoopla",
        "rent_pcm": 1400,
        "listingUrn": "zp-abc",
        "full_address": "1 Demo Rd",
        "bathroom": 1,
    }
    L = normalize_listing_payload(d)
    assert L.source == "zoopla"
    assert L.rent_pcm == 1400.0
    assert L.listing_id == "zp-abc"
    assert L.bathrooms == 1.0


def test_batch_and_to_analyze():
    items = [
        {"rent": 1000, "bedrooms": 1, "source": "api"},
        "not-a-dict",  # type: ignore
        {"price": 800, "postcode": "N1 1AA"},
    ]
    Ls = normalize_listing_batch(items, source=None)
    assert len(Ls) == 3
    assert Ls[0].rent_pcm == 1000.0
    assert Ls[1].source == "unknown"
    p = to_analyze_payload(Ls[0], budget=1500)
    assert p.get("rent") == 1000.0
    assert p.get("budget") == 1500


def test_is_valid_after_normalize():
    d = {"address": "Somewhere"}
    assert is_valid_listing_payload(d)
    L = normalize_listing_payload(d)
    assert L.address == "Somewhere"


if __name__ == "__main__":
    test_manual_style()
    test_api_style()
    test_rightmove_style()
    test_zoopla_style()
    test_batch_and_to_analyze()
    test_is_valid_after_normalize()
    print("test_listing_normalizer: all ok")

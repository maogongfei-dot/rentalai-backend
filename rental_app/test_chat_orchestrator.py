# Phase D10-3：chat_orchestrator 单测（mock D6，无网络）
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from services.chat_orchestrator import run_housing_ai_query


def _sample_combined():
    return {
        "success": True,
        "location": "London",
        "total_before_dedupe": 2,
        "total_after_dedupe": 2,
        "sources_used": ["zoopla"],
        "errors": {},
        "listings": [
            {
                "title": "A",
                "price_pcm": 1100,
                "bedrooms": 2,
                "postcode": "E1 1AA",
                "address": "1 St",
                "image_url": "http://img",
                "listing_url": "http://l",
            },
            {
                "title": "B",
                "price_pcm": 1500,
                "bedrooms": 2,
                "postcode": "SW1 1AA",
                "address": "2 Rd",
                "image_url": "",
                "listing_url": "http://l2",
                "furnished": "unfurnished",
            },
        ],
    }


class TestChatOrchestrator(unittest.TestCase):
    @patch("services.chat_orchestrator.get_combined_market_listings")
    def test_happy_path(self, mock_gc):
        mock_gc.return_value = _sample_combined()
        r = run_housing_ai_query("London 2 bed 1000 to 1600")
        self.assertTrue(r["success"])
        self.assertEqual(r["normalized_filters"].get("location"), "London")
        self.assertTrue(r["top_deals"].get("top_deals"))
        self.assertGreaterEqual(r["explanations"].get("count", 0), 1)
        self.assertTrue(r["recommendation_report"].get("summary_sentence"))
        self.assertIsInstance(r["errors"], dict)
        json.dumps(r)

    def test_missing_location(self):
        r = run_housing_ai_query("")
        self.assertTrue(r["success"])
        self.assertTrue(r.get("message"))
        self.assertEqual(r["top_deals"]["top_deals"], [])

    @patch("services.chat_orchestrator.get_combined_market_listings")
    def test_postcode_only(self, mock_gc):
        mock_gc.return_value = _sample_combined()
        r = run_housing_ai_query("DE1 flat budget 1200")
        self.assertTrue(r["success"])
        self.assertEqual(r["normalized_filters"].get("postcode"), "DE1")

    @patch("services.chat_orchestrator.get_combined_market_listings")
    def test_location_no_price(self, mock_gc):
        mock_gc.return_value = _sample_combined()
        r = run_housing_ai_query("Nottingham 1 bed")
        self.assertTrue(r["success"])
        self.assertIn("Nottingham", r["normalized_filters"].get("location") or "")

    @patch("services.chat_orchestrator.get_combined_market_listings")
    def test_cheap_sort(self, mock_gc):
        mock_gc.return_value = _sample_combined()
        r = run_housing_ai_query("Nottingham cheap 1 bed")
        self.assertEqual(r["normalized_filters"].get("sort_by"), "price_asc")

    @patch("services.chat_orchestrator.get_combined_market_listings")
    def test_image_required_filters(self, mock_gc):
        mock_gc.return_value = _sample_combined()
        r = run_housing_ai_query("London 最好有图 2 bed")
        tops = r["top_deals"].get("top_deals") or []
        for x in tops:
            self.assertTrue((x.get("image_url") or "").strip())


if __name__ == "__main__":
    unittest.main()

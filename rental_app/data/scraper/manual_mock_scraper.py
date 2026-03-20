# P3 Phase4: 本地调试用 mock 抓取器 — 非真实数据源
from __future__ import annotations

from typing import Any

from .base_scraper import BaseListingScraper


class ManualMockScraper(BaseListingScraper):
    """
    占位 source=manual_mock，返回少量 dict，字段名尽量贴近 normalizer 别名（price/rent、beds、url 等）。
    """

    source = "manual_mock"

    def scrape(
        self,
        query: dict[str, Any] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        _ = query
        rows: list[dict[str, Any]] = [
            {
                "source": self.source,
                "listing_id": "mock-001",
                "title": "Mock 2-bed flat near station",
                "price": "£1,450 pcm",
                "bedrooms": 2,
                "address": "10 Mock Street",
                "postcode": "E1 6AN",
                "url": "https://example.com/listings/mock-001",
                "property_type": "flat",
            },
            {
                "source": self.source,
                "listing_id": "mock-002",
                "title": "Studio for rent",
                "rent_pcm": 980,
                "bed": 0,
                "full_address": "99 Demo Lane, London",
                "post_code": "N1 5QT",
                "link": "https://example.com/listings/mock-002",
            },
            {
                "source": self.source,
                "listing_id": "mock-003",
                "title": "House share room",
                "monthly_rent": 650,
                "beds": 1,
                "postcode": "SW1A 1AA",
                "listing_url": "https://example.com/listings/mock-003",
                "bills_included": True,
            },
        ]
        return rows[: max(0, limit)]

# P3 Phase4: 统一抓取入口 — 仅数据层，不写路由、不写 storage
from __future__ import annotations

from typing import Any

from data.normalizer.listing_normalizer import normalize_listing_batch
from data.schema.listing_schema import ListingSchema

from .base_scraper import BaseListingScraper
from .manual_mock_scraper import ManualMockScraper
from .rightmove_scraper import RightmoveScraper
from .zoopla_scraper import ZooplaScraper

# 多平台入口：统一经 SCRAPER_REGISTRY + scrape_listings；新增平台在此注册 key 即可。
# 顺序约定：rightmove（已落地）→ zoopla（准备中）→ manual_mock（开发）→ unknown（占位）。
SCRAPER_PLATFORM_ORDER: tuple[str, ...] = (
    "rightmove",
    "zoopla",
    "manual_mock",
    "unknown",
)


class UnknownListingScraper(BaseListingScraper):
    """source=unknown：占位空结果，便于与注册表对齐。"""

    source = "unknown"

    def scrape(
        self,
        query: dict[str, Any] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        _ = query, limit
        return []


SCRAPER_REGISTRY: dict[str, type[BaseListingScraper]] = {
    "rightmove": RightmoveScraper,
    "zoopla": ZooplaScraper,
    "manual_mock": ManualMockScraper,
    "unknown": UnknownListingScraper,
}
# 校验与 SCRAPER_PLATFORM_ORDER 一致（轻量文档化，避免注册表漂移）
assert set(SCRAPER_PLATFORM_ORDER) == set(SCRAPER_REGISTRY.keys())


def scrape_listings(
    source: str,
    query: dict[str, Any] | None = None,
    limit: int = 20,
    *,
    normalized: bool = False,
) -> list[dict[str, Any]] | list[ListingSchema]:
    """
    按 source 分发到对应 Scraper；normalized=False 返回原始 dict，
    True 时走 Phase2 normalize_listing_batch（不写入 storage）。
    无法识别的 source：返回空列表。
    """
    key = (source or "").strip().lower()
    cls = SCRAPER_REGISTRY.get(key)
    if cls is None:
        return []
    scraper = cls()
    raw = scraper.scrape(query=query, limit=limit)
    if not normalized:
        return raw
    return normalize_listing_batch(raw, source=key)


# 最小示例（README 亦有）
if __name__ == "__main__":
    print(len(scrape_listings("manual_mock", normalized=False)))
    print(type(scrape_listings("manual_mock", normalized=True)[0]).__name__)
    print(scrape_listings("rightmove", normalized=False))

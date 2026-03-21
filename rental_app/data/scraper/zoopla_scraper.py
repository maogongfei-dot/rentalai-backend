# P3 Phase4 + P6: Zoopla 占位 — **第二优先**（Rightmove 单平台闭环后再扩）
# P6 Phase1：仍无网络/Playwright
from __future__ import annotations

from typing import Any

from .base_scraper import BaseListingScraper


class ZooplaScraper(BaseListingScraper):
    """当前不发起 HTTP/浏览器；`scrape` 返回 []。"""

    source = "zoopla"

    def scrape(
        self,
        query: dict[str, Any] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        _ = query, limit
        return []

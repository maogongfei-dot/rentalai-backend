# P3 Phase4 + P6: Rightmove 占位 — **第一优先**真实平台（先于 Zoopla 打通闭环）
# P6 Phase1：仍无网络/Playwright；Phase2+ 可内部调用 data.scraper.playwright_runner
from __future__ import annotations

from typing import Any

from .base_scraper import BaseListingScraper


class RightmoveScraper(BaseListingScraper):
    """当前不发起 HTTP/浏览器；`scrape` 返回 []。真实逻辑见 `playwright_runner` 规划文档。"""

    source = "rightmove"

    def scrape(
        self,
        query: dict[str, Any] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        _ = query, limit
        return []

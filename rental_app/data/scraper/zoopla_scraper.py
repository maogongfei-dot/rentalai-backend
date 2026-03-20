# P3 Phase4: Zoopla 占位骨架 — 非实际抓取器，后续在此接入真实逻辑
from __future__ import annotations

from typing import Any

from .base_scraper import BaseListingScraper


class ZooplaScraper(BaseListingScraper):
    """当前阶段不发起任何 HTTP / 浏览器请求；scrape 恒为空列表。"""

    source = "zoopla"

    def scrape(
        self,
        query: dict[str, Any] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        _ = query, limit
        return []

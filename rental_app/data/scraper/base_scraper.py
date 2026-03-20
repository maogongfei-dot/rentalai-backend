# P3 Phase4: 抓取层统一协议（无联网、无 HTML）
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseListingScraper(ABC):
    """
    各平台真实抓取器未来均实现此协议。
    scrape 仅返回原始 list[dict]，标准化由 normalizer / 入口 scrape_listings(normalized=True) 负责。
    """

    source: str

    @abstractmethod
    def scrape(
        self,
        query: dict[str, Any] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """返回原始房源 dict 列表；当前骨架无网络请求。"""
        ...

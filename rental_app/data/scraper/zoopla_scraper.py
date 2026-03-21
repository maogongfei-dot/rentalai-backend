# P3 Phase4 + P6 Phase5：Zoopla 第二平台 — **骨架与字段策略**（无真实列表解析）
# 下一阶段（Phase6+）：在保持本文件结构与 raw 字段策略前提下，接入 Playwright + selectors。
from __future__ import annotations

from typing import Any

from .base_scraper import BaseListingScraper

# ---------------------------------------------------------------------------
# 未来 Zoopla raw dict 输出策略（与 Rightmove 对齐，便于同一套 normalizer）
#
# 单条 dict 建议至少包含（命名与 Rightmove 一致；值保持原始/半原始）：
#   - source: "zoopla"
#   - listing_id: str
#   - title: str | None
#   - price 或 rent: 原始租金文案或数字（normalizer 识别 rent / price）
#   - bedrooms 或 beds: str | int | None
#   - address: str | None
#   - url 与 source_url: 绝对链接（与 Rightmove 相同，便于 _base_alias_map）
#   - property_type: str | None
#   - summary 或 description: str | None
#
# Pipeline 层可在入库前注入 scraped_at（与 rightmove_pipeline 一致）。
# ---------------------------------------------------------------------------

# Phase6+ 默认列表 URL 占位（真实 URL 以 query["search_url"] / ScraperRunConfig 为准）
DEFAULT_ZOOPLA_TO_RENT_URL = "https://www.zoopla.co.uk/to-rent/"


def _parse_zoopla_listing_card(_card: Any, _page_url: str) -> dict[str, Any] | None:
    """
    Phase6+：从单张列表卡片解析一条 raw dict（字段见模块顶部说明）。
    **P6 Phase5**：未实现，恒返回 None。
    """
    _ = _card, _page_url
    return None


def _extract_zoopla_listing_cards(
    _page: Any,
    _base_url: str,
    _limit: int,
) -> tuple[int, list[dict[str, Any]]]:
    """
    Phase6+：在列表页上定位卡片根节点、去重 listing_id、截断至 limit。
    返回 (dom 卡片数或近似值, raw 列表)。
    **P6 Phase5**：未实现，恒返回 (0, [])。
    """
    _ = _page, _base_url, _limit
    return 0, []


class ZooplaScraper(BaseListingScraper):
    """
    Zoopla 租赁列表页抓取器骨架。

    **P6 Phase5**：不发起真实解析；`scrape` 恒返回 []。
    未来将内部复用 `playwright_runner.browser_page_for_scraper_config` + `ScraperRunConfig`
    （与 Rightmove 相同配置结构，勿另起一套 config）。
    """

    source = "zoopla"

    def __init__(self) -> None:
        # 与 RightmoveScraper 对齐，供调试与 pipeline 统计（Phase6+ 填值）
        self.last_scrape_stats: dict[str, int] | None = None

    def scrape(
        self,
        query: dict[str, Any] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        _ = query, limit
        self.last_scrape_stats = {"cards_in_dom": 0, "parsed_ok": 0}
        return []

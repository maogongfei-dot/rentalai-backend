# P6 Phase1: 真实抓取运行配置（仅结构定义，不执行抓取）
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from data.scraper.types import ScraperQueryDict


@dataclass
class ScraperRunConfig:
    """
    未来 Playwright 抓取一次任务的参数（P6 Phase2+ 消费）。

    链路规划（见 docs/P6_PLAYWRIGHT_INTEGRATION_PLAN.md）:
    ScraperRunConfig -> playwright_runner / platform scraper -> raw dicts
    -> normalize_listing_batch -> ListingSchema -> storage（由上层编排，非本文件职责）。
    """

    source: str
    """平台名：**rightmove** / **zoopla** 等与 `SCRAPER_REGISTRY` key 对齐；与平台无关的通用任务参数共用本 dataclass，不另建 Zoopla 专用 config。"""

    search_url: str = ""
    """列表页或搜索入口 URL（Phase2+ 必填校验可放在 runner）。"""

    query: ScraperQueryDict = field(default_factory=dict)
    """附加查询参数（如邮编、半径）；与 URL 并存时可二选一，由实现约定。"""

    max_pages: int = 1
    """列表翻页上限；调试期建议 1。"""

    limit: int = 20
    """最多采集条数上限（与 scraper.scrape limit 语义对齐）。"""

    headless: bool = True
    """Playwright 是否无头；本地调试可置 False。"""

    save_raw_html: bool = False
    """是否落盘原始 HTML 片段（仅调试；Phase2+ 实现）。"""

    save_screenshots: bool = False
    """是否保存截图（仅调试；Phase2+ 实现）。"""

    output_dir: str | None = None
    """原始 HTML/截图输出目录；None 表示使用项目默认临时策略（Phase2+）。"""

    def to_runner_kwargs(self) -> dict[str, Any]:
        """未来 runner 入参扁平化；Phase1 仅占位。"""
        return {
            "source": self.source,
            "search_url": self.search_url,
            "query": dict(self.query),
            "max_pages": self.max_pages,
            "limit": self.limit,
            "headless": self.headless,
            "save_raw_html": self.save_raw_html,
            "save_screenshots": self.save_screenshots,
            "output_dir": self.output_dir,
        }

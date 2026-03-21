# P6 Phase1: Playwright 运行器占位 — 不启动浏览器、不访问网络
from __future__ import annotations

from typing import Any

from data.scraper.scraper_config import ScraperRunConfig


def run_playwright_scrape(config: ScraperRunConfig) -> list[dict[str, Any]]:
    """
    未来由 **RightmoveScraper** / **ZooplaScraper**（Phase2+）在需要浏览器渲染时调用。

    规划职责：
    - 按 config 启动 Playwright（Chromium）
    - 打开 search_url、处理翻页（max_pages）、抽取列表项原始字段
    - 返回 **list[dict]**（与 BaseListingScraper.scrape 输出一致），再交给 normalizer

    **P6 Phase1**：不安装、不调用 Playwright；恒返回空列表。
    第一优先平台：**Rightmove**；第二：**Zoopla**。manual_mock 不走本 runner。
    """
    _ = config
    return []


def playwright_available() -> bool:
    """Phase2+ 可改为检测 playwright 是否已安装；Phase1 恒 False。"""
    return False

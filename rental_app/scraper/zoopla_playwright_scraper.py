# Phase D3：Zoopla 列表页 Playwright 抓取骨架（可扩展；与 requests 路径共用解析）
# 安装说明见仓库 README「Phase D3：Zoopla Playwright 抓取模式」
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# 与 data/scraper/playwright_runner 思路一致：弱化自动化指纹（Zoopla / Cloudflare）
_CHROMIUM_ARGS = ["--disable-blink-features=AutomationControlled"]
_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36"
)


def fetch_zoopla_listings_playwright(query: dict) -> list[dict[str, Any]]:
    """
    用 Chromium 打开 Zoopla 搜索页，取渲染后 HTML，再复用 ``zoopla_scraper`` 的 BS4 解析。

    本阶段为骨架：解析成功则返回列表；失败或 0 条则返回 ``[]``（由统一入口决定是否回退 requests/mock）。
    """
    from scraper.zoopla_scraper import _build_search_url, _parse_html_listings

    q = dict(query or {})
    url = _build_search_url(q)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("playwright package not installed; skip fetch_zoopla_listings_playwright")
        return []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=_CHROMIUM_ARGS)
            try:
                context = browser.new_context(
                    user_agent=_DEFAULT_UA,
                    locale="en-GB",
                    viewport={"width": 1366, "height": 768},
                )
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                # Phase D3：与 test_zoopla_playwright_probe 类似 — 先等卡片，再补固定延迟便于 CSR 渲染
                try:
                    page.wait_for_selector(
                        '[data-testid="listing-card-content"]',
                        timeout=25_000,
                    )
                except Exception:
                    pass
                try:
                    page.wait_for_timeout(2_500)
                except Exception:
                    pass
                html = page.content()
                final_url = page.url or url
            finally:
                browser.close()
    except Exception as exc:
        logger.warning("fetch_zoopla_listings_playwright failed: %s", exc)
        return []

    rows = _parse_html_listings(html, final_url, q)
    logger.info(
        "zoopla playwright: url=%s html_len=%s parsed=%s",
        final_url,
        len(html),
        len(rows),
    )
    return rows


def test_zoopla_playwright_probe(query: dict) -> dict[str, Any]:
    """
    最小探针：验证能否用浏览器打开搜索页并拿到 HTML（不要求解析出完整 listing）。

    返回结构便于脚本/人工验收 Phase D3。
    """
    from scraper.zoopla_scraper import _build_search_url

    q = dict(query or {})
    url = _build_search_url(q)
    base: dict[str, Any] = {
        "ok": False,
        "mode": "playwright",
        "url": url,
        "html_length": 0,
        "listing_count_guess": 0,
        "note": "",
    }

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        base["note"] = "playwright Python package not installed (pip install playwright)"
        return base

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=_CHROMIUM_ARGS)
            try:
                context = browser.new_context(
                    user_agent=_DEFAULT_UA,
                    locale="en-GB",
                    viewport={"width": 1366, "height": 768},
                )
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                try:
                    page.wait_for_timeout(2_000)
                except Exception:
                    pass
                html = page.content()
                final_url = page.url or url
            finally:
                browser.close()
    except Exception as exc:
        base["note"] = f"playwright probe failed: {exc}"
        return base

    n = len(re.findall(r'data-testid="listing-card-content"', html))
    base["ok"] = True
    base["url"] = final_url
    base["html_length"] = len(html)
    base["listing_count_guess"] = n
    base["note"] = "playwright page fetch succeeded"
    return base


__all__ = ["fetch_zoopla_listings_playwright", "test_zoopla_playwright_probe"]

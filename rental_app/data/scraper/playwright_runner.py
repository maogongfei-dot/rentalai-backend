# P6 Phase2+: Playwright 页面探针 + Phase3 浏览器会话复用
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, TypedDict

from data.scraper.scraper_config import ScraperRunConfig


class PageProbeResult(TypedDict):
    """`run_playwright_page_probe` 返回结构（便于类型提示与测试断言）。"""

    success: bool
    source: str
    url: str
    final_url: str | None
    page_title: str | None
    html_length: int | None
    error: str | None


def _default_debug_output_dir() -> Path:
    return Path(__file__).resolve().parent / "samples" / "debug"


def _resolve_output_dir(config: ScraperRunConfig) -> Path:
    if config.output_dir:
        return Path(config.output_dir).expanduser().resolve()
    return _default_debug_output_dir()


def _optional_debug_artifacts(
    page: Any,
    html: str,
    config: ScraperRunConfig,
) -> None:
    """save_raw_html / save_screenshots；任意一步失败不影响主流程。"""
    out = _resolve_output_dir(config)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_source = "".join(c if c.isalnum() else "_" for c in config.source) or "probe"
    try:
        out.mkdir(parents=True, exist_ok=True)
    except OSError:
        return
    if config.save_raw_html:
        try:
            fp = out / f"{safe_source}_{stamp}.html"
            fp.write_text(html, encoding="utf-8")
        except OSError:
            pass
    if config.save_screenshots:
        try:
            fp = out / f"{safe_source}_{stamp}.png"
            page.screenshot(path=str(fp), full_page=False)
        except OSError:
            pass


def run_playwright_page_probe(config: ScraperRunConfig) -> PageProbeResult:
    """
    最小页面探针：启动 Chromium、打开 `search_url`、读取标题与 HTML 长度。
    不抽取房源卡片；异常时返回 `success=False` 与 `error` 文案，不向外抛。
    """
    url = (config.search_url or "").strip()
    base: PageProbeResult = {
        "success": False,
        "source": config.source,
        "url": url,
        "final_url": None,
        "page_title": None,
        "html_length": None,
        "error": None,
    }
    if not url:
        base["error"] = "search_url is empty"
        return base

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        base["error"] = (
            "playwright package not installed; run: pip install playwright"
        )
        return base

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=config.headless)
            try:
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                final = page.url
                title = page.title()
                html = page.content()
                base["final_url"] = final
                base["page_title"] = title or None
                base["html_length"] = len(html)
                base["success"] = True
                if config.save_raw_html or config.save_screenshots:
                    _optional_debug_artifacts(page, html, config)
            finally:
                browser.close()
    except Exception as e:  # noqa: BLE001 — 探针需吞掉异常并结构化返回
        base["error"] = f"{type(e).__name__}: {e}"
    return base


# 与 `probe_rightmove_search` 同义，供调用方任选命名
def run_rightmove_probe(
    search_url: str | None = None,
    *,
    headless: bool = True,
    save_raw_html: bool = False,
    save_screenshots: bool = False,
    output_dir: str | None = None,
    query: dict[str, Any] | None = None,
    max_pages: int = 1,
    limit: int = 20,
) -> PageProbeResult:
    """
    Rightmove 专用探针入口：仅验证列表/搜索页能否打开。
    未传 `search_url` 时使用站内租房入口页（可换为自有测试 URL）。
    """
    default = "https://www.rightmove.co.uk/property-to-rent.html"
    cfg = ScraperRunConfig(
        source="rightmove",
        search_url=(search_url or default).strip(),
        query=dict(query or {}),
        max_pages=max_pages,
        limit=limit,
        headless=headless,
        save_raw_html=save_raw_html,
        save_screenshots=save_screenshots,
        output_dir=output_dir,
    )
    return run_playwright_page_probe(cfg)


# 与 run_rightmove_probe 同义，便于按「probe」命名调用
probe_rightmove_search = run_rightmove_probe


@contextmanager
def browser_page_for_scraper_config(
    config: ScraperRunConfig,
) -> Iterator[Any]:
    """
    启动 Chromium、打开 `config.search_url`、在 `domcontentloaded` 后把 `Page` 交给调用方。
    由调用方负责列表页等待与解析；关闭浏览器在上下文结束时完成。
    """
    url = (config.search_url or "").strip()
    if not url:
        raise ValueError("search_url is empty")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=config.headless)
        try:
            page = browser.new_page()
            page.set_default_timeout(30_000)
            page.goto(url, wait_until="domcontentloaded", timeout=90_000)
            yield page
        finally:
            browser.close()


def run_playwright_scrape(config: ScraperRunConfig) -> list[dict[str, Any]]:
    """
    按 `ScraperRunConfig.source` 分发到平台抓取器；返回原始 `list[dict]`。

    **P6 Phase3**：`source=rightmove` 时解析列表页卡片；其余平台仍返回 `[]`。
    """
    key = (config.source or "").strip().lower()
    if key == "rightmove":
        from data.scraper.rightmove_scraper import rightmove_raw_from_config

        return rightmove_raw_from_config(config)
    return []


def playwright_available() -> bool:
    """检测是否已安装 `playwright` Python 包（不校验浏览器是否已 install）。"""
    try:
        import playwright  # noqa: F401

        return True
    except ImportError:
        return False

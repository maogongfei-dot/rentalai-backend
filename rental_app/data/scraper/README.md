# Scraper（P3 Phase4 + P6 Phase1）

## 职责

- 提供 **外部房源来源** 的统一结构：`BaseListingScraper` + 按 `source` 分发的 **`scrape_listings`**。
- **P6 Phase1**：增加 **`ScraperRunConfig`**、**`playwright_runner`** 占位、`selectors/`、`samples/` 目录规划；**仍不** 真实抓取、**不** 运行 Playwright。
- 输出默认为 **`list[dict]`**（原始扁平结构）；需要标准模型时由调用方设 **`normalized=True`**，内部交给 **Phase2 normalizer** → `list[ListingSchema]`。
- **不负责**：storage 持久化、HTTP API 路由、`/analyze` 主流程。

## 支持的 source（平台顺序）

| source | 说明 |
|--------|------|
| `rightmove` | **第一优先**真实平台（P6 规划）；当前 `scrape` 返回 `[]` |
| `zoopla` | **第二优先**；当前 `scrape` 返回 `[]` |
| `manual_mock` | 开发测试用，返回 2～3 条 mock dict（保留） |
| `unknown` | 空列表占位 |

未注册的字符串：**返回空列表**（不抛错）。

## P6 相关文件

| 文件 | 说明 |
|------|------|
| `scraper_config.py` | `ScraperRunConfig`（search_url、max_pages、headless、调试开关等） |
| `playwright_runner.py` | `run_playwright_scrape` 占位，Phase2+ 实现 |
| `types.py` | 轻量类型别名 |
| `selectors/README.md` | 未来选择器说明 |
| `samples/README.md` | 未来脱敏样例 |

规划文档：`docs/P6_PLAYWRIGHT_INTEGRATION_PLAN.md`、`docs/P6_SCRAPER_LOCAL_DEBUG_FLOW.md`。

## 扩展示意

真实抓取：在 `*_scraper.py` 中实现 `scrape()`（或内部调用 `playwright_runner`），保持返回 **`list[dict]`**；**ListingSchema / storage 核心不改**，仅接在 normalizer 之后。

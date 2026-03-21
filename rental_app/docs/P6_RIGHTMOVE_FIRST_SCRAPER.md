# P6 Phase3 — Rightmove 首个真实列表抓取器

## 本阶段已完成

- **`RightmoveScraper.scrape`**：用 Playwright 打开 **租赁搜索结果列表页**（默认单页），在 `[data-testid^="propertyCard-"]` 卡片上抽取原始字段，返回 **`list[dict]`**。
- **复用**：`playwright_runner.browser_page_for_scraper_config`、`ScraperRunConfig`（`search_url`、`limit`、`headless`、`save_raw_html`、`save_screenshots`、`output_dir`）。
- **Selector**：集中在 `data/scraper/selectors/rightmove_selectors.py`。
- **调试**：`query["debug"]` 打印 DOM 卡片数、解析成功条数与一条样本关键字段；`query["save_raw_sample"]=True` 时写入 `data/scraper/samples/debug/rightmove_raw_sample.json`（失败不影响抓取）。
- **CLI**：`scripts/run_rightmove_scrape.py`。
- **`run_playwright_scrape(config)`**：当 `config.source=="rightmove"` 时等价于 `rightmove_raw_from_config(config)`。

## 抓取范围

- **仅列表页、单页**；**不做翻页**；`limit` 为最多返回条数：按 DOM 顺序扫描卡片，**按 `listing_id` 去重**后填满 `limit`（避免重复卡片占位）。
- **不是** `ListingSchema`；**未** 调用 normalizer / storage；**未** 接入 analyze。
- 建议 Phase4 前对 Rightmove **不要**使用 `scrape_listings(..., normalized=True)`（字段映射尚未对齐）。

## 默认 URL

未传 `search_url` / `url` 时使用 `DEFAULT_RIGHTMOVE_SEARCH_URL`（伦敦区域列表，便于本地试跑）。生产调用请传入真实搜索 URL。

## `query` 常用键

| 键 | 说明 |
|----|------|
| `search_url` / `url` | 列表页 URL |
| `headless` | 默认 `True` |
| `debug` | 控制台轻量调试输出 |
| `save_raw_sample` | 写入 `rightmove_raw_sample.json` |
| `save_raw_html` / `save_screenshots` | 与 Phase2 相同，落盘到 `samples/debug/` |

## 本地运行

```bash
cd rental_app
pip install -r requirements.txt
python -m playwright install chromium
python scripts/run_rightmove_scrape.py --limit 5 --debug
```

## 下一阶段（P6 Phase4）

- Rightmove **raw dict → normalizer → ListingSchema → storage** 闭环与编排。

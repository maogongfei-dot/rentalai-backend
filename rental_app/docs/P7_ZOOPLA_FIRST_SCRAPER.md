# P7 Phase1 — Zoopla 首个真实列表抓取器

## 本阶段已完成

- **`ZooplaScraper.scrape`**：Playwright 打开 **租赁搜索结果列表页**（默认伦敦），在 **`[data-testid="regular-listings"] [data-testid="listing-card-content"]`** 上抽取字段，返回 **`list[dict]`**（与 Rightmove raw 形状对齐）。
- **Runner**：复用 **`browser_page_for_scraper_config`**；`playwright_runner` 对 **`source=zoopla`** 使用 **桌面 Chrome UA + `AutomationControlled` 弱化**，以降低 Cloudflare「Just a moment」拦截概率（不保证所有环境通过）。
- **Selector**：`data/scraper/selectors/zoopla_selectors.py`。
- **`run_playwright_scrape`**：`source=zoopla` 时走 **`zoopla_raw_from_config`**。
- **探针**：**`run_zoopla_probe` / `probe_zoopla_search`**（与 Rightmove 探针对称）。
- **CLI**：`scripts/run_zoopla_scrape.py`。
- **调试**：`query["debug"]`、`save_raw_sample` → `samples/debug/zoopla_raw_sample.json`。

## 抓取范围

- **仅列表页、单页**；**不翻页**；`limit` 与 **`listing_id` 去重** 规则同 Rightmove 模式。

## 输出字段（raw）

`source`, `listing_id`, `title`, `price`, `bedrooms`, `address`, `url`, `source_url`, `property_type`（由摘要/正文轻量猜测，可为空）, `summary`。

**不是** `ListingSchema`；**未** 接 `normalize_listing_batch` / `save_listings`（见 Phase2）。

## 本地运行

```bash
cd rental_app
python -m playwright install chromium
python scripts/run_zoopla_scrape.py --limit 5 --debug
python -c "from data.scraper.playwright_runner import run_zoopla_probe; print(run_zoopla_probe())"
```

## 下一阶段（P7 Phase2）

- **Zoopla → normalizer → storage** 闭环（镜像 `run_rightmove_pipeline`）。

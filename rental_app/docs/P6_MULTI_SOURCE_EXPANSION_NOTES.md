# P6 — 多房源平台扩展说明（工程原则）

## 当前状态

- **已接入真实抓取 + 闭环**：**Rightmove**（`RightmoveScraper`、`run_rightmove_pipeline`）。
- **结构准备中**：**Zoopla**（`ZooplaScraper` 骨架、`zoopla_selectors` / `zoopla_pipeline` / 脚本占位；**无真实解析**）。

## 统一分层原则

1. **Scraper**：只负责 **raw `list[dict]`**；不做复杂业务标准化、不写 storage。
2. **Normalizer**：**`normalize_listing_batch(..., source=<platform>)`** → `ListingSchema`；平台差异尽量在 normalizer 已有 dispatch 与别名中消化。
3. **Storage**：**`save_listings`**；去重/更新策略保持在 storage 层，各平台共用。

## Raw 字段约定

- 不同平台 **尽量输出相近字段名**（与 Rightmove 对齐：`listing_id`、`title`、`price`/`rent`、`bedrooms`、`address`、`url`+`source_url`、`property_type`、`summary` 等）。
- 允许原始文本（如带 `£` 的租金）；**避免在 scraper 内做重度清洗**。

## 再扩第三平台时

- 新增 `NewPortalScraper(BaseListingScraper)`、`source` 常量、**注册到 `SCRAPER_REGISTRY`**。
- 新增 `selectors/` 子文件与可选 `pipeline/<portal>_pipeline.py`，**仍复用** `ScraperRunConfig`、Playwright runner、`normalize_listing_batch`、`save_listings`。
- 在 `run_playwright_scrape` 或专用 `*_raw_from_config` 中增加分支，**不另起并行数据体系**。

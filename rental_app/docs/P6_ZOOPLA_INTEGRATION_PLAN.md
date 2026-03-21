# P6 Phase5 — Zoopla 接入规划（结构准备）

## 为什么在 Rightmove 闭环后准备 Zoopla

- Rightmove 已验证 **Playwright → raw dict → `normalize_listing_batch` → `save_listings`** 全链路；第二平台应 **复用同一分层**，只替换「列表页解析」与 selector。
- Zoopla 与 Rightmove 同属英国租赁聚合站，补充房源覆盖面；工程上作为 **registry 第二个真实 source**，风险可控、便于对比两套 DOM 与反爬差异。

## 将如何复用现有架构

| 层 | 复用方式 |
|----|-----------|
| **Scraper** | `ZooplaScraper`（`BaseListingScraper`）+ `SCRAPER_REGISTRY["zoopla"]` + `scrape_listings("zoopla", ...)` |
| **Runner** | 继续用 `ScraperRunConfig` + `browser_page_for_scraper_config`；`run_playwright_scrape` 在 Phase6+ 增加 `zoopla` 分支（或 `zoopla_raw_from_config`） |
| **Normalizer** | 已有 `_normalize_zoopla_payload` + `_base_alias_map`；`normalize_listing_batch(..., source="zoopla")` |
| **Storage** | 共用 `save_listings` / `load_listings_by_source("zoopla")` |
| **Pipeline** | `data/pipeline/zoopla_pipeline.py` 镜像 `run_rightmove_pipeline`（当前仅占位） |

## Zoopla 未来 raw dict 字段策略

与 **Rightmove 对齐**（减少平台差异），单条建议至少包括：

`source`, `listing_id`, `title`, `price`（或 `rent`）, `bedrooms`（或 `beds`）, `address`, `url` **与** `source_url`, `property_type`, `summary`（或 `description`）；`scraped_at` 由 pipeline 注入。

详见 `data/scraper/zoopla_scraper.py` 模块顶部注释。

## 本阶段范围（Phase5）

- 已整理：**zoopla_scraper 骨架**、`selectors/zoopla_selectors.py` 占位、`zoopla_pipeline` 占位、**调试脚本占位**、**注册表顺序说明**、本文档与多平台总览 `P6_MULTI_SOURCE_EXPANSION_NOTES.md`。
- **未实现**：真实 Zoopla 页面 probe、listing 卡片解析、多页抓取、与 storage 的真实写入。

## 下一阶段（Phase6+ 建议）

- 实现 **Zoopla 首个真实列表页抓取器**（单页、`limit`、与 Rightmove 相近的 raw 形状），再落地 `run_zoopla_pipeline` 与可选 `run_zoopla_probe`（仅连通性）。

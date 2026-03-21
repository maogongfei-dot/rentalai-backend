# P7 Phase2 — Zoopla → normalizer → storage 闭环

## 本阶段已完成

- **`data/pipeline/zoopla_pipeline.py`**：`run_zoopla_pipeline` 串联 **ZooplaScraper.scrape** → **`normalize_listing_batch(..., source="zoopla")`** → **`save_listings`**。
- **别名**：`scrape_and_normalize_zoopla`、`run_zoopla_normalization_pipeline`。
- **CLI**：`scripts/run_zoopla_pipeline.py`（与 Rightmove 脚本对称）。
- **调试样本**（可选，失败不影响主流程）：
  - `data/scraper/samples/debug/zoopla_raw_sample.json`
  - `data/scraper/samples/debug/zoopla_normalized_sample.json`
- **`data/pipeline/__init__.py`**：导出 `run_zoopla_normalization_pipeline`。

## 数据流

1. **抓取**：`ZooplaScraper.scrape` → `list[dict]`（P7 Phase1 字段已与 normalizer 别名兼容：`price`、`url`/`source_url`、`bedrooms`、`listing_id`、`summary` 等）。
2. **标准化**：pipeline 注入 **`scraped_at`** 后调用 **`normalize_listing_batch(stamped, source="zoopla")`**（`_normalize_zoopla_payload` + `_base_alias_map`）。
3. **存储**：**`save_listings`**，去重规则与 P3 Phase3 一致（`listing_id`+`source` 优先）。

## 返回结构（`run_zoopla_pipeline`）

| 字段 | 含义 |
|------|------|
| `success` | 抓取无未捕获异常且（若 `persist`）storage 写入成功 |
| `error` | 失败说明 |
| `raw_count` / `normalized_count` | 条数 |
| `normalization_skipped` | 标准化后未通过 `is_valid_listing_payload` 的条数 |
| `saved` / `updated` / `skipped` | `save_listings` 统计 |
| `sample_normalized` | 首条 `ListingSchema.to_dict()` |

`persist=False` 时不写盘：`saved`/`updated`/`skipped` 均为 0。

## 本地运行

```bash
cd rental_app
python scripts/run_zoopla_pipeline.py --limit 5
python scripts/run_zoopla_pipeline.py --limit 3 --no-save --save-raw --save-normalized
```

## 明确未做（后续阶段）

- 多平台统一调度、analyze/前端/Agent 自动拉数、多页翻页、第三平台。

## 下一阶段建议

- **多平台聚合**：对 `load_listings` / 按 `source` 过滤结果做分析或统一导出。
- **体验增强**：Rightmove + Zoopla 结果并排对比、去重合并策略（业务层，非本文件范围）。
- **抓取增强**：单平台多页（仍保持 scraper / pipeline 分层）。

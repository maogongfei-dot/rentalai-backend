# P6 Phase4 — Rightmove → normalizer → storage 闭环

## 本阶段已完成

- **`data/pipeline/rightmove_pipeline.py`**：`run_rightmove_pipeline` 串联 **RightmoveScraper.scrape** → **`normalize_listing_batch(..., source="rightmove")`** → **`save_listings`**。
- **别名**：`scrape_and_normalize_rightmove`、`run_rightmove_normalization_pipeline`（均指向同一实现）。
- **CLI**：`scripts/run_rightmove_pipeline.py`。
- **调试样本**（可选，失败不影响主流程）：
  - `data/scraper/samples/debug/rightmove_raw_sample.json`
  - `data/scraper/samples/debug/rightmove_normalized_sample.json`
- **Rightmove raw dict**：增加与 normalizer 一致的 **`source_url`**（与 `url` 同值）；仍保留 `price`、`bedrooms` 等别名，由既有 `_base_alias_map` / `_normalize_rightmove_payload` 消费。

## 数据流

1. **抓取**：`RightmoveScraper.scrape(query=..., limit=...)` → `list[dict]`（原始列表页字段）。
2. **标准化**：每条 dict 写入 `scraped_at`（UTC ISO）后，`normalize_listing_batch(stamped, source="rightmove")` → `list[ListingSchema]`。单条异常已由 normalizer 内部降级，整批不崩。
3. **存储**：`save_listings(normalized, file_path=...)`，去重/更新规则与 P3 Phase3 一致（`listing_id` + `source` 优先，否则 `source_url`）。

## 返回结构（`run_rightmove_pipeline`）

| 字段 | 含义 |
|------|------|
| `success` | 抓取无未捕获异常且（若 `persist`）storage 写入成功 |
| `error` | 失败说明，成功多为 `null` |
| `raw_count` | 抓取到的 raw 条数 |
| `normalized_count` | 标准化后的条数（与 raw 一一对应） |
| `normalization_skipped` | 标准化后仍不满足 `is_valid_listing_payload` 的条数（弱数据） |
| `saved` / `updated` / `skipped` | `save_listings` 的统计（`skipped` 为 storage 层单条失败数） |
| `sample_normalized` | 首条 `ListingSchema.to_dict()`，便于肉眼检查 |

`persist=False` 时不写文件：`saved`/`updated`/`skipped` 均为 0，`success` 仍可为 True。

## 本地运行

```bash
cd rental_app
pip install -r requirements.txt
python -m playwright install chromium
python scripts/run_rightmove_pipeline.py --limit 5
python scripts/run_rightmove_pipeline.py --limit 3 --no-save --save-raw --save-normalized
```

## 明确未做（后续阶段）

- **Zoopla**、多平台统一调度、多页翻页。
- **analyze / 前端 / Agent** 自动消费新入库数据（需后续编排）。

## 下一阶段（P6 Phase5 建议）

- **Zoopla** 同源 pipeline 或统一多平台 runner；再视需求把 storage 与 analyze 批处理衔接。

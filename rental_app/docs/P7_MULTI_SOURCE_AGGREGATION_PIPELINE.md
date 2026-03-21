# P7 Phase3 — 多平台聚合入口（Rightmove + Zoopla）

## 本阶段已完成

- **`data/pipeline/multi_source_pipeline.py`**：
  - **`PIPELINE_REGISTRY`**：`rightmove` → `run_rightmove_pipeline`，`zoopla` → `run_zoopla_pipeline`
  - **`run_source_pipeline(source, **kwargs)`**：单平台调度（未知 source 抛 `ValueError`）
  - **`run_multi_source_pipeline(...)`**：按 `sources` 顺序调用子 pipeline（**`include_normalized_listings=True`**），汇总统计，**`dedupe_normalized_listings`** 聚合视图
  - 可选 **`samples/debug/multi_source_aggregated_sample.json`**
- **子 pipeline 轻量扩展**：`include_normalized_listings` 默认 `False`；为 `True` 时在返回中附加 `normalized_listings`（不改变默认行为体积）
- **CLI**：`scripts/run_multi_source_pipeline.py`
- **测试**：`test_multi_source_pipeline.py`

## 职责边界

| 层 | 职责 |
|----|------|
| `run_rightmove_pipeline` / `run_zoopla_pipeline` | 各平台 scrape → normalize → save |
| `run_multi_source_pipeline` | 调度顺序、汇总 **`per_source_stats`**、合并 **`normalized_listings` 视图**、基础去重、可选聚合样本 |

## 统一返回（摘要）

- `success`、`sources_requested`、`sources_run`、`errors`
- `per_source_stats`：各平台子结果（**已去掉** `normalized_listings` 以控制体积）
- `total_raw_count`、`total_normalized_count`、`total_normalization_skipped`、`total_saved`、`total_updated`、`total_skipped`
- `aggregated_unique_count`、`aggregated_listings_sample`（去重后前几条）

## 去重策略（基础）

1. 键 **`(id, source, listing_id)`**（`listing_id` 非空）
2. 否则 **`(url, source, source_url 或 url)`**
3. 否则 **`(weak, source, title|address)`** 文本弱键  

**不做** 跨平台同一房源智能匹配。

## 本地运行

```bash
cd rental_app
python scripts/run_multi_source_pipeline.py --sources rightmove --limit 3
python scripts/run_multi_source_pipeline.py --sources zoopla --limit 3
python scripts/run_multi_source_pipeline.py --sources rightmove,zoopla --limit 2 --save-aggregated-sample
```

## 明确未做

- 前端 / Agent 触发、analyze 自动消费、多页增强、第三平台、智能跨平台去重。

## 下一阶段建议

- 产品层封装「一次搜索多源」参数（地区/预算）；或增加第三平台时在 **`PIPELINE_REGISTRY`** 注册即可。

# P7 Phase4 — 多平台数据接入 analyze / analyze-batch 统一桥接

## 本阶段完成内容

- 新增 **`data/pipeline/analysis_bridge.py`**：在 **不改** `api_analysis` 评分与 `ListingSchema` 核心的前提下，把多平台聚合后的 **listing dict** 转为 **`POST /analyze-batch`** 所需的 `properties[]`，并调用现有 **`analyze_batch_request_body`**。
- **`run_multi_source_pipeline`** 增加可选参数 **`include_aggregated_listings`**；为 `True` 时在结果中附带完整去重列表 **`aggregated_listings`**（默认仍为 `False`，避免无意拉大响应体）。
- **`query` 多平台专用键** `save_analysis_sample` 与子 pipeline 的 **`save_aggregated_sample`** 一样，会在 **`_child_query`** 中剥离，不传给 Rightmove/Zoopla。
- 调试脚本 **`scripts/run_multi_source_analysis.py`**：本地一键「抓取聚合 + batch 分析」。
- 可选调试文件 **`data/scraper/samples/debug/multi_source_analysis_sample.json`**（`--save-analysis-sample` 或 `save_analysis_sample` in query）；写入失败不影响主流程。

## 数据如何进入 analyze-batch

1. **`run_multi_source_pipeline`**（`include_aggregated_listings=True`）产出去重后的 **`ListingSchema.to_dict()` 形态** 列表。
2. 桥接层对每条 dict 执行 **`ListingSchema.from_dict`** → **`to_analyze_payload`**（内部为 **`convert_listing_schema_to_analyze_payload`**），得到与手工/API 一致的 **`STANDARD_INPUT_KEYS`** 子集。
3. **`analyze_batch_request_body({"properties": [...]})`** 走现有逐条 **`analyze_property_item_for_batch`** 与排名、Top 推荐等逻辑。

## 职责边界

| 层 | 职责 |
|----|------|
| **multi_source / 单平台 pipeline** | 抓取、归一、可选落库；输出统计与 listing dicts |
| **analysis_bridge** | 仅做 **ListingSchema → batch property** 映射与 **analyze_batch** 调用 |
| **api_analysis** | 原有 batch 校验、引擎调用、排名与摘要（本阶段未改核心） |

## 统一入口与函数名

- **`run_multi_source_analysis(...)`**：抓取聚合 + 分析 + 统一统计 dict（推荐主入口）。
- **`fetch_multi_source_listings(...)`**：仅 pipeline（含 **`aggregated_listings`**）。
- **`analyze_multi_source_listings(aggregated_listings, ...)`**：仅对已聚合列表做 batch 分析。

辅助映射：

- **`listing_schema_dict_to_batch_property`**
- **`listings_dicts_to_batch_properties`** / **`listings_to_batch_analysis_payload`**

## 返回结构要点（`run_multi_source_analysis`）

- **抓取侧**：`sources_run`、`total_raw_count`、`total_normalized_count`、`aggregated_unique_count`、`total_saved` / `total_updated` / `total_skipped`、`pipeline_success`、`pipeline`（不含大列表 `aggregated_listings`）。
- **分析侧**：`total_analyzed_count`、`batch_succeeded` / `batch_failed`、`properties_built_count`、`analysis_summary`、`top_recommendations`、`sample_analyzed_listing`、`analysis_envelope`（完整 batch 响应）。
- **问题排查**：`errors`（pipeline 调度、单行映射、batch 封套错误等分 `stage`）。
- **`success`**：`analyze_batch` 封套成功且至少构建并分析了一条有效 `property`（`properties_built_count > 0`）。**允许** `pipeline_success` 为 `False`（例如某一平台失败）但仍有另一平台 listings 被分析。

## 本阶段未做

- 前端按钮直连 multi-source + analyze
- Agent 自动触发真实抓取分析
- 多页翻页、第三平台、生产级调度
- 修改 analyze 评分引擎或 ListingSchema 字段定义

## 下一阶段建议

- Streamlit / API 路由层调用 **`run_multi_source_analysis`** 或拆分 **`fetch` + `analyze`**。
- Agent 在适当时机调用同一桥接函数，保持与 UI 一致。
- 按需增加「用户预算/目标邮编」会话级默认值传入 `budget` / `target_postcode`。

## 本地运行

在 **`rental_app`** 目录下：

```text
python scripts/run_multi_source_analysis.py --sources rightmove --limit 3
python scripts/run_multi_source_analysis.py --sources zoopla --limit 3
python scripts/run_multi_source_analysis.py --sources rightmove,zoopla --limit 2 --save-analysis-sample
```

可选：`python test_analysis_bridge.py`（结构与小样本映射，不依赖外网）。

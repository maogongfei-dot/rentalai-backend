# Web UI 组件（P4 Phase1–5）

## `listing_result_card`（Phase1）

- **`build_analyze_card_model` / `build_batch_row_card_model` / `render_listing_result_card`**

## Phase2：条件摘要 + 本地筛选/排序

- **`summarize_analyze_context` / `summarize_batch_request`** — 生成 `(标签, 值)` 列表供页面展示。
- **`filter_batch_rows` / `sort_batch_rows` / `collect_top_indices` / `collect_source_values`** — 对 batch `results[]` 做派生列表，**不修改**原始响应。

## Phase3：详情 / Explain 展开

- **`build_analyze_detail_bundle` / `build_batch_detail_bundle`** — 从 `result` 或 batch 行抽取统一详情结构（字段兼容）。
- **`render_listing_detail_expander`** — 卡片内 **`st.expander("View details & explain")`**（Streamlit 1.28+），分区展示 Overview / Explain / Score breakdown / Risks / Source。
- 引擎 **`top_house_export`** 经 **`api_analysis.normalize_engine_output`** 与 **`legacy_ui_result`**、**batch 行** 轻量透传，便于组件分展示（无新 HTTP 接口）。

## Phase4：batch 分区 + Top picks

- **`batch_results_view`**：`select_top_picks_from_batch`、`partition_remaining_for_batch`、`render_batch_partitioned_listings`（统计行 + Top 1–3 强化卡片 + Other good / Review 分区）。
- 与 Phase2 筛选/排序后的 **`displayed`** 列表一致；Top 优先对齐 API `top_3_recommendations` / `recommended_listings` / `top_recommendations`。

## Phase5：Product 收口

- **`product_copy`** — 全页展示文案单一来源（`DISPLAY_LABELS`、`VIEW_DETAILS` 等）。
- **`result_ui`** — `section_header`、`card_spacing`、轻量 `state_*` 辅助。
- 验收清单：**`docs/P4_PRODUCT_ACCEPTANCE_CHECKLIST.md`**。

单页入口仍为根目录 **`app_web.py`**（`streamlit run app_web.py`）。

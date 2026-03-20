# Web UI 组件（P4 Phase1）

## `listing_result_card`

- **`build_analyze_card_model(result, listing_context)`** — 单条 `/analyze` 风格 `result` + 表单规范化后的 `listing_context`。
- **`build_batch_row_card_model(row, highlight_top=False)`** — `/analyze-batch` 的 `results[]` 行或 `top_1_recommendation`。
- **`render_listing_result_card(model)`** — Streamlit 渲染；缺失字段显示为「—」或提示文案，不抛错。

单页入口仍为根目录 **`app_web.py`**（`streamlit run app_web.py`）。

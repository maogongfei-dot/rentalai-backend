# P7 Phase5 — 前端搜索入口接入真实多平台分析

## 做了什么

1. **`web_ui/real_analysis_service.py`**（新建）  
   统一函数 **`run_real_listings_analysis(...)`**：调用 Phase4 的 **`run_multi_source_analysis`**，把返回的 **`analysis_envelope`** 整理成与 **`POST /analyze-batch`** 相同的封套，供 **`st.session_state["p2_batch_last"]`** 使用；请求摘要写入 **`p2_batch_last_request`**（含一条「场景」`properties[0]`，来自 Agent intent 或 Property details 表单）。

2. **`web_ui/agent_runner.py`**  
   **`run_agent_intent_analysis`** 改为仅调用 **`run_real_listings_analysis`**（进程内；**不再**对 Agent 走 HTTP `/analyze-batch`）。  
   签名仍含 `use_local` / `api_base_url`，与 `app_web` 兼容。

3. **`web_ui/agent_entry.py`**  
   **Continue to Analysis** 传入侧栏的 **`limit_per_source` / `headless` / `persist_listings`**，并把 **`_p7_debug`** 写入 session，供轻量日志展示。

4. **`app_web.py`**  
   - 侧栏 **Real listings (P7)**：每平台条数、是否 headless、是否写入 storage。  
   - **Batch analysis** 折叠区顶部：**Run real multi-source analysis** 按钮（表单 + 可选上次 Agent intent → 预算 / target postcode）。  
   - 折叠区内 **`p7_debug_caption`**：展示上次运行的 `sources_run`、原始行数、去重数、分析数、耗时（秒）。

5. **`web_ui/product_copy.py`**  
   更新 Agent / batch 相关文案，反映「真实抓取 + batch」。

6. **未改**：`api_analysis` 评分、`data/pipeline/*` 抓取实现、P4 卡片 / 筛选 / Top picks 组件 — 仅复用其数据结构。

## 数据流

```text
用户 NL（Agent）→ parse_rental_intent → Continue
    → run_agent_intent_analysis → run_real_listings_analysis
    → run_multi_source_analysis（Rightmove+Zoopla 默认搜索 URL）
    → analyze_batch_request_body
    → p2_batch_last（与手动 JSON batch 成功时相同形态）
    → 下方 Batch results / P4 UI
```

表单路径：

```text
Property details（+ 可选已解析的 Agent intent）
    → Run real multi-source analysis
    → 同上
```

## Fallback

- 抓取结果为空或无法映射为引擎字段：服务层返回 **`success: false`** 的合成封套，**`error.message`** 为 *No listings found, try adjusting your criteria*（或映射/引擎失败时的说明）。  
- 异常：同样写入 **`p2_batch_last`**，Batch 区显示 **`batch_last_failed`** 文案，不抛崩 Streamlit。  
- **Analyze Property**（单条 `/analyze`）与 **Run batch request**（纯 JSON + HTTP API）逻辑**未删除**；仅 Agent 与「真实多源」按钮走新路径。

## 限制（本阶段）

- 各平台仍使用 **代码内默认列表 URL**（如伦敦）；未做「用户邮编 → 自动生成 Rightmove/Zoopla URL」。  
- **无**多页翻页、无实时轮询、无生产调度。  
- 真实抓取依赖本机 **Playwright** 与环境；首次运行可能较慢。

## 相关代码入口

| 位置 | 作用 |
|------|------|
| `run_real_listings_analysis` | 前端统一「真实分析」API |
| `run_agent_intent_analysis` | Agent Continue 专用封装 |
| `app_web.py` 侧栏 + batch expander | 参数与第二入口 |

## 本地验证

在 `rental_app` 下：

```bash
streamlit run app_web.py
```

1. **Agent**：Parse → Continue → 等待抓取结束后查看 **Batch results**。  
2. **Batch 区**：**Run real multi-source analysis**（可先填表单预算 / target postcode）。  
3. 侧栏调小 **Listings per portal** 以缩短调试时间。

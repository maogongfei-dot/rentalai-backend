# P10 Phase3 UI Flow

## 1. Homepage

用户在本机启动 API 服务后，用浏览器打开根路径 **`/`**（与 FastAPI 同源，例如 `http://127.0.0.1:8000/`）。首页为静态 HTML，不依赖单独前端构建。

首次提交分析前，页面脚本会自动调用 **`POST /auth/register`** + **`POST /auth/login`**，在 `localStorage` 中保存 `rentalai_bearer`，以便后续 **`POST /tasks`** 与 **`GET /tasks/{task_id}`** 携带 Bearer 令牌（与现有 P10 任务接口一致）。

## 2. Input

单一文本框，支持两类输入（由前端根据是否以 `http://` / `https://` 开头判断）：

- **Postcode / 地区关键词**：写入异步任务 JSON 的 **`target_postcode`**，走多平台默认列表抓取 + 批量分析。
- **房源列表 URL**：写入 **`listing_url`**，服务端将其作为各平台 scraper 的 **`search_url`**；若未显式指定 `sources`，则按域名粗判为 **Rightmove** 或 **Zoopla** 单平台任务，避免把错误平台的 URL 交给另一平台。

不做多字段表单，也不做复杂校验。

## 3. Submit

用户点击 **Analyze** 后：

1. 调用 **`POST /tasks`**（JSON：`limit_per_source`、`persist`、`headless`，以及 `target_postcode` 或 `listing_url`）。
2. 响应体中的 **`task_id`** 用于后续轮询与结果页路径。

## 4. Loading

首页在请求进行中展示 **`Analyzing...`**；轮询过程中文案为 **`Analyzing... (queued|running|...)`**，不阻塞浏览器主线程逻辑（异步 `fetch` + `setTimeout` 轮询）。

轮询 **`GET /tasks/{task_id}`**，直到状态为 **`success`** / **`degraded`**（进入结果页），或为 **`failed`** / **`timeout`** / **`interrupted`**（展示失败文案）。

## 5. Result Page

路径：**`/result/{task_id}`**（同一静态 `result.html`，由客户端从 URL 解析 `task_id`）。

展示内容来自任务完成时的 **`result`** 对象：

- **基本信息**：优先使用服务端附加的 **`representative_row`**（与 P10 explain 同源的最高分成功条目），否则回退 **`sample_analyzed_listing`**；展示 **score、title、price、postcode/area**（字段来自 `input_meta` 或行上兼容字段）。
- **Explain**：**`p10_explain`** — **`explain_summary`、`pros`、`cons`、`risk_flags`**（由服务端在任务成功写入 TaskStore 时附加，与规则解释引擎一致）。

若任务失败或数据缺失，统一展示：**`Analysis failed, please try again`**。

## 6. Full Flow

**首页 → 输入 postcode/URL → Analyze →（自动注册/登录）→ POST /tasks → 轮询 GET /tasks/{id} → 跳转 /result/{id} → 展示分数、房源信息与 Explain。**

## 7. Limitations

- UI 仅为最小可用：无设计系统、无响应式细调、无无障碍深度优化。
- 依赖浏览器 **`localStorage`**；清除站点数据后需重新隐式注册 guest 用户。
- 分析耗时可长达数分钟；轮询有上限，极端情况下可能超时并显示失败，尽管后台任务仍在跑。
- **representative_row** 与批量内「第一条成功」在边界情况下可能不一致；当前以 explain 所用「最高分成功行」为准。
- 非 Rightmove/Zoopla 的 URL 默认按 Rightmove 单平台尝试，可能抓取失败。

## 8. Next Step

- 在结果页展示 **`task_id`、degraded、elapsed** 等元数据，并支持从 **`/records/analysis`** 拉历史（已登录用户）。
- 将轮询改为 SSE 或 WebSocket，或暴露可配置的 **`limit_per_source` / sources** 的简单高级选项。
- 与 Streamlit 演示页互链，或统一入口说明（API + 两种 UI）。
- 为「仅 postcode」与「仅 URL」分别补充更明确的占位提示与后端校验错误信息映射。

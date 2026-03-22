# P9 Phase4 Second Async Integration

---

## 1. Flow Chosen

**Agent 入口的多平台抓取 + 批量分析。**

调用链：`render_p5_agent_entry` → `_process_agent_batch_submit` → `run_agent_intent_analysis` → `run_real_listings_analysis`（旧同步）或 `run_real_listings_analysis_async`（新异步）。

### 选择理由

1. 它是 P9 Phase4 Expansion Plan 中明确选定的第二流程，也是 Phase3 Closeout 中 "What Still Blocks Scale" 第一项。
2. Agent 入口是用户最常触发多平台分析的位置。在 async mode 关闭时，它仍然在 Streamlit 进程中直接运行 Playwright——这是剩余的最大 OOM 风险源。
3. 底层调用的是与 batch 按钮完全相同的 `run_multi_source_analysis`，后端 `POST /tasks` 端点零修改。
4. 前端改动量极小：三个文件各增加一个 `async_mode` 参数传递即可。

---

## 2. Backend Integration

### 与第一个流程完全一致

- **任务创建**：复用 `POST /tasks`，请求体 `AnalyzeRealRequest` 不变。
- **任务执行**：复用 `_run_analysis_task` → `run_multi_source_analysis`，后台 daemon thread 执行。
- **任务查询**：复用 `GET /tasks/{task_id}`，返回统一结构。
- **并发控制**：复用 `_TASK_SEMAPHORE`。
- **无新增端点、无新增模型、无新增存储逻辑。**

### 唯一的后端修改

`_TASK_SEMAPHORE.acquire(timeout=5)` → `acquire(timeout=300)`。从"5 秒内获取不到就失败"改为"排队等待最多 5 分钟"。这使得 Agent 区和 batch 区先后触发分析时，第二个任务排队等待而非立即报 "Server busy"。

---

## 3. Frontend Integration

### 触发入口

与 batch 按钮共享同一个 `Async mode (pilot)` sidebar checkbox。勾选后，Agent 区的 **Continue to Analysis** 按钮走异步路径。

### 调用链（async mode ON）

1. 用户点击 **Continue to Analysis** → `_continue()` 设置 `PHASE_SUBMITTING`。
2. 下次 rerun 进入 `_process_agent_batch_submit` → `async_mode=True` 分支。
3. `st.empty()` 显示实时状态 → 调用 `run_agent_intent_analysis(async_mode=True, on_status=callback)`。
4. 内部调用 `run_real_listings_analysis_async(api_base_url=..., on_status=...)` — 与 batch 按钮使用完全相同的函数。
5. 任务完成后，结果写入 `st.session_state["p2_batch_last"]`，页面自然 rerun 渲染 batch 结果。

### 调用链（async mode OFF）

与修改前完全一致：`st.spinner` → `run_agent_intent_analysis` → `run_real_listings_analysis`（进程内同步执行）。

### 状态查询

由 `run_real_listings_analysis_async` 内部自动轮询（3 秒间隔，最多 80 次），前端通过 `on_status` 回调更新 `st.empty()` 显示。与 batch 按钮模式完全一致。

---

## 4. Pattern Consistency Check

| 维度 | Batch 按钮（Pilot） | Agent 入口（本次） | 一致？ |
|------|---------------------|-------------------|--------|
| 后端端点 | `POST /tasks` | `POST /tasks` | ✅ |
| 请求体模型 | `AnalyzeRealRequest` | `AnalyzeRealRequest` | ✅ |
| 后台执行函数 | `_run_analysis_task` | `_run_analysis_task` | ✅ |
| 查询端点 | `GET /tasks/{task_id}` | `GET /tasks/{task_id}` | ✅ |
| 前端异步函数 | `run_real_listings_analysis_async` | `run_real_listings_analysis_async` | ✅ |
| `on_status` 回调 | `st.empty()` + callback | `st.empty()` + callback | ✅ |
| 返回格式 | `(envelope, error, request_payload)` | `(envelope, error, request_payload)` | ✅ |
| Session state 写入 | `p2_batch_last` / `p7_last_debug` | `p2_batch_last` / `p7_last_debug` | ✅ |
| Fallback 控制 | `_p7_async` checkbox | `_p7_async` checkbox（同一个） | ✅ |
| 并发保护 | `_TASK_SEMAPHORE` | `_TASK_SEMAPHORE`（同一个） | ✅ |

**结论：完全一致，无偏差。** 两个入口复用了完全相同的后端端点、异步服务函数、前端回调模式和 session state 写入逻辑。唯一的区别是触发位置（Agent 区 vs batch expander）和调用入口层（`agent_runner.py` vs `app_web.py` 直接调用）。

---

## 5. Validation Steps

### 前置条件

1. 启动 FastAPI：`uvicorn api_server:app --host 127.0.0.1 --port 8000`
2. 启动 Streamlit：`streamlit run app_web.py`

### Agent 异步路径验证

1. 打开 `http://localhost:8501`。
2. 侧栏勾选 **Async mode (pilot)**。
3. 在 Agent 区输入自然语言，例如 `"2 bedroom flat under 1500 in London"`。
4. 点击 **Parse**。
5. 确认解析结果后，点击 **Continue to Analysis**。
6. 观察 `st.info` 框依次显示：
   - "Submitting async task to backend…"
   - "Task **{task_id}** — queued"
   - "Task **{task_id}** — running"
7. 等待 30–120 秒后，页面 rerun 显示 batch 分析结果。

### 成功标志

- Batch 结果区显示真实 listing 卡片。
- `p7_last_debug` 包含 `async_task_id` 字段。
- FastAPI 日志中可见 `[TASK] created ...`、`[TASK] ... -> running`、`[TASK] ... -> success`。

### 排队验证

1. 在 Agent 区触发一个异步任务。
2. 任务 running 期间，在 batch expander 中再点击 **Run real multi-source analysis (async)**。
3. 第二个任务应显示 "queued"，并在第一个完成后自动开始（而非立即报 "Server busy"）。

### 失败排查

1. **"Failed to submit async task"** → FastAPI 未启动或 API base URL 配错。
2. **"Queue timeout"** → 前一个任务运行超过 5 分钟。检查后端日志。
3. **"Polling timed out"** → 任务运行超过 4 分钟。检查后端日志。

### 同步路径回归验证

取消勾选 **Async mode (pilot)** → Agent 区 Parse + Continue → 确认通过同步路径正常运行（spinner 方式）。

---

## 6. What We Learned

### 第二次接入确实更快

- 后端端点零修改。
- `agent_runner.py` 仅增加 `async_mode` + `on_status` 参数和一个 `if` 分支。
- `agent_entry.py` 仅增加 `async_mode` 参数传递和 `st.empty()` + 回调模式。
- `app_web.py` 仅增加一个 `async_mode=_p7_async` 参数。
- 总代码改动约 30 行，且几乎是 Pilot 模式的精确复制。

### 标准模式已验证为可复用

`run_real_listings_analysis_async` 被证明是一个真正通用的异步入口函数。任何需要触发多平台分析的前端入口，只需要传递正确的参数并提供 `on_status` 回调即可。不需要了解 TaskStore、后端线程模型或轮询细节。

### 仍然不顺的地方

- **Streamlit 阻塞体验不变。** `time.sleep` 在轮询期间阻塞脚本，用户无法操作页面。这是 Streamlit 执行模型的固有限制，非异步化本身的问题。
- **两个入口共享同一个 toggle。** 目前无法单独控制 Agent 或 batch 的异步模式。这是设计选择——保持简单——但后续可能需要分开控制。

---

## 7. Remaining Gaps

1. **进程内 TaskStore 无法跨 worker 共享。** gunicorn 多 worker 部署前必须解决。
2. **无任务取消机制。** 一旦提交无法中止。
3. **无结果缓存。** 相同参数的重复请求会重新运行完整 pipeline。
4. **Streamlit 轮询阻塞。** 用户在等待期间无法操作页面。
5. **`timeout` 状态未使用。** `mark_timeout` 存在但从未被调用。

---

## 8. Next Step

**P9 Phase4 Step3 — 收口复测 + 系统成熟度评估。**

确认 Agent + batch 两个入口都稳定走异步路径后，Phase4 可收口。下一步应关注：
1. 跨 worker TaskStore 方案设计（为生产多 worker 部署做准备）。
2. 结果缓存/去重（减少重复 Playwright 运行）。

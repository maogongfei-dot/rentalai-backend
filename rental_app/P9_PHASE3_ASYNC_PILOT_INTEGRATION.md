# P9 Phase3 Async Pilot Integration

---

## 1. Pilot Flow Chosen

**流程：多平台抓取 + 批量分析（`run_multi_source_analysis`，通过 `POST /tasks` 异步执行）。**

为什么选它：

1. 它是 Step3 中明确选定的异步试点 — 耗时最长（30–120s）、阻塞最严重、收益最大。
2. 输入/输出边界清晰：接受少量参数，返回标准 `analysis_envelope` 结构，无需改造中间层。
3. 它已经具备超时保护（per-source 120s、整体 180s）和降级标记（`degraded`），异步化不增加额外容错需求。
4. 当前这个流程在 Streamlit 进程里同步运行时，会阻塞所有用户并消耗大量内存（Playwright Chromium）。移到后端异步执行后，Streamlit 进程仅做轮询，内存和 CPU 压力转移到 FastAPI 进程。

为什么现在接它最合适：

- Step3 骨架已就绪（`TaskStore`、`POST /tasks`、`GET /tasks/{task_id}`）。
- 只需要在前端 service 层增加一个 HTTP 提交 + 轮询函数，在 UI 层增加一个 checkbox 开关，即可跑通闭环。改动量极小，风险极低。

---

## 2. Backend Integration

### 提交任务接口

`POST /tasks` — 已在 Step3 实现。接收 `AnalyzeRealRequest`（`sources`、`limit_per_source`、`budget`、`target_postcode`、`headless`、`persist`），创建 `TaskRecord`，启动 daemon thread 执行 `run_multi_source_analysis`，立即返回 `{ task_id, status }`.

**Step4 新增：并发信号量。** `_TASK_SEMAPHORE = threading.Semaphore(1)` 确保同一时刻最多只有一个分析任务在运行。如果信号量 5 秒内未获取到，任务直接标记为 `failed`（"Server busy"），避免多个 Playwright 实例同时运行导致 OOM。

### 后台执行逻辑

`_run_analysis_task(task_id, params)` — 在 daemon thread 中：

1. 获取信号量（失败则 `mark_failed` + 退出）
2. `mark_running(task_id)`
3. 调用 `run_multi_source_analysis(...)`
4. 成功 → `mark_success(task_id, result, degraded=..., elapsed=...)`
5. 异常 → `mark_failed(task_id, error, elapsed=...)`
6. `finally` → 释放信号量

### 查询状态接口

`GET /tasks/{task_id}` 返回：

```json
{
  "task_id": "...",
  "status": "running | success | failed | degraded",
  "created_at": "...",
  "updated_at": "...",
  "degraded": false,
  "elapsed_seconds": 75.3,
  "error": null,
  "result": { ... }    // 仅在 success/degraded 时包含
}
```

---

## 3. Frontend Integration

### 触发入口

侧栏 **Real listings (P7)** 区新增 **Async mode (pilot)** checkbox。勾选后，batch expander 中的 **"Run real multi-source analysis (async)"** 按钮走异步路径。

### 异步调用函数

`web_ui/real_analysis_service.py` 新增 `run_real_listings_analysis_async()`：

1. 构造 `task_body`（与 `AnalyzeRealRequest` 一致）。
2. `POST {api_base}/tasks` — 拿到 `task_id`。
3. 每 3 秒 `GET {api_base}/tasks/{task_id}` 轮询，最多 80 次（~4 min）。
4. 通过 `on_status(task_id, status_text)` 回调更新 Streamlit 页面上的 `st.empty()` 信息框，显示当前任务 ID 和状态。
5. 终态时解析 `result`，构造与同步版完全相同的 `(envelope, error, request_payload)` 三元组返回。

### 结果显示

异步路径的返回值与同步路径格式完全一致，直接写入 `st.session_state["p2_batch_last"]` 后 `st.rerun()`。后续的 batch 结果渲染、filter/sort、Agent insight panel 全部复用，无需任何修改。

---

## 4. State Flow

```
用户点击按钮
  │
  ├─ [Async mode OFF] → 旧同步路径（run_real_listings_analysis 直接在 Streamlit 进程执行）
  │
  └─ [Async mode ON]
       │
       ▼
  POST /tasks → 返回 task_id     状态：queued
       │
       ▼ (daemon thread)
  mark_running(task_id)            状态：running
       │
       ▼
  run_multi_source_analysis(...)
       │
       ├─ 全部成功 → mark_success   状态：success     result 可用
       ├─ 部分失败 → mark_success   状态：degraded    result 可用, degraded=true
       └─ 异常     → mark_failed    状态：failed      error 可用
```

前端轮询循环在看到 `success` / `degraded` / `failed` 后结束，将结果写入 session state 并 rerun。

---

## 5. Safety Notes

### 为什么这次改动是低风险

1. **旧同步流程完全保留。** Async mode 是一个 opt-in checkbox，默认关闭。不勾选时行为与之前 100% 一致。
2. **新代码与旧代码无交叉修改。** 异步路径是一个独立分支（`if _p7_async ... else ...`），旧 `run_real_listings_analysis` 函数没有任何改动。
3. **返回格式完全兼容。** 异步函数返回的三元组结构与同步版一致，下游 session state 写入和 UI 渲染代码无需修改。
4. **并发保护已到位。** `Semaphore(1)` 防止多任务同时启动 Playwright OOM。
5. **回退方式极简。** 取消勾选 checkbox 即回到旧路径，无需 rollback 任何代码。

### 旧同步流程没有被破坏的原因

- `run_real_listings_analysis` 函数体 0 行改动。
- `app_web.py` 中旧按钮 handler 原封不动移入 `else` 分支。
- 所有旧端点（`/analyze`、`/analyze-batch` 等）不受影响。

---

## 6. Validation Plan

### 前置条件

1. 在 `rental_app` 目录下启动 FastAPI：
   ```
   uvicorn api_server:app --host 127.0.0.1 --port 8000
   ```
2. 在另一终端启动 Streamlit：
   ```
   streamlit run app_web.py
   ```

### 验证步骤

1. 打开 `http://localhost:8501`。
2. 在侧栏 **Real listings (P7)** 区勾选 **Async mode (pilot)**。
3. 展开页面底部的 **batch** expander。
4. 点击 **"Run real multi-source analysis (async)"** 按钮。
5. 观察页面出现 `st.info` 框，依次显示：
   - "Submitting async task to backend…"
   - "Task **{task_id}** — queued"
   - "Task **{task_id}** — running"
6. 等待约 30–120 秒后，页面自动 rerun 并显示 batch 分析结果。

### 成功标志

- batch 结果区显示真实 listing 卡片（与同步路径一致）。
- `p7_last_debug` 中包含 `async_task_id` 字段。
- FastAPI 日志中可见 `[TASK] created ...`、`[TASK] ... -> running`、`[TASK] ... -> success`。

### 失败排查

1. **"Server busy" 错误** → 另一个任务正在运行，等待完成后重试。
2. **"Failed to submit async task"** → FastAPI 未启动或 API base URL 配置错误。
3. **"Polling timed out"** → 任务运行超过 4 分钟，检查后端日志 (`uvicorn` 终端)。
4. **页面未跳转** → 检查浏览器 console 或 Streamlit 日志。

### 同步路径回归验证

取消勾选 **Async mode (pilot)** → 点击按钮 → 确认仍通过同步路径正常运行。

---

## 7. Current Limitations

1. **轮询间隔固定 3 秒** — 无 WebSocket 或 SSE 推送，前端体验是"等待 + 周期性状态更新"。
2. **单并发限制** — Semaphore(1) 意味着同一时刻只能运行一个分析任务；第二个提交的任务会立即失败。
3. **进程内存储** — 任务记录在进程内 dict，服务重启后丢失。
4. **无任务取消** — 一旦提交，无法取消正在运行的任务。
5. **Streamlit 执行模型** — 轮询期间 Streamlit 脚本处于阻塞状态（`time.sleep`），用户无法操作页面其他元素。这与旧同步路径的 spinner 行为一致，但并非理想 UX。
6. **仅 pilot 入口** — 只有 batch expander 中的按钮支持 async；Agent 入口（`render_p5_agent_entry`）仍走旧路径。

---

## 8. Recommended Next Step

**将 Agent 入口（`render_p5_agent_entry` 中的 real analysis 调用）也接入异步路径。**

Agent 入口是用户最常触发多平台分析的位置。当前它仍在 Streamlit 进程中直接运行 Playwright + `analysis_bridge`，是最大的阻塞和 OOM 风险源。接入方式与 batch 按钮完全相同：判断 `_p7_async` → 调用 `run_real_listings_analysis_async`。

同时可考虑将 `Semaphore(1)` 改为队列式排队（queued 等待 → 有序执行），使第二个任务不立即失败而是排队等待。

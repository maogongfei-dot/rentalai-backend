# P9 Phase3 Async Pilot Validation

---

## 1. Validation Scope

**本轮复测覆盖：**

| 模块 | 覆盖 | 复测方式 |
|------|------|----------|
| `task_store.py` — TaskRecord / TaskStore | ✅ | 代码级逐行审查：线程安全、状态流转、TTL 清理、容量淘汰 |
| `api_server.py` — POST /tasks, GET /tasks/{id}, GET /tasks | ✅ | 代码级审查：请求处理、Semaphore 并发控制、后台线程启动、错误处理 |
| `real_analysis_service.py` — run_real_listings_analysis_async | ✅ | 代码级审查：HTTP 提交、轮询逻辑、终态处理、返回格式兼容性 |
| `app_web.py` — Async mode checkbox + 按钮 handler | ✅ | 代码级审查：分支正确性、session state 写入、st.rerun 时机 |
| 旧同步路径 — run_real_listings_analysis + 旧按钮 handler | ✅ | 确认 0 行改动，完全保留 |
| 旧同步端点 — /analyze, /analyze-batch, /health 等 | ✅ | 确认未修改 |

**未纳入本轮复测：**

- Agent 入口（`render_p5_agent_entry`）— 仍走旧同步路径，不在本轮异步试点范围内。
- Scraper / analysis_bridge 内部逻辑 — 已在 P9 Phase2 复测中确认，本轮不重复。

---

## 2. Backend Validation Result

### 创建任务接口（POST /tasks）

| 检查项 | 结果 |
|--------|------|
| 请求体解析（Pydantic `AnalyzeRealRequest`） | ✅ 类型校验 + 范围约束（`ge=1, le=50`）正常 |
| task_id 生成（`uuid4().hex[:12]`） | ✅ 12 位 hex，碰撞概率极低 |
| TaskRecord 创建 + 存入 dict | ✅ 线程安全（`_lock`），`updated_at` 自动设置 |
| 后台线程启动 | ✅ `daemon=True`，不阻塞主请求返回 |
| 返回结构 | ✅ `{ task_id, status }` |

### 后台执行（_run_analysis_task）

| 检查项 | 结果 |
|--------|------|
| Semaphore(1) 并发保护 | ✅ 5 秒获取超时，失败 → `mark_failed("Server busy")` |
| Semaphore 释放 | ✅ `finally` 块确保必定释放，无泄漏风险 |
| 状态流转 queued → running | ✅ `mark_running` 在 semaphore 获取成功后立即调用 |
| 状态流转 running → success / degraded | ✅ `mark_success` 包含 `result`、`degraded`、`elapsed` |
| 状态流转 running → failed | ✅ 异常被捕获，`mark_failed` 包含错误信息和 `elapsed` |
| 状态流转 queued → failed（semaphore 超时） | ✅ 跳过 `running`，直接 `failed`，语义正确 |
| 日志输出 | ✅ `logger.error` 含 `exc_info=True` 完整堆栈 |

### 查询任务状态接口（GET /tasks/{task_id}）

| 检查项 | 结果 |
|--------|------|
| 正常返回所有字段 | ✅ 含 `task_id, status, created_at, updated_at, input_summary, degraded, elapsed_seconds, error` |
| `result` 仅在终态返回 | ✅ 仅 `success` / `degraded` 时包含 |
| 未知 task_id | ✅ 404 + `{ error, task_id }` |
| 线程安全 | ✅ `get()` 在 `_lock` 内执行 |

**小修复：** `GET /tasks/{task_id}` 原始实现遗漏了 `input_summary` 字段，已补齐。

### 风险点

- **进程重启后所有任务丢失。** 前端轮询中的任务 ID 变为 404。用户需重新提交。这是设计决策（in-process dict），在当前 MVP 阶段可接受。
- **daemon 线程在进程退出时被强制终止。** 正在运行的 Playwright 实例不会优雅关闭。可接受——Chromium 子进程会被 OS 回收。

---

## 3. Frontend Validation Result

### 创建任务（run_real_listings_analysis_async）

| 检查项 | 结果 |
|--------|------|
| 构造 task_body 正确性 | ✅ 参数从 intent / form_raw 正确提取，None 值被过滤 |
| POST /tasks 调用 | ✅ 15 秒 timeout，异常被捕获并返回 synthetic failure envelope |
| task_id 提取 | ✅ 检查 `created.get("task_id")` 是否为空 |
| on_status 回调触发 | ✅ 提交成功后立即回调 `("queued")` |

### 轮询逻辑

| 检查项 | 结果 |
|--------|------|
| 轮询间隔 | ✅ 3 秒，通过 `time.sleep` |
| 最大轮询次数 | ✅ 80 次（~4 分钟） |
| 网络错误处理 | ✅ `except Exception` 捕获后 continue，不中断轮询 |
| success / degraded 终态处理 | ✅ 提取 result，构造兼容 envelope |
| failed 终态处理 | ✅ 提取 error，返回 synthetic failure |
| 轮询超限处理 | ✅ 返回 synthetic failure + task_id 供手动查询 |
| on_status 回调每轮触发 | ✅ 每次 poll 结果后调用，显示当前 status |
| 轮询停止条件 | ✅ 仅 `success` / `degraded` / `failed` 三种终态停止 |

### Streamlit 集成（app_web.py）

| 检查项 | 结果 |
|--------|------|
| Async mode checkbox 控制 | ✅ 默认关闭，勾选后走异步分支 |
| 按钮标签区分 | ✅ 勾选后显示 "(async)" 后缀 |
| st.empty() 状态显示 | ✅ 实时更新任务 ID 和状态 |
| 结果写入 session state | ✅ 与同步路径写入相同 key（`p2_batch_last`、`p2_batch_last_request`、`p7_last_debug`） |
| st.rerun() 时机 | ✅ 异步/同步两个分支都在结果处理完成后 rerun |
| 异常兜底 | ✅ `except Exception` 写入 failure session state |

### 风险点

- **轮询期间 Streamlit 脚本阻塞。** `time.sleep(3)` 阻塞整个脚本执行，用户无法操作页面其他元素。与旧同步路径的 `st.spinner` 行为一致，但并非理想 UX。这是 Streamlit 执行模型的固有限制。
- **后端重启导致持续空轮询。** 如果后端在任务运行中重启，task_id 丢失，`GET /tasks/{id}` 返回 404。poll 函数的 `except Exception` 会将 404 当作暂时性错误继续重试，最终在 80 次后超时。约浪费 4 分钟。可接受——用户会看到超时提示。

---

## 4. Async Benefit Assessment

### 明确收益

1. **Playwright / 分析引擎从 Streamlit 进程转移到 FastAPI 进程。** 这是最核心的收益。旧同步路径中，Streamlit 进程直接 import 并运行 `analysis_bridge` → `multi_source_pipeline` → Playwright，消耗大量内存和 CPU。异步路径中，Streamlit 仅做 HTTP POST + 轮询 GET，内存和 CPU 压力完全由 FastAPI 后端承担。这为前后端独立扩展打下基础。

2. **并发保护机制到位。** `Semaphore(1)` 确保同一时刻最多一个 Playwright 实例运行，从根本上防止了多用户同时触发导致的 OOM 崩溃。旧同步路径没有这个保护——每个 Streamlit session 都可以独立启动 Playwright。

3. **任务可查询、可追踪。** `GET /tasks/{task_id}` 提供了任务状态、耗时、错误信息的结构化查询能力。`GET /tasks` 提供活跃任务列表。这比旧路径（分析结果只存在 Streamlit session state 中，无法从外部查看）有质的提升。

### 需要继续观察的收益

- **用户等待体验改善程度。** 异步路径显示了实时状态更新（queued → running → success），理论上比纯 spinner 信息更丰富。但由于 Streamlit 的 `time.sleep` 阻塞模型，用户仍然无法在等待期间操作页面，实际体验提升有限。需要在真实用户场景中观察。
- **后端独立扩展的实际效果。** 当前仍是单 uvicorn worker，异步化的扩展收益尚未体现。当切换到 gunicorn 多 worker 时，需要解决 TaskStore 跨 worker 共享问题。

---

## 5. Current Limitations

1. **单并发限制（Semaphore(1)）。** 第二个任务提交时直接失败（"Server busy"），而非排队等待。对于多用户场景，这意味着只有一个用户的请求能同时执行。

2. **进程内存储。** TaskStore 是进程内 dict——服务重启后所有任务记录丢失；gunicorn 多 worker 时各 worker 有独立 store，创建任务和查询任务可能落在不同 worker 上导致 404。

3. **轮询阻塞 Streamlit。** `time.sleep` 阻塞脚本执行，用户在等待期间完全无法操作页面。这是 Streamlit 执行模型的固有限制。

4. **Agent 入口未接入。** 用户最常触发多平台分析的 Agent 路径仍走旧同步流程（Streamlit 进程内直接运行 Playwright），是当前最大的实际阻塞和 OOM 风险源。

5. **无任务取消机制。** 一旦提交无法中止，daemon thread 会运行直到完成或失败。

6. **timeout 状态未使用。** `TaskStore.mark_timeout` 存在但从未被调用。当前超时由 analysis_bridge 内部处理，抛出异常后变为 `failed` 状态。语义可接受，但 `timeout` 作为独立状态的价值未体现。

---

## 6. Regression / Stability Risks

| 风险 | 等级 | 说明 |
|------|------|------|
| 旧同步流程被误伤 | **无** | `run_real_listings_analysis` 0 行改动；旧按钮 handler 完整保留在 `else` 分支；所有旧 API 端点未修改 |
| Async mode 默认开启导致意外 | **无** | checkbox 默认关闭（`False`），用户必须主动勾选 |
| 新端点影响现有端点 | **无** | `/tasks` 路径独立，不与 `/analyze` / `/analyze-batch` 冲突；HTTP middleware 的 perf/alert 覆盖新端点（正常行为） |
| 内存泄漏 — TaskStore 无限增长 | **低** | TTL 10 分钟 + max 200 条 + 自动淘汰。每条 TaskRecord 的 `result` 可能较大（完整 analysis_envelope），但 200 条上限足以控制 |
| Semaphore 泄漏 | **无** | `finally` 块确保释放，无论正常完成还是异常 |
| daemon thread 孤立运行 | **低** | 进程退出时被强制终止。Chromium 子进程由 OS 回收。不会导致僵尸进程 |
| 前端轮询风暴 | **低** | 3 秒间隔 × 单一 GET 请求，负载可忽略。最多 80 次后自动停止 |

**结论：无回归问题。稳定性风险均为已知的设计 trade-off，在 MVP 阶段可接受。**

---

## 7. Can We Expand This Pattern?

**可以扩展到下一个真实流程。**

理由：

1. **骨架已验证为 correct-by-review。** 状态流转（queued → running → success/failed/degraded）完整，线程安全，Semaphore 保护到位，错误处理覆盖所有路径，返回格式与旧流程兼容。

2. **前端集成模式已证明可行。** `on_status` 回调 + `st.empty()` 提供了最小可用的实时状态显示，session state 写入与旧路径完全兼容，downstream UI 无需修改。

3. **扩展成本极低。** 下一个流程（Agent 入口）只需要在 `render_p5_agent_entry` 中增加与 batch 按钮相同的 `if _p7_async` 分支即可。不需要修改 TaskStore、后端端点或异步服务函数。

**扩展前建议先做：**

- 将 `Semaphore(1)` 改为排队式等待（`acquire(blocking=True)`），使第二个任务不立即失败而是等前一个完成后再运行。这对 Agent 入口尤其重要——用户在 Agent 区和 batch 区同时触发分析时，第二个不应直接报 "Server busy"。

---

## 8. Recommended Next Step

**P9 Phase3 收口完成后，建议进入 P10 — 异步模式推广 + Agent 入口迁移。**

具体第一步：

1. 将 Agent 入口（`render_p5_agent_entry` 中的 real analysis 调用）接入 `run_real_listings_analysis_async`，与 batch 按钮共享相同的 `_p7_async` toggle。
2. 将 `Semaphore(1)` 改为 `acquire(blocking=True)` + 超时（如 300 秒），使排队等待成为可能。
3. 在 `GET /tasks/{task_id}` 中增加 `position_in_queue` 字段（可选），让前端显示排队位置。

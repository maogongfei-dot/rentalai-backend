# P9 Phase3 Async Task Skeleton

---

## 1. First Async Pilot

**选择的流程：多平台抓取 + 批量分析（`run_multi_source_analysis`）。**

为什么选它：

1. 它是系统中耗时最长的单一流程（30–120s），是 Scalability Risk Map 中 Top 1 瓶颈。
2. 它的输入/输出边界清晰：接受 `sources`、`limit_per_source`、`budget` 等参数，返回一个结构化的 `dict`（包含 `analysis_envelope`、`errors`、`degraded` 等）。无需改造中间接口。
3. 它当前在 Streamlit 进程中同步运行，阻塞全部用户。将它异步化后收益最大：前端不再阻塞，后端可在后台线程独立执行。
4. 它本身已具备超时保护（per-source 120s、整体 180s）和降级标记（`degraded`），异步化不需要额外增加容错逻辑。
5. 不改核心分析引擎或 scraper 内部代码，只是把调用入口从同步变为"提交 + 后台执行 + 轮询"。

---

## 2. Task Model

| 字段 | 类型 | 用途 |
|------|------|------|
| `task_id` | `str` | 12 位 hex UUID 片段，前端轮询的唯一标识 |
| `status` | `str` | 任务生命周期状态（见下表） |
| `created_at` | `str` | ISO 8601 UTC 时间戳，任务创建时间 |
| `updated_at` | `str` | ISO 8601 UTC 时间戳，最后状态变更时间 |
| `input_summary` | `dict` | 请求参数摘要（`sources`、`limit_per_source`），用于调试和日志 |
| `result` | `dict \| None` | 任务成功后的完整 `run_multi_source_analysis` 返回值 |
| `error` | `str \| None` | 失败时的错误描述 |
| `degraded` | `bool` | 部分 source 失败但仍有结果时为 `True` |
| `elapsed_seconds` | `float \| None` | 任务实际运行耗时 |

### 状态机

```
queued ──→ running ──→ success
                  ├──→ failed
                  ├──→ timeout
                  └──→ degraded (success with partial failure)
```

| 状态 | 含义 |
|------|------|
| `queued` | 已创建，后台线程尚未开始执行 |
| `running` | 后台线程正在执行 `run_multi_source_analysis` |
| `success` | 全部完成，`result` 字段包含完整结果 |
| `failed` | 执行过程中抛出异常，`error` 字段包含错误信息 |
| `timeout` | 执行超时（预留状态，当前版本由 analysis_bridge 内部 timeout 触发 `failed`） |
| `degraded` | 分析成功但 pipeline 部分失败，`result` 可用但不完整 |

---

## 3. Storage Strategy

**方式：进程内 `dict`（`TaskStore._tasks`），以 `threading.Lock` 保护并发访问。**

**为什么这样做：**
- 零依赖 — 不需要 Redis、数据库或文件 I/O。
- 线程安全 — 所有读写通过 `_lock` 保护。
- 即刻可用 — 与 FastAPI 同进程，无序列化/反序列化开销。

**局限性：**
- 进程重启后所有任务丢失。用户会看到 404 "task_not_found"，需要重新提交。
- gunicorn 多 worker 时各 worker 有独立的 `TaskStore`，创建任务的 worker 和查询任务的 worker 可能不同，导致 404。当前单 worker 部署不受影响。
- 内存容量上限：默认 `max_tasks=200`，超过后自动淘汰最旧的已完成任务。活跃任务（queued/running）不会被淘汰。
- 已完成任务在 10 分钟后自动过期清理（`_TASK_TTL_SECONDS=600`）。

---

## 4. New Endpoints

### POST /tasks — 提交任务

**请求体：**

```json
{
  "sources": ["rightmove", "zoopla"],
  "limit_per_source": 10,
  "budget": 1500.0,
  "target_postcode": "SW1A",
  "headless": true,
  "persist": true
}
```

所有字段均可选，未提供时使用默认值。

**响应（201 逻辑，实际 200）：**

```json
{
  "task_id": "a1b2c3d4e5f6",
  "status": "queued"
}
```

**行为：** 立即返回 `task_id`，在后台 daemon 线程中启动 `run_multi_source_analysis`。

### GET /tasks/{task_id} — 查询任务状态

**运行中响应：**

```json
{
  "task_id": "a1b2c3d4e5f6",
  "status": "running",
  "created_at": "2026-03-21T15:00:00+00:00",
  "updated_at": "2026-03-21T15:00:01+00:00",
  "degraded": false,
  "elapsed_seconds": null,
  "error": null
}
```

**成功响应（包含完整结果）：**

```json
{
  "task_id": "a1b2c3d4e5f6",
  "status": "success",
  "created_at": "2026-03-21T15:00:00+00:00",
  "updated_at": "2026-03-21T15:01:15+00:00",
  "degraded": false,
  "elapsed_seconds": 75.3,
  "error": null,
  "result": { "success": true, "analysis_envelope": { ... }, ... }
}
```

**任务不存在：**

```json
HTTP 404
{ "error": "task_not_found", "task_id": "nonexistent" }
```

### GET /tasks — 列出活跃任务

```json
{
  "tasks": [
    { "task_id": "a1b2c3d4e5f6", "status": "running", "created_at": "..." }
  ]
}
```

---

## 5. Execution Strategy

**方式：Python `threading.Thread(daemon=True)`，在 `POST /tasks` handler 中启动。**

```
POST /tasks handler:
  1. 创建 TaskRecord (status=queued)
  2. 启动 daemon thread → _run_analysis_task(task_id, params)
  3. 立即返回 { task_id, status }

_run_analysis_task (后台线程):
  1. mark_running(task_id)
  2. 调用 run_multi_source_analysis(...)
  3. 成功 → mark_success(task_id, result, degraded, elapsed)
     失败 → mark_failed(task_id, error, elapsed)
```

**为什么用 Thread 而不是 asyncio：**
- FastAPI 的同步路由（`def` 而非 `async def`）运行在线程池中。`run_multi_source_analysis` 内部大量使用 `ThreadPoolExecutor`、Playwright 同步 API 等，不适合 `asyncio.create_task`。
- `threading.Thread` 与现有代码兼容性最好，不需要将调用链改为 async。

**风险点：**
- daemon thread 在进程退出时被强制终止，正在运行的任务会丢失。可接受 — 用户重新提交即可。
- 无并发限制 — 理论上可以同时提交多个任务，每个启动一个线程。在 Render 512MB 下，多个 Playwright 实例会 OOM。后续可增加信号量限制。

---

## 6. Relationship with Existing Sync Flow

### 旧同步流程完全保留

| 端点 | 类型 | 变化 |
|------|------|------|
| `POST /analyze` | 同步 | 不变 |
| `POST /score-breakdown` | 同步 | 不变 |
| `POST /risk-check` | 同步 | 不变 |
| `POST /explain-only` | 同步 | 不变 |
| `POST /analyze-batch` | 同步 | 不变 |
| `GET /health` | 同步 | 不变 |
| `GET /alerts` | 同步 | 不变 |

### 新增异步端点

| 端点 | 类型 | 用途 |
|------|------|------|
| `POST /tasks` | 异步（提交） | 提交多平台抓取+分析任务 |
| `GET /tasks/{task_id}` | 同步（查询） | 查询任务状态和结果 |
| `GET /tasks` | 同步（查询） | 列出活跃任务 |

### 不影响的现有功能

- 前端 `app_web.py` 中的所有现有按钮和表单仍通过旧同步流程工作。
- `real_analysis_service.py` 中的 `run_real_listings_analysis` 仍然直接调用 `analysis_bridge`，不受影响。
- 新端点是增量添加，不修改任何旧端点的逻辑或返回结构。

### 迁移路径

后续如果要让前端使用异步任务：
1. `real_analysis_service.py` 改为 `POST /tasks` + 轮询 `GET /tasks/{task_id}`。
2. `app_web.py` 中的 Agent 按钮改为提交任务 + 轮询 + 显示结果。
3. 旧同步路径仍可作为 fallback 保留。

---

## 7. Current Limitations

1. **单进程绑定** — TaskStore 是进程内 dict，gunicorn 多 worker 时任务状态不共享。
2. **重启丢失** — 进程重启后所有任务记录清空，无持久化。
3. **无并发限制** — 无信号量限制同时运行的任务数，多个任务同时启动 Playwright 可能 OOM。
4. **不是真正的队列** — 没有优先级、重试、延迟执行、死信队列等能力。
5. **无进度报告** — 任务只有 queued/running/终态，没有中间进度（如"已完成 1/2 个 source"）。
6. **result 全量存储** — 成功任务的完整 envelope 存在内存中，大批量结果可能占用较多内存。
7. **daemon thread 不可取消** — 一旦启动，无法从外部中止正在运行的任务。

---

## 8. Recommended Next Step

**将前端 Agent 路径迁移到异步骨架。**

具体：将 `real_analysis_service.py` 中的 `run_real_listings_analysis` 从直接 import `analysis_bridge` 改为 HTTP `POST /tasks` + 轮询 `GET /tasks/{task_id}`。这样：
- Streamlit 进程不再运行 Playwright 和分析引擎（消除阻塞和 OOM）。
- 前端用 `st.spinner` + 轮询循环等待结果。
- 后端在独立线程中完成抓取和分析。

同时添加并发信号量（`threading.Semaphore(1)`），防止多个 Playwright 实例同时运行导致 OOM。

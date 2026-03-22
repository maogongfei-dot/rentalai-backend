# P9 Phase4 Async Expansion Plan

---

## 1. Second Flow Chosen

**流程：Agent 入口的多平台抓取 + 批量分析。**

调用链：`render_p5_agent_entry` → `_process_agent_batch_submit` → `run_agent_intent_analysis` → `run_real_listings_analysis`（同步）。

### 选择理由

1. **它是当前最大的同步阻塞和 OOM 风险源。** Agent 是用户最常触发多平台分析的入口（自然语言输入 → 解析 → Continue to Analysis）。当前它在 Streamlit 进程内直接运行 Playwright + analysis_bridge，与 batch 按钮的旧同步路径相同——P9 Phase3 Closeout 明确将其列为 "What Still Blocks Scale" 第一项。

2. **它与已验证的 Pilot 调用的是完全相同的后端函数。** `run_agent_intent_analysis` 最终调用的 `run_real_listings_analysis` 与 batch 按钮使用的是同一个函数。这意味着后端 `POST /tasks` 端点无需任何修改——请求体和执行逻辑完全复用。

3. **前端改动量极小。** 只需要：
   - `agent_runner.py`：增加一个 `run_agent_intent_analysis_async` 函数（或给现有函数加 `async_mode` 参数），内部调用 `run_real_listings_analysis_async` 代替 `run_real_listings_analysis`。
   - `agent_entry.py`：在 `_process_agent_batch_submit` 中增加 `if async_mode` 分支，与 batch 按钮的实现模式完全一致。
   - 不需要修改 TaskStore、后端端点、异步服务函数或 UI 渲染逻辑。

4. **风险极低。** 旧同步路径保留为 fallback（async mode 默认关闭），downstream session state 写入和 batch 结果渲染完全不变。

### 为什么现在适合扩展

- Phase3 骨架已通过逐行代码审查，确认状态流转正确、线程安全、Semaphore 保护到位、零回归。
- Pilot 已验证异步函数的返回格式与同步版完全兼容，downstream UI 无需修改。
- Agent 入口是唯一一个仍然在 Streamlit 进程中直接运行 Playwright 的路径。不扩展到 Agent，异步化的实际收益只覆盖了一半用户场景。

---

## 2. Standard Async Pattern (Backend)

所有需要异步化的流程都应遵循以下后端接入模式：

### 2.1 定义任务输入

使用 Pydantic `BaseModel` 定义请求体，包含该流程必要的参数和合理默认值。模型名以 `...Request` 结尾。

```python
class AnalyzeRealRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    sources: Optional[list[str]] = Field(default=None)
    limit_per_source: int = Field(default=10, ge=1, le=50)
    # ... 其余参数
```

### 2.2 创建任务

复用 `POST /tasks` 端点。如果未来需要多种任务类型，可在请求体中增加 `task_type` 字段区分，但当前所有异步流程都是 "multi-source analysis"，共享同一端点。

```
POST /tasks
→ TaskStore.create(input_summary={...})
→ threading.Thread(target=_run_analysis_task, daemon=True).start()
→ return { task_id, status: "queued" }
```

### 2.3 执行任务

在 daemon thread 中执行：

1. 获取 `_TASK_SEMAPHORE`（排队等待或失败）。
2. `mark_running(task_id)`。
3. 调用业务函数。
4. 成功 → `mark_success(task_id, result, degraded=..., elapsed=...)`。
5. 异常 → `mark_failed(task_id, error, elapsed=...)`。
6. `finally` → 释放 semaphore。

### 2.4 返回 Summary

`GET /tasks/{task_id}` 返回标准结构：

```json
{
  "task_id": "...",
  "status": "queued | running | success | failed | degraded",
  "created_at": "...",
  "updated_at": "...",
  "input_summary": { ... },
  "degraded": false,
  "elapsed_seconds": null,
  "error": null,
  "result": { ... }   // 仅 success/degraded 时包含
}
```

---

## 3. Standard Async Pattern (Frontend)

所有异步前端入口都应遵循以下模式：

### 3.1 触发任务

在用户操作（按钮点击 / Agent Continue）时，判断 `_p7_async` toggle：
- **开启** → 走异步路径。
- **关闭** → 走旧同步路径（fallback）。

### 3.2 获取 task_id

调用 `run_real_listings_analysis_async(api_base_url=..., on_status=callback, ...)`。函数内部：
1. `POST {api_base}/tasks` → 拿到 `task_id`。
2. 通过 `on_status(task_id, "queued")` 通知前端。

### 3.3 轮询状态

函数内部自动轮询（3 秒间隔，最多 80 次）：
- 每次 `GET {api_base}/tasks/{task_id}`。
- 通过 `on_status(task_id, status)` 更新前端显示。
- 遇到终态（success / degraded / failed）停止。

前端通过 `st.empty()` + `on_status` 回调实时显示：
```
Task a1b2c3d4e5f6 — running
```

### 3.4 展示结果

异步函数返回与同步版相同的三元组 `(envelope, error, request_payload)`。写入 `st.session_state["p2_batch_last"]` 后 `st.rerun()`，downstream batch 结果渲染完全复用。

---

## 4. Task Lifecycle Standard

```
                    ┌──────── Semaphore 超时
                    │
  queued ──→ failed ◄────── 任何异常
     │
     ▼
  running ──→ success       全部完成
     │    └─→ degraded      部分 source 失败，result 仍可用
     │    └─→ failed        运行中异常
     │
     ▼ (TTL 过期或容量淘汰)
  [evicted]                 从 TaskStore 中移除
```

| 状态 | 含义 | `result` | `error` | `degraded` |
|------|------|----------|---------|------------|
| `queued` | 已创建，等待执行 | — | — | `false` |
| `running` | 后台线程正在执行 | — | — | `false` |
| `success` | 全部完成 | ✅ 完整 | — | `false` |
| `degraded` | 完成但部分 source 失败 | ✅ 部分 | — | `true` |
| `failed` | 异常或 semaphore 超时 | — | ✅ | `false` |

所有状态转换都通过 `TaskStore._update` 执行，自动设置 `updated_at`。

---

## 5. Error Handling Standard

### 后端

| 场景 | 处理方式 |
|------|----------|
| Semaphore 5s 内未获取 | `mark_failed("Server busy — another task is running")` |
| `run_multi_source_analysis` 抛出异常 | `mark_failed(str(exc), elapsed=...)` + `logger.error(..., exc_info=True)` |
| 分析成功但部分 source 超时/失败 | `mark_success(result, degraded=True, elapsed=...)` |
| 未知异常 | 全局 `except Exception` 捕获，不泄漏到主线程 |

### 前端

| 场景 | 处理方式 |
|------|----------|
| `POST /tasks` 失败 | 返回 synthetic failure envelope + error 字符串 |
| 轮询中网络错误 | `continue` — 重试下一轮，不中断 |
| 任务 `status == "failed"` | 提取 `error`，返回 synthetic failure envelope |
| 轮询超限（80 次） | 返回 synthetic failure envelope + task_id 供手动查询 |
| 函数整体异常 | `except Exception` 写入 failure session state |

### 统一原则

- **failed** = 前端显示 `st.error(message)` 或 batch error block。
- **degraded** = 前端正常显示 result，但 debug 区标记 `degraded=true`。
- **所有失败路径必须产生一个与同步版格式兼容的 envelope**，确保 downstream 渲染不崩。

---

## 6. Logging & Monitoring Standard

### 任务生命周期日志

`TaskStore._update` 自动产出每次状态变更的日志：
```
[TASK] a1b2c3d4e5f6 -> running
[TASK] a1b2c3d4e5f6 -> success
```

### 失败日志

`_run_analysis_task` 中 `except` 块：
```
[TASK] a1b2c3d4e5f6 failed: ConnectionError: ...
  (+ full stack trace via exc_info=True)
```

### 性能日志

HTTP middleware 自动为所有 `/tasks` 请求产出 `[PERF]` 日志。分析引擎内部的 `[PERF]` 日志（pipeline、scraper、batch analysis）在后台线程中正常输出。

### 报警

- `POST /tasks` 如果触发 500 → 全局异常处理器 → `send_alert(level="P1")`。
- 慢请求（≥ 5s）→ `send_alert(level="P2")`（仅限 HTTP handler 本身，不含后台线程）。

### 问题定位路径

1. 前端 `p7_last_debug.async_task_id` → 找到 task_id。
2. 后端日志搜索 `[TASK] {task_id}` → 看到状态流转。
3. 如果 failed → 日志中有完整 stack trace。
4. `GET /tasks/{task_id}` → 查看 `error`、`elapsed_seconds`。
5. `GET /tasks` → 查看是否有 stuck（queued/running 超过预期时间的）任务。

---

## 7. What Changes from "Pilot" to "System"

| 维度 | Pilot（Phase3） | System（Phase4+） |
|------|-----------------|-------------------|
| **入口数量** | 1 个（batch 按钮） | 2+ 个（batch + Agent） |
| **并发模式** | Semaphore(1) + 直接失败 | Semaphore(1) + **排队等待**（blocking acquire + timeout） |
| **前端模式** | 每个入口单独写分支 | 统一通过 `run_real_listings_analysis_async` + `on_status` |
| **Agent 集成** | 未接入 | 接入（`agent_runner.py` 增加 async 分支） |
| **文档** | 单独试点文档 | 标准模式文档 + 规则文档 |
| **回退方式** | checkbox 关闭 | 同上，不变 |

### 关键升级点

1. **Semaphore 改为排队式。** `_TASK_SEMAPHORE.acquire(timeout=300)` — 第二个任务排队等待最多 5 分钟，而非 5 秒后直接失败。这对 Agent 入口至关重要：用户在 Agent 区和 batch 区先后触发分析时，第二个应排队而非报错。

2. **Agent runner 增加 async 分支。** `run_agent_intent_analysis` 增加 `async_mode` / `api_base_url` 参数，内部根据 flag 选择 `run_real_listings_analysis` 或 `run_real_listings_analysis_async`。

3. **`agent_entry.py` 传递 async flag。** `_process_agent_batch_submit` 接收 `async_mode` 参数，转发到 `run_agent_intent_analysis`。`render_p5_agent_entry` 接收外部的 `_p7_async` 值。

---

## 8. Incremental Expansion Plan

### Phase 4 Step2 — Agent 入口接入异步

**改动文件：**
- `api_server.py`：Semaphore acquire timeout 从 5s 改为 300s（排队式）。
- `agent_runner.py`：`run_agent_intent_analysis` 增加 `async_mode` + `api_base_url` 参数，async 时调用 `run_real_listings_analysis_async`。
- `agent_entry.py`：`_process_agent_batch_submit` 和 `render_p5_agent_entry` 传递 `async_mode` 和 `api_base_url`。
- `app_web.py`：向 `render_p5_agent_entry` 传递 `_p7_async` 和 `_api_base`。

**验证方式：** 勾选 Async mode → Agent 区输入自然语言 → Parse → Continue to Analysis → 任务提交到后端 → 轮询 → 结果显示在 batch 区。

### Phase 4 Step3 — 收口复测

**目标：** 确认 Agent + batch 两个入口都能稳定走异步路径，旧同步路径不受影响。

### Phase 5（未来） — 跨 worker TaskStore

**前置条件：** 切换到 gunicorn 多 worker 部署。
**方案选择：** SQLite WAL 模式（最小依赖）或 Redis（如果已引入）。
**影响：** 仅替换 `TaskStore` 内部实现，接口不变。

### Phase 6（未来） — Result 缓存 + 去重

**目标：** 对相同输入参数的分析请求进行结果缓存（LRU），避免重复 Playwright 运行。
**影响：** 在 `_run_analysis_task` 中增加缓存查询层。

---

## 9. Risks of Expansion

| 风险 | 等级 | 应对 |
|------|------|------|
| Agent + batch 同时提交，Semaphore 排队超时 | **中** | 排队式 acquire(timeout=300)。超时后 `mark_failed("Queue timeout")`，前端显示提示 |
| Agent 入口的 `on_status` 回调与 Streamlit 状态管理冲突 | **低** | 使用与 batch 按钮完全相同的 `st.empty()` + 回调模式，已验证可行 |
| `_process_agent_batch_submit` 修改引入回归 | **低** | 新逻辑放在 `if async_mode` 分支，`else` 保留旧代码不动 |
| 排队等待期间 Streamlit 脚本阻塞 | **已知** | 与 Pilot 相同——Streamlit 执行模型固有限制。`on_status` 回调提供最小进度反馈 |
| TaskStore 内存压力增加 | **低** | Agent 和 batch 共享 TaskStore，上限仍为 200 条。两个入口的使用频率不会同时很高 |

---

## 10. Recommended Next Step

**进入 P9 Phase4 Step2 — Agent 入口异步化实施。**

具体动作：

1. `api_server.py`：`_TASK_SEMAPHORE.acquire(timeout=5)` → `acquire(timeout=300)`。
2. `agent_runner.py`：`run_agent_intent_analysis` 增加 `async_mode` / `api_base_url` 参数。
3. `agent_entry.py`：`_process_agent_batch_submit` 和 `render_p5_agent_entry` 传递 async 相关参数。
4. `app_web.py`：向 `render_p5_agent_entry` 传递 `_p7_async` 和 `_api_base`。
5. 验证 + 文档更新。

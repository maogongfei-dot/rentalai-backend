# P9 Phase4 Async System Status

---

## Current Coverage

| # | 流程 | 入口 | 异步方式 | 状态 |
|---|------|------|----------|------|
| 1 | 多平台抓取 + 批量分析（Batch 按钮） | `app_web.py` → `run_real_listings_analysis_async` | `POST /tasks` + 轮询 | ✅ 验证通过 |
| 2 | Agent 入口 → 多平台抓取 + 批量分析 | `agent_entry.py` → `agent_runner.py` → `run_real_listings_analysis_async` | `POST /tasks` + 轮询 | ✅ 已接入 |

两条路径最终调用完全相同的后端执行函数 (`_run_analysis_task`) 和前端异步服务函数 (`run_real_listings_analysis_async`)。

---

## System Maturity

**初级 → 可用**

| 能力 | 状态 |
|------|------|
| 任务提交 | ✅ 可用 |
| 后台执行 | ✅ daemon thread |
| 状态查询 | ✅ GET /tasks/{task_id} |
| 并发控制 | ✅ Semaphore(1) + 排队 |
| 错误捕获 | ✅ failed / degraded |
| 前端轮询 | ✅ on_status 回调 |
| 活跃任务列表 | ✅ GET /tasks |
| 任务持久化 | ❌ 进程内 dict |
| 跨 worker 共享 | ❌ 不支持 |
| 任务取消 | ❌ 不支持 |
| 结果缓存 | ❌ 不支持 |
| 定时清理 | ✅ TTL 10 分钟 |
| 最大容量 | ✅ 200 任务 |

---

## Consistency Level

**完全一致。**

两个已接入流程复用了同一套：
- 后端端点（`POST /tasks` / `GET /tasks/{task_id}`）
- 请求体模型（`AnalyzeRealRequest`）
- 执行函数（`_run_analysis_task`）
- 前端服务函数（`run_real_listings_analysis_async`）
- 回调模式（`on_status`）
- Session state 写入（`p2_batch_last`）

未发现任何偏差。新流程的接入无需修改后端代码，仅需在前端增加参数传递。

---

## Biggest Weak Points

1. **进程内 TaskStore 无法跨 worker。** 当 gunicorn 以多 worker 部署时，不同 worker 拥有独立的 TaskStore，前端创建任务的 worker 和查询任务的 worker 可能不同，导致 404。这是进入生产多 worker 部署前必须解决的阻塞项。

2. **Streamlit 轮询阻塞。** `time.sleep(3)` 在轮询期间阻塞整个 Streamlit 脚本。用户无法在等待期间进行其他操作（填表、切标签等）。这是 Streamlit 执行模型的固有限制。

3. **无任务取消 / 无超时终止。** 一旦任务提交无法中止。如果 Playwright 卡住，任务会一直占用 Semaphore 直到进程被杀。虽然 `mark_timeout` 方法存在，但当前没有任何 watchdog 调用它。

---

## Ready for Scale?

**Not yet**, but ready for controlled production use.

当前系统足以支撑单 worker 部署下的少量用户（< 10 并发）正常使用异步模式。标准模式已验证为可复用——后续新流程的接入预计只需前端传参修改。

进入规模化之前需要解决：
1. 跨 worker TaskStore（Redis / DB / sticky sessions）。
2. 任务超时 watchdog。
3. Streamlit 替代方案或 WebSocket 推送（长期）。

---

## Next Focus

1. **P9 Phase4 收口复测** — 确认两个入口都稳定可用后，Phase4 收口。
2. **跨 worker TaskStore 方案设计** — 为生产多 worker 部署做准备。
3. **结果缓存 / 去重** — 相同参数请求复用结果，减少 Playwright 运行次数。

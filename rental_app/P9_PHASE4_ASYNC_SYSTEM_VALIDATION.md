# P9 Phase4 Async System Validation

---

## 1. Validation Scope

本轮验收覆盖模块：

- 后端任务系统：`task_store.py`、`api_server.py`（`POST /tasks`、`GET /tasks/{task_id}`、`GET /tasks`、`GET /tasks/stats`、`GET /tasks/system`）。
- 前端异步服务：`web_ui/real_analysis_service.py`（`run_real_listings_analysis_async`）。
- 两个已接入异步流程：
  - Batch 按钮路径（`app_web.py` -> `run_real_listings_analysis_async`）
  - Agent Continue 路径（`agent_entry.py` -> `agent_runner.py` -> `run_real_listings_analysis_async`）
- 监控相关：API perf 日志、task 日志、`send_alert` 失败告警调用。

未纳入本轮验收：

- 新流程接入（本轮不扩展范围）。
- scraper 内部抓取质量与算法准确性（不属于任务调度验收目标）。
- 分布式队列能力（Redis/Celery/RabbitMQ），按阶段原则明确不引入。

---

## 2. Task Lifecycle Validation

验证结论：`queued -> running -> success/failed/degraded` 生命周期正常，调度行为符合“最小队列化 + 并发控制”目标。

关键验收点：

- 新任务创建后先进入 `queued`，再由 worker 消费进入 `running`。
- 并发上限生效（`MAX_CONCURRENT_TASKS` 控制 worker 数量，running 不超过上限）。
- running 结束后 queued 自动补位，无需额外触发调度。
- `success` / `failed` / `degraded` 均可落盘并可回读。
- `updated_at`、`started_at`、`finished_at` 均正常更新。

本轮实测（离线 TestClient + fake analysis bridge）观察到：

- 初始状态快照：`queued_count=2`、`running_count=1`（并发=1 场景）。
- 终态快照：`success=1`、`degraded=1`、`failed=1`。
- 三个任务全部具备 `started_at` 与 `finished_at`。

风险提示：

- 当前为进程内队列，进程重启会丢失内存队列本体（但任务记录可恢复为可见状态）。

---

## 3. API Consistency Validation

结论：create/get/list/system status 接口整体稳定，两个异步流程使用同一接口结构与状态语义，无“流程特殊化”偏差。

检查结果：

- `POST /tasks`：稳定返回 `{task_id, status}`，保持兼容。
- `GET /tasks/{task_id}`：状态字段完整（含 `task_type`、`stage`、`priority`、`started_at`、`finished_at`）。
- `GET /tasks`：`active/recent` 模式正常。
- `GET /tasks/stats`：状态统计正常。
- `GET /tasks/system`：最小系统观测正常（queued/running/success/failed/degraded + 并发上限）。

本轮低风险修正：

- 修复了路由顺序问题：`/tasks/{task_id}` 原先会吞掉 `/tasks/system` 和 `/tasks/stats`，导致 404。
- 修复后 `system/stats` 已按预期返回。

---

## 4. Persistence Validation

结论：持久化与恢复链路可用，历史任务可查询，字段完整性基本满足当前阶段。

检查结果：

- `TaskStore` 状态变更后会写入 JSON（`tmp -> os.replace`）。
- 任务终态与新字段可持久化并重载（包含 `started_at`、`finished_at`、`priority` 等）。
- `GET /tasks?mode=recent` 可查看历史任务，适合运维回查。
- 重启恢复时，旧 `queued/running` 会转为 `interrupted`，避免“假 running”。

本轮小修正：

- `interrupted` 转换时补齐 `finished_at`（若缺失），避免终态时间字段不完整。

---

## 5. Frontend Integration Validation

结论：前端异步闭环稳定，两个流程都能创建任务、拿到 task_id、轮询状态并写入统一结果结构；同步路径未被误伤。

检查要点：

- Batch 与 Agent 都通过同一个 `run_real_listings_analysis_async`。
- 创建成功后都能拿到 `task_id`，并通过 `on_status` 显示 queued/running 等状态。
- 终态后都写入 `p2_batch_last` / `p2_batch_last_request`，结果展示路径一致。
- 异常路径都返回 synthetic failure envelope，不会中断 UI 主流程。
- `async_mode` 关闭时仍走原同步路径，兼容保留。

风险：

- Streamlit 轮询采用 `time.sleep`，等待期间脚本阻塞，交互体验仍有限（已知限制，非回归）。

---

## 6. What Is Now Reliable

当前已稳定的能力：

1. 任务从“创建即线程争抢”升级为“入队 + 固定 worker 执行”，调度可控。
2. 并发上限明确可配置（`MAX_CONCURRENT_TASKS`），可防重任务同时冲击。
3. 前后端统一异步模式已在两个流程复用，接口语义与结果封套一致。
4. 任务元数据可持久化、可恢复、可回查（含 recent/stats/system 观察面）。
5. 基础日志与失败告警链路可用于定位调度与执行问题。

---

## 7. What Still Limits Scale

仍阻碍进一步扩展的关键点：

1. 单进程内存队列，无法跨 worker/跨实例共享。
2. 缺少取消、自动重试、死信队列等生产级任务治理能力。
3. 缺少硬 watchdog（任务卡死时无法主动中止 worker 内执行）。
4. 轮询模式仍是拉取式 + Streamlit 阻塞体验，不是推送式实时体验。

---

## 8. Phase4 Final Verdict

**Phase4 Validated**

原因：

- 本阶段目标（异步统一化、任务可靠性、最小队列化、并发控制、可观测性增强）均已实现并经代码 + 离线实测验证通过。
- 发现的关键问题（`/tasks/system`/`/tasks/stats` 路由冲突）已做最小修正并复测通过。
- 当前剩余问题主要属于“下一阶段扩展能力”，不阻断 Phase4 收口。

---

## 9. Recommended Next Step

建议进入：**P9 Phase5《跨进程任务共享 + 任务治理增强设计》**。

优先顺序建议：

1. 设计可共享的 TaskStore（Redis/SQLite/KV 三选一评估）。
2. 增加任务 watchdog + 取消机制（先最小可控版本）。
3. 在保持现有 API 兼容前提下补充重试策略与运维可观测字段。

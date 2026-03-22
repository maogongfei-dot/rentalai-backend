# P9 Phase4 Queue and Concurrency Upgrade

---

## 1. Current Scheduling Risks

- 旧实现里，`POST /tasks` 创建任务后会立刻起一个后台线程执行。
- 并发控制依赖线程内 `Semaphore.acquire(timeout=300)`，本质是“先起线程，再在运行路径阻塞等待”。
- 当短时间提交很多任务时，会堆积大量“等待信号量”的线程，队列形态不可见、调度不可控。
- 超过 5 分钟未拿到信号量会直接 `failed`，属于资源等待失败，不是业务执行失败，容易误导排障。
- **最危险点**：高峰提交下线程堆积 + 重任务排队不可观测，存在拖慢 API 进程甚至触发内存压力的风险。

---

## 2. Queue Strategy

- 采用进程内轻量队列：`queue.Queue`（无 Redis / Celery / RabbitMQ）。
- 新任务创建后仍是 `status=queued`，并写入队列等待 worker 消费。
- worker 从队列取出任务后才进入 `running`，执行完成后自动拉取下一个任务。
- 设计理由：改动最小、风险最低、与当前 `TaskStore + FastAPI + thread` 风格一致。
- 局限性：
  - 仅单进程有效，跨 worker 不共享队列；
  - 进程重启后内存队列丢失（`TaskStore` 会把旧 queued/running 记录标为 `interrupted`）；
  - 无优先级调度和重试机制。

---

## 3. Concurrency Control

- 增加配置：`MAX_CONCURRENT_TASKS`（默认 `2`）。
- 服务启动时创建固定数量 daemon worker（等于并发上限），每个 worker 串行处理任务。
- 因为同一时刻最多只有 `MAX_CONCURRENT_TASKS` 个 worker 在执行业务，`running` 数量天然受限。
- 设置为 2 的原因：在不明显拉高资源风险的前提下，比单并发更平衡吞吐与稳定性，且可通过环境变量快速回退或调整。

---

## 4. Scheduler Behavior

- 新任务创建后：
  1. 写入 `TaskStore`，状态为 `queued`；
  2. 放入内存队列；
  3. 立即返回 `{task_id, status}`（保持兼容）。
- worker 取到任务后：
  1. 标记 `running`（`stage=scraping`）并写 `started_at`；
  2. 调用 `run_multi_source_analysis` 执行；
  3. 成功写 `success/degraded`，失败写 `failed`，并写 `finished_at`。
- 当某个 running 任务结束后，空闲 worker 自动继续消费下一个 queued 任务，无需额外触发调度。
- 关键日志最小覆盖：入队、出队开始执行、成功结束、失败结束。

---

## 5. Task Model Enhancements

本轮新增字段：

- `priority`（`int`，默认 0）：预留优先级位，当前不做复杂调度，仅保持模型可扩展。
- `started_at`（`str | None`）：任务实际开始执行时间（首次进入 running 时写入）。
- `finished_at`（`str | None`）：任务进入终态（success/degraded/failed/timeout）时间。

已有字段继续沿用：

- `task_type`：区分任务类型；
- `stage`：表示执行阶段；
- `last_error_at`：失败时间定位。

---

## 6. API Impact

- `POST /tasks`：接口形式不变，仍即时返回 `task_id` 和 `status`（兼容）。
- `GET /tasks/{task_id}`：向后兼容增强，新增 `priority`、`started_at`、`finished_at`。
- `GET /tasks`：保持现有 `active/recent` 语义，不破坏调用方。
- 新增 `GET /tasks/system`（最小观察接口）：
  - `queued_count`
  - `running_count`
  - `success_count`
  - `failed_count`
  - `degraded_count`
  - `max_concurrent_tasks`

---

## 7. Reliability / Stability Gains

- 从“创建即起线程 + 运行路径阻塞”升级到“先入队，再由固定 worker 执行”，调度行为更可控。
- `running` 上限可配置，避免多个重任务同时冲击导致系统抖动。
- 任务等待不再通过线程阻塞表达，减少高峰期线程堆积风险。
- 新增系统状态观察面，能快速判断是“排队中”还是“执行中”。
- 时间字段更完整（started/finished），排障和性能分析更直接。

---

## 8. Remaining Limitations

- 仍是单进程内存队列，不支持多 worker 共享。
- 无自动重试、无取消、无死信队列。
- 无真正优先级调度（`priority` 仅预留）。
- 无硬 watchdog 终止卡死任务（仍依赖分析层内部 timeout / 异常返回）。
- 非正式分布式任务系统，不能替代 Redis/Celery 级别能力。

---

## 9. Recommended Next Step

建议进入：**Phase4 - Step5《收口复测 + 压测验证》**。

重点执行：
1. 并发/排队行为回归（连续提交 3~5 个任务，验证 queued -> running 轮转）；
2. 失败注入验证（异常路径日志与状态完整性）；
3. 观察 `GET /tasks/system` 与 `GET /tasks?mode=recent` 是否满足一线排障；
4. 形成下一阶段“跨进程共享 TaskStore”技术选型（Redis/SQLite/外部 KV）。

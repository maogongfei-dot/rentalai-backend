# P9 Phase4 Task Reliability Upgrade

---

## 1. Current Reliability Risks (Before This Step)

| 风险 | 严重度 | 说明 |
|------|--------|------|
| 重启丢失全部任务状态 | High | TaskStore 纯内存 dict，进程退出即清零 |
| 无法查看历史任务 | Medium | `GET /tasks` 仅返回 queued/running，完成后消失 |
| 缺少任务类型/阶段字段 | Medium | 排查时无法区分任务来源或当前执行阶段 |
| 无状态分布统计 | Low | 无法快速了解任务系统健康度 |
| TTL 仅 10 分钟 | Low | 完成的任务很快被逐出，回查困难 |
| failed/timeout 缺少 `last_error_at` | Low | 无法定位错误发生的精确时刻 |

---

## 2. Persistence Strategy

### 方案

每次任务状态变更（create / mark_running / mark_success / mark_failed / mark_timeout）时，自动将整个 TaskStore 序列化为 JSON，写入本地文件。写入采用 `tmp → os.replace` 原子替换，避免写半截文件。

### 文件位置

默认 `rental_app/.task_store.json`（与 `task_store.py` 同目录）。可通过 `RENTALAI_TASK_STORE_PATH` 环境变量覆盖。

### 启动恢复

`TaskStore.__init__` 时自动读取持久化文件。读入的记录中，处于 `queued` 或 `running` 状态的任务会被标记为 `interrupted`——因为上一次进程中执行它们的 background thread 已不存在，标记为 interrupted 比保留虚假的 running 状态更准确。

### 局限性

1. **单进程专用。** 多 worker 同时写同一个 JSON 文件会覆盖，不做跨进程锁。
2. **result 可能较大。** 如果任务返回的 result 包含大量 listing 数据，JSON 文件可能增长到数 MB。TTL 逐出机制保持文件尺寸有限。
3. **不是真正的持久化队列。** 已中断的任务不会自动重试。

---

## 3. Task Model Enhancements

### 新增字段

| 字段 | 类型 | 用途 |
|------|------|------|
| `task_type` | `str` | 标识任务来源/类型，当前固定 `"multi_source_analysis"`，未来可扩展 |
| `stage` | `str` | 任务当前执行阶段：`queued` → `scraping` → `done` / `failed` / `timeout` / `interrupted` |
| `last_error_at` | `str \| None` | 最近一次错误发生的 UTC ISO 时间戳，仅 failed/timeout 时写入 |

### 新增状态

| 状态 | 含义 |
|------|------|
| `interrupted` | 任务在进程重启前处于 queued/running，重启后被自动标记 |

### 其他调整

- **TTL 从 600 秒提升到 3600 秒（1 小时）。** 完成的任务保留更久，方便回查。
- **`_TERMINAL_STATUSES` 集合。** 用于逐出判断，包括 `success`、`failed`、`degraded`、`timeout`、`interrupted`。

---

## 4. API Impact

### 现有接口兼容性

| 接口 | 变化 |
|------|------|
| `POST /tasks` | **无破坏性变化。** 返回仍为 `{task_id, status}`。内部 TaskRecord 多了字段但不影响创建响应。 |
| `GET /tasks/{task_id}` | **向后兼容增强。** 新增返回 `task_type`、`stage`、`last_error_at` 字段。现有消费方忽略未知字段即可。 |
| `GET /tasks` | **向后兼容增强。** 新增 `mode` query 参数（默认 `active`，保持旧行为）。`mode=recent` 可查看所有状态的最近 N 条任务。 |

### 新增接口

| 接口 | 说明 |
|------|------|
| `GET /tasks/stats` | 返回 `{total, by_status: {queued: N, running: N, ...}}`。用于快速观察任务系统健康度。 |

---

## 5. Recovery Behavior

### 服务重启后

1. `TaskStore.__init__` 读取 `.task_store.json`。
2. `queued` / `running` 状态的任务被重标为 `interrupted`，并设置 `error = "Process restarted while task was in progress."`、`last_error_at = now`。
3. 其他终态任务（`success`、`failed`、`degraded`、`timeout`）保持原样。
4. 前端通过 `GET /tasks/{task_id}` 可查到 `status: "interrupted"`，不再误以为任务仍在运行。

### 能保留的

- 所有已到达终态的任务元数据（task_id、status、input_summary、error、elapsed_seconds 等）。
- 已 success/degraded 的任务 result 数据（除非被 TTL 逐出）。

### 仍不能恢复的

- 被中断的任务**不会自动重试**。用户需要手动重新提交。
- 如果 `.task_store.json` 文件被删除或损坏，所有历史记录丢失。
- 多 worker 部署时，每个 worker 拥有独立的 JSON 文件，不共享。

---

## 6. Reliability Gains

| 维度 | 之前 | 之后 |
|------|------|------|
| 重启后任务可见性 | ❌ 全部丢失 | ✅ 终态任务保留，running 标记 interrupted |
| 历史任务查看 | ❌ 仅 active | ✅ `GET /tasks?mode=recent` 查看最近 30 条 |
| 任务类型识别 | ❌ 无字段 | ✅ `task_type` 字段 |
| 执行阶段追踪 | ❌ 仅 status | ✅ `stage` 字段（queued/scraping/done/failed/...） |
| 错误时间定位 | ❌ 无 | ✅ `last_error_at` |
| 系统健康快照 | ❌ 无 | ✅ `GET /tasks/stats` |
| 任务可见窗口 | 10 分钟 | 1 小时 |

---

## 7. Remaining Limitations

1. **单进程 / 单 worker 专用。** 多 worker 部署前必须迁移到 Redis 或 DB。
2. **无自动重试。** interrupted 任务需手动重新提交。
3. **无任务取消。** 无法中止正在执行的 Playwright 任务。
4. **JSON 文件非并发安全。** 两个进程同时写会覆盖。
5. **result 占用磁盘。** 大量任务 + 大 result 时文件可能增长至 MB 级别。
6. **无超时 watchdog。** 如果 Playwright 永久卡住，任务会持续占用 Semaphore。

---

## 8. Recommended Next Step

**P9 Phase4 Step4 — 收口复测 + Phase4 成熟度评估。**

确认持久化、历史查看、interrupted 恢复、stats 端点都正常工作后，Phase4 收口。下一阶段应关注：
1. 跨 worker TaskStore（Redis / SQLite / 外部 KV）。
2. 任务超时 watchdog + 取消机制。

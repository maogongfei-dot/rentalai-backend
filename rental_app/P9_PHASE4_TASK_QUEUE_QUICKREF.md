# P9 Phase4 Task Queue Quick Reference

---

## New Task Lifecycle

- `queued`
- `running`
- `success`
- `failed`
- `degraded`

---

## Queue Rules

- 新任务通过 `POST /tasks` 创建后先进入 `queued`。
- 任务被放入进程内 `queue.Queue`，等待 worker 消费。
- 只有 worker 取出任务时才转为 `running`。

---

## Concurrency Rules

- 最大并发由 `MAX_CONCURRENT_TASKS` 控制（默认 `2`）。
- 系统只启动固定数量 worker，因此同一时刻 running 不会超过上限。
- 当 running 已满时，新任务保持 `queued`，直到有 worker 空闲。

---

## System Status

- 观察接口：`GET /tasks/system`
- 返回最小状态计数：
  - `queued_count`
  - `running_count`
  - `success_count`
  - `failed_count`
  - `degraded_count`
  - `max_concurrent_tasks`

---

## Notes

- 当前是轻量队列化版本（进程内队列 + 固定 worker）。
- 不引入外部中间件，低风险、可快速回退。
- 仍不等同于正式分布式队列系统（无跨进程共享、无重试、无取消、无死信）。

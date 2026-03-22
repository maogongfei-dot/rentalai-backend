# P9 Phase3 Async Decision Summary

## Must Async

1. **Agent 多平台抓取 + 分析 (`run_multi_source_analysis`)** — 耗时 30–120s，远超同步可接受范围。改为 `POST /analyze-real` 返回 task_id + `GET /task/{task_id}` 轮询结果。这是最高优先级改造。

2. **大批量分析 (> 20 项 `/analyze-batch`)** — 超过 10s 的同步请求占满 worker。可选方案：保持同步但限制到 ≤ 10 项，或引入异步任务模型。当前优先级低于 Agent 路径。

## Can Stay Sync

1. **`/analyze` 单条分析** — 0.3–1s，即时反馈，异步化反而增加延迟。
2. **`/score-breakdown`、`/risk-check`、`/explain-only`** — 同上，均 < 1s。
3. **`/analyze-batch` (≤ 10 项)** — 2–5s，用户可接受的同步等待。
4. **`/health`、`/alerts`** — 实时状态查询，必须同步。

## Must Decouple

1. **Streamlit ↔ Playwright/Scraper** — Chromium 运行在 Streamlit 单进程中，1 个抓取任务阻塞所有用户。必须将 Playwright 移到后端进程。改动点：`real_analysis_service.py` 从直接 import `analysis_bridge` 改为 HTTP 请求后端。

2. **同步 HTTP 请求 ↔ 长耗时任务** — 30–120s 的任务不能在 HTTP 请求生命周期内同步完成。必须引入"提交 → 后台执行 → 轮询结果"模式。改动点：新增 `TaskStore` + `/analyze-real` + `/task/{task_id}`。

3. **单 uvicorn worker → gunicorn 多 worker** — 单 worker 无法同时处理多个 CPU-bound 请求。改动点：`render.yaml` 启动命令。

## Can Defer

1. **listings.json → 数据库** — 当前数据量极小，文件存储尚可。用户增长到 100+ 时再迁移。
2. **Redis 缓存** — 先用进程内 LRU cache 验证缓存效果，再考虑引入 Redis。
3. **Playwright 浏览器复用** — 复杂度高。先解耦到后端进程，再在后端内部做实例复用。
4. **ProcessPoolExecutor 替代 ThreadPoolExecutor** — GIL 限制在 2 worker 下影响可控。先增加 worker 数量，再评估多进程方案。
5. **Celery/RQ 任务队列** — 进程内 TaskStore + Thread 足以支撑 10–50 并发用户，不需要引入外部 broker。
6. **前端迁移 (React/Vue)** — 架构变更极大。Streamlit 在解耦 Agent 路径后，作为 MVP 前端仍可用。

## Next Focus

**Phase A：Agent 后端化 + 异步任务模型。**

在 FastAPI 后端新增 `POST /analyze-real` 和 `GET /task/{task_id}`，将 Playwright 和 `run_multi_source_analysis` 从 Streamlit 进程迁移到后端后台线程。前端改为 HTTP 提交 + 轮询，不再阻塞 Streamlit 进程。这一步消除系统最致命的单点瓶颈，预计将并发 Agent 用户承载从 1 提升到 3–5。

# P9 Phase3 Architecture Upgrade Plan

基于 `P9_PHASE3_SCALABILITY_RISK_MAP.md` 中识别的 Top 5 瓶颈和真实代码结构，设计分阶段的架构升级蓝图。目标是在不做全面重构的前提下，将系统承载能力从 ~1–3 并发用户提升到 ~20–50 并发用户。

---

## 1. Upgrade Goal

### 必须解决的问题

1. **消除 Agent 路径对前端的阻塞** — 1 个用户触发 Agent 抓取 = 所有用户被阻塞 30–120s，这在多用户场景下不可接受。
2. **后端并发能力提升** — 单 worker uvicorn 无法同时处理多个 CPU-bound 分析请求。
3. **避免重复计算** — 相同输入每次重新运行引擎，浪费计算资源。

### 为什么必须升级

当前系统的承载极限约 1 个并发 Agent 用户 + 3 个并发分析用户。超过这个阈值后，前端白屏、后端超时、内存溢出同时发生。这不是"性能优化"问题，而是"架构约束"问题 — 在当前架构下，任何代码级优化都无法突破单进程单线程的物理限制。

---

## 2. Current Pain Points

### 同步链路

```
当前 Agent 路径（耗时 30–120s，全部同步）：

用户点击 → Streamlit 进程内:
  real_analysis_service.run_real_listings_analysis()
    → analysis_bridge.run_multi_source_analysis()
      → multi_source_pipeline.run_multi_source_pipeline()
        → ThreadPoolExecutor: rightmove_pipeline / zoopla_pipeline
          → Playwright Chromium 启动 + 页面加载 + DOM 解析  ← 30–90s
        → dedupe + aggregate
      → analyze_multi_source_listings()
        → analyze_batch_request_body()
          → ThreadPoolExecutor: N × call_analysis_engine()  ← N × 0.5s
    → 整理 envelope, 返回结果
```

整条链路在 Streamlit 进程内同步执行，期间 `st.spinner` 阻塞 UI，其他用户的 WebSocket 消息排队。

### 阻塞链路

| 链路 | 耗时 | 阻塞范围 | 当前保护 |
|------|------|---------|---------|
| Agent 真实分析 | 30–120s | 全 Streamlit 进程 | 180s 硬超时 |
| `/analyze-batch` | N × 0.5s | uvicorn 线程池 | 50 项上限 |
| `/analyze` 单条 | 0.3–1s | uvicorn 线程池 | 120s timeout |
| Local engine | 0.3–1s | Streamlit 进程 | 10s 慢警告 |

### 耦合点

| 耦合 | 文件 | 风险 |
|------|------|------|
| Streamlit ↔ Playwright | `app_web.py` → `real_analysis_service.py` → `analysis_bridge.py` → `multi_source_pipeline.py` → Playwright | Chromium 运行在 Streamlit 进程中 |
| Streamlit ↔ Analysis Engine | `app_web.py` → `run_analysis_for_ui()` → `web_bridge.run_web_demo_analysis()` | `RENTALAI_USE_LOCAL=1` 时引擎在 Streamlit 进程内 |
| API Server ↔ Analysis Engine | `api_server.py` → `api_analysis.py` → `web_bridge` | 同步调用，请求期间占用 worker 线程 |
| Pipeline ↔ 文件存储 | `*_pipeline.py` → `listing_storage.save_listings()` | 并发写无锁保护 |

---

## 3. Proposed Target Architecture

### 目标拓扑（渐进式，非一步到位）

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Render (Oregon)                               │
│                                                                      │
│  ┌─────────────────────────┐                                        │
│  │  rentalai-ui (Streamlit) │  纯展示 + 轻量交互                     │
│  │  不运行引擎              │                                        │
│  │  不运行 Playwright       │  ──── HTTP ────┐                      │
│  │  只做 HTTP 请求 + 轮询   │                │                      │
│  └─────────────────────────┘                │                      │
│                                              ▼                      │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │  rentalai-api (FastAPI, gunicorn 2 workers)               │       │
│  │                                                          │       │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐  │       │
│  │  │ /analyze  │  │ /analyze-batch│  │ /analyze-real    │  │       │
│  │  │ (同步)    │  │ (同步)       │  │ (异步: 提交+轮询) │  │       │
│  │  └────┬─────┘  └──────┬───────┘  └────┬─────────────┘  │       │
│  │       │               │               │                │       │
│  │       ▼               ▼               ▼                │       │
│  │  ┌──────────────────────────────────────────────┐      │       │
│  │  │  Analysis Engine (web_bridge, in-process)     │      │       │
│  │  │  CPU-bound, ~0.3–1s/property                  │      │       │
│  │  │  + LRU 结果缓存                               │      │       │
│  │  └──────────────────────────────────────────────┘      │       │
│  │       │                                                │       │
│  │       │ (仅 /analyze-real)                             │       │
│  │       ▼                                                │       │
│  │  ┌──────────────────────────────────────────────┐      │       │
│  │  │  Scraper Pipeline (Playwright, in-process)    │      │       │
│  │  │  通过 ThreadPoolExecutor 运行                  │      │       │
│  │  │  120s per-source timeout                      │      │       │
│  │  └──────────────────────────────────────────────┘      │       │
│  │                                                        │       │
│  │  ┌──────────────────────────────────────────────┐      │       │
│  │  │  Task Store (进程内 dict, keyed by task_id)   │      │       │
│  │  │  保存异步任务状态与结果                        │      │       │
│  │  └──────────────────────────────────────────────┘      │       │
│  └──────────────────────────────────────────────────────────┘       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 与当前架构的关键差异

| 维度 | 当前 | 目标 |
|------|------|------|
| Agent 路径位置 | Streamlit 进程内 | FastAPI 后端进程 |
| 前端角色 | 运行引擎 + Playwright + 展示 | 仅 HTTP 请求 + 展示 |
| 后端 worker 数 | 1 | 2 (gunicorn) |
| 异步任务 | 无 | /analyze-real 使用提交+轮询模式 |
| 结果缓存 | 无 | 分析引擎进程内 LRU cache |
| Scraper 位置 | Streamlit 进程 | FastAPI 后端进程 |
| 任务状态 | 无 | 进程内 dict (轻量) |

### 为什么不直接引入 Celery/Redis

1. **部署复杂度**：Celery 需要 Redis/RabbitMQ broker，Render Free 档不支持 Redis addon。
2. **运维成本**：3 个服务（API + Worker + Broker）vs 当前 2 个服务。
3. **当前规模不需要**：目标是 10–50 并发用户，进程内 `ThreadPoolExecutor` + 任务 dict 已足够。
4. **渐进原则**：先用最轻量方案验证异步模式，确认有效后再考虑 Celery。

---

## 4. What Should Become Async

| 流程 | 当前耗时 | 异步理由 |
|------|---------|---------|
| **Agent 多平台抓取 + 分析** | 30–120s | 远超用户可接受的同步等待时间。Playwright 是 I/O-bound + CPU-bound 混合，单独占用大量进程资源。必须异步化为"提交任务 → 返回 task_id → 后台执行 → 前端轮询结果"。 |
| **大批量 `/analyze-batch` (> 20 项)** | > 10s | 20+ 项分析需 > 10s CPU 时间，长时间占满 worker。可改为：≤ 10 项同步返回，> 10 项异步化。 |

### 异步模式设计

```
POST /analyze-real
  Body: { sources, limit_per_source, query, ... }
  Response: { task_id: "abc-123", status: "queued" }

GET /task/{task_id}
  Response:
    { task_id, status: "running", progress: { sources_completed: 1, total: 2 } }
    or
    { task_id, status: "success", result: { ...envelope... } }
    or
    { task_id, status: "failed", error: "..." }
```

前端轮询间隔：首次 2s，之后 5s，最多轮询 180s / REAL_ANALYSIS_TIMEOUT。

---

## 5. What Should Stay Sync

| 流程 | 当前耗时 | 同步理由 |
|------|---------|---------|
| **`/analyze` 单条** | 0.3–1s | 用户体验要求即时反馈。引擎在 < 1s 内完成，异步化反而增加复杂度和延迟（轮询至少 2s）。 |
| **`/score-breakdown`** | 0.3–1s | 同上。 |
| **`/risk-check`** | 0.3–1s | 同上。 |
| **`/explain-only`** | 0.3–1s | 同上。 |
| **`/analyze-batch` (≤ 10 项)** | 2–5s | 在 gunicorn 2 workers 下，5s 的同步响应可接受。异步化收益不大。 |
| **`/health`、`/alerts`** | ~0ms | 纯状态查询，必须同步。 |

---

## 6. Decoupling Plan

### 6.1 Streamlit ↔ Scraper + Analysis 解耦

**当前耦合方式：**

```
app_web.py
  → import real_analysis_service
    → import analysis_bridge
      → import multi_source_pipeline
        → import rightmove_pipeline, zoopla_pipeline
          → import Playwright
```

所有模块在 Streamlit 进程中被 import 和执行。

**解耦方案：**

1. 在 FastAPI 后端新增 `POST /analyze-real` 端点，内部调用 `run_multi_source_analysis`。
2. Streamlit 前端的 `run_real_listings_analysis` 改为 HTTP 请求后端 `/analyze-real`，不再直接 import `analysis_bridge` 和 `multi_source_pipeline`。
3. Streamlit 的 `RENTALAI_USE_LOCAL=1` 仍然保留给单条 `/analyze`（轻量），但 Agent 路径强制走后端。

**边界切割点：**

```
real_analysis_service.py:
  之前: from data.pipeline.analysis_bridge import run_multi_source_analysis
  之后: requests.post(api_url + "/analyze-real", json=payload)
```

**影响范围：**
- 修改：`real_analysis_service.py`（1 个文件，改调用方式）
- 新增：`api_server.py` 中 1 个端点
- 不改：`analysis_bridge.py`、`multi_source_pipeline.py`、`*_pipeline.py`、`*_scraper.py`

### 6.2 API 同步请求 ↔ 长耗时任务解耦

**当前耦合方式：**

所有请求在 HTTP 请求生命周期内同步完成。`/analyze-real` 如果直接同步调用 `run_multi_source_analysis`，会占满 worker 30–120s。

**解耦方案：**

1. 新增轻量 `TaskStore` 类（进程内 dict），管理异步任务生命周期。
2. `POST /analyze-real` 立即返回 `task_id`，在后台线程中运行 `run_multi_source_analysis`。
3. `GET /task/{task_id}` 返回任务状态和结果。
4. 前端轮询 `/task/{task_id}` 直到完成或超时。

**不需要 Celery 的理由：** 当前目标是单机 2 workers，进程内 dict + `threading.Thread` 足够。任务结果在进程重启时丢失是可接受的（用户会看到"task not found"并重试）。

### 6.3 解耦优先级

| 优先级 | 解耦 | 原因 |
|--------|------|------|
| **1** | Streamlit ↔ Playwright/Analysis (Agent 路径) | 消除最致命的阻塞 — 1 个 Agent 用户阻塞所有用户 |
| **2** | 同步 API ↔ 长任务 | 防止 30–120s 的 Agent 请求占满 worker |
| **3** | Streamlit ↔ Local Engine (单条分析) | 当前 `USE_LOCAL=1` 让引擎跑在前端进程中，但对单条 < 1s 的请求影响小，优先级低 |

---

## 7. Minimal Task Model

用于 `/analyze-real` 异步任务的最小状态模型：

```python
@dataclass
class TaskRecord:
    task_id: str          # UUID，唯一标识
    status: str           # "queued" | "running" | "success" | "failed" | "timeout"
    created_at: str       # ISO 8601 UTC 时间戳
    updated_at: str       # 最后状态变更时间
    input_summary: dict   # 请求参数摘要：sources, limit_per_source 等
    result: dict | None   # 完成后的 analysis envelope
    error: str | None     # 失败时的错误信息
    degraded: bool        # 部分 source 失败但仍有结果
    elapsed_seconds: float | None  # 总耗时
```

### 字段用途

| 字段 | 用途 |
|------|------|
| `task_id` | 前端轮询的唯一标识，UUID4 格式 |
| `status` | 前端用于决定展示哪种 UI 状态（loading / results / error） |
| `created_at` | 用于 TTL 清理 — 超过 N 分钟的旧任务可被自动回收 |
| `updated_at` | 用于检测 stuck 任务 — 如果 `running` 状态超过 timeout 仍未更新，标记为 `timeout` |
| `input_summary` | 调试和日志 — 不存完整 payload，只存关键参数 |
| `result` | 任务成功后的完整结果 envelope，供前端渲染 |
| `error` | 失败时的结构化错误描述 |
| `degraded` | 从 `analysis_bridge` 的 `degraded` 标记传递，前端可显示"partial results"提示 |
| `elapsed_seconds` | 性能日志 + 前端可展示"分析耗时 X 秒" |

### TaskStore 设计

```python
class TaskStore:
    """进程内轻量任务存储，非持久化。"""
    _tasks: dict[str, TaskRecord]  # task_id → TaskRecord
    _lock: threading.Lock
    _max_age_seconds: int = 600    # 10 分钟后自动清理

    def create(self, input_summary: dict) -> str:
        """创建新任务，返回 task_id。"""

    def update_status(self, task_id: str, status: str, **kwargs) -> None:
        """更新任务状态。"""

    def get(self, task_id: str) -> TaskRecord | None:
        """查询任务，返回 None 表示不存在或已过期。"""

    def cleanup_expired(self) -> int:
        """清理过期任务，返回清理数量。"""
```

**注意：** 这是进程内 dict，gunicorn 多 worker 时各 worker 有独立的 TaskStore。这意味着创建任务的 worker 和查询任务的 worker 可能不同。解决方案：

- **方案 A（推荐起步）：** gunicorn 使用 `--preload`，并限制 `/analyze-real` 和 `/task/{task_id}` 始终在同一个 worker 上处理（通过 sticky session 或限制 worker 数为 1 仅处理 real-analysis）。
- **方案 B：** 任务结果写入临时文件（`/tmp/rentalai-tasks/{task_id}.json`），多 worker 共享文件系统读取。
- **方案 C（后续）：** 引入 Redis 做共享 TaskStore。

---

## 8. Cache / Reuse Opportunities

### 最值得先缓存的

| 缓存点 | 缓存键 | TTL | 预期命中率 | 实现方式 |
|--------|--------|-----|-----------|---------|
| **分析引擎结果** | `hash(sorted(input_dict.items()))` | 5 分钟 | 中（同一用户连续点击） | 进程内 `functools.lru_cache` 或自定义 dict + TTL |
| **Scraper 抓取结果** | `(source, search_url, limit)` | 10 分钟 | 高（同一区域多用户搜索） | 进程内 dict + TTL |
| **`_load_area_data()` JSON** | 已有（`_AREA_DATA_CACHE`） | 永久 | 100% | 已实现 |

### 最值得复用的

| 复用点 | 场景 | 实现 |
|--------|------|------|
| **相同区域 scraper 结果** | 10 分钟内多个用户搜索"London"，复用第一次抓取结果 | scraper 结果缓存 |
| **同一 batch 中重复房源** | batch 输入中相同 property 参数出现多次 | 输入去重 |

### 不适合缓存的

- `/health`、`/alerts` — 实时状态，不能缓存。
- `listings.json` 写入 — 写操作无法缓存。

---

## 9. Incremental Upgrade Order

### Phase A — Agent 后端化 + 异步任务模型（最高优先）

**改动范围：**
1. `api_server.py`：新增 `POST /analyze-real` 和 `GET /task/{task_id}` 端点。
2. 新增 `task_store.py`：进程内任务存储。
3. `real_analysis_service.py`：`run_real_listings_analysis` 改为向 `/analyze-real` 发 HTTP 请求 + 轮询 `/task/{task_id}`。
4. `render.yaml`：Streamlit 服务移除 `playwright install chromium`（不再需要在前端进程运行 Playwright）。后端服务添加 `playwright install chromium`。

**收益：** 消除 Streamlit 进程阻塞，Agent 路径不再影响其他用户。

**风险：** 后端现在需要运行 Playwright（增加内存消耗）。Render Free 档 512MB 可能不够同时运行 API + Chromium。可能需要升级到 Starter 档。

### Phase B — 后端多 Worker（紧接 Phase A）

**改动范围：**
1. `render.yaml` 后端启动命令改为 `gunicorn api_server:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`。
2. `requirements.txt`：确认 `gunicorn` 已在依赖列表。
3. `TaskStore` 适配多 worker：选择方案 A（`--preload`）或方案 B（文件共享）。

**收益：** 后端可并行处理 2 个请求，分析吞吐从 ~2–3 RPS 提升到 ~4–6 RPS。

**风险：** 内存翻倍（2 workers × ~100MB）。需评估 Render 档位是否支持。

### Phase C — 分析引擎 LRU 缓存（低风险快赢）

**改动范围：**
1. `api_analysis.py`：在 `call_analysis_engine` 入口增加基于输入 hash 的进程内 TTL 缓存。
2. 可选：scraper 结果缓存（基于 search URL + source + limit）。

**收益：** 相同输入不重复计算，降低 CPU 使用率。对连续点击"Analyze"的用户效果显著。

**风险：** 极低 — 缓存仅是 dict 查询，cache miss 退化到原始路径。TTL 5 分钟内数据一致性可接受。

### Phase D — Scraper 结果缓存 + 抓取节流（后续）

**改动范围：**
1. `multi_source_pipeline.py`：新增基于 `(source, url, limit)` 的结果缓存，TTL 10 分钟。
2. 可选：增加全局抓取 rate limiter（每 source 每分钟最多 N 次）。

**收益：** 避免重复抓取同一页面，减少反爬风险，降低 Chromium 启动次数。

**风险：** 需要处理缓存失效和内存上限。

---

## 10. Risks of the Upgrade

| 风险 | 严重度 | 缓解方式 |
|------|--------|---------|
| **后端 OOM** | 高 | Playwright 移到后端后，512MB 可能不够。缓解：限制并发抓取任务数（信号量），或升级 Render 档位。 |
| **Task 状态丢失** | 中 | 进程内 dict 在重启时清空。缓解：前端轮询到 "task not found" 时提示用户重试。不做持久化（MVP 可接受）。 |
| **多 worker TaskStore 不一致** | 中 | 任务创建和查询可能命中不同 worker。缓解：Phase A 先用单 worker，Phase B 用文件共享或 `--preload`。 |
| **Scraper 缓存数据过期** | 低 | 10 分钟 TTL 可能返回过期 listing。缓解：明确标注数据时间，用户可手动触发刷新。 |
| **前端轮询增加请求量** | 低 | 每个 Agent 任务产生 ~30 次 GET /task 轮询。缓解：5s 轮询间隔，单任务 ~30 次请求，轻量 dict 查询几乎不消耗资源。 |
| **API 接口增加** | 低 | 新增 2 个端点增加维护面。缓解：端点逻辑简单（提交/查询），复用现有 `run_multi_source_analysis`。 |

---

## 11. Recommended Next Implementation Step

### 下一步真正落地时，最应该先实施 Phase A：Agent 后端化

**具体改造清单：**

1. **`api_server.py`** — 新增 `POST /analyze-real`：接收 sources/limit/query 参数，创建任务，在后台线程启动 `run_multi_source_analysis`，立即返回 `{ task_id, status: "queued" }`。
2. **`api_server.py`** — 新增 `GET /task/{task_id}`：从 TaskStore 查询状态和结果。
3. **新增 `task_store.py`** — 进程内 `TaskStore` 类，管理任务生命周期。
4. **`real_analysis_service.py`** — 将 `run_real_listings_analysis` 改为：HTTP POST `/analyze-real` → 循环 GET `/task/{task_id}` → 返回结果。
5. **`render.yaml`** — 后端 buildCommand 增加 `playwright install chromium`；前端 buildCommand 移除 `playwright install chromium`。
6. **`.env.example`** — 增加 `RENTALAI_TASK_TTL`、`RENTALAI_MAX_CONCURRENT_TASKS` 说明。

**预计工作量：** ~200 行新代码 + ~50 行修改。不需要改分析引擎、不需要改 scraper 内部、不需要改前端 UI 渲染逻辑。

**验证方式：** 本地启动 FastAPI → `POST /analyze-real` → 轮询 `/task/{task_id}` → 确认结果与当前 `run_real_listings_analysis` 一致。

# P9 Phase3 Scalability Risk Map

基于当前 RentalAI MVP 的真实代码结构、部署配置和 Phase2 优化后状态，对系统在用户增长场景下的承载能力进行建模分析。

---

## 1. Current System Architecture Summary

### 服务拓扑

```
┌──────────────────────────────────────────────────────────────────────┐
│                     Render Free Tier (Oregon)                        │
│                                                                      │
│  ┌──────────────────────┐      ┌──────────────────────┐             │
│  │   rentalai-ui         │      │   rentalai-api        │             │
│  │   Streamlit (Python)  │──────│   FastAPI (uvicorn)   │             │
│  │   单进程 + 进程内引擎  │ HTTP │   单进程单线程池       │             │
│  │   + Playwright        │      │                      │             │
│  │   Port: $PORT         │      │   Port: $PORT        │             │
│  └──────────────────────┘      └──────────────────────┘             │
│         │                              │                             │
│         │ in-process                   │ in-process                  │
│         ▼                              ▼                             │
│  ┌──────────────────────────────────────────────────────┐           │
│  │  Analysis Engine (web_bridge → module2_scoring)       │           │
│  │  CPU-bound 纯 Python, ~0.3–1s/property                │           │
│  └──────────────────────────────────────────────────────┘           │
│         │                                                            │
│         ▼ (Agent 路径)                                               │
│  ┌──────────────────────────────────────────────────────┐           │
│  │  Scraper Pipeline (Playwright Chromium)                │           │
│  │  每次启动浏览器实例, 30–120s/请求                       │           │
│  └──────────────────────────────────────────────────────┘           │
│                                                                      │
│  数据持久化：listings.json (本地文件，无 DB)                          │
│  缓存层：无                                                          │
│  消息队列：无                                                        │
│  CDN/负载均衡：无                                                    │
└──────────────────────────────────────────────────────────────────────┘
```

### 部署方式

- **前端（rentalai-ui）**：Render Free Web Service，单实例，Streamlit 单进程。`RENTALAI_USE_LOCAL=1` 时分析引擎运行在前端进程内。Playwright 也运行在此进程中（Agent 路径）。
- **后端（rentalai-api）**：Render Free Web Service，单实例，uvicorn 单 worker。所有 `/analyze*` 请求由 FastAPI 的同步路由线程池处理。
- **Scraper**：内嵌于 rentalai-ui 进程（非独立 worker），每次 Agent 抓取启动新 Chromium 实例。
- **存储**：本地 JSON 文件（`listings.json`），无数据库，无共享存储。
- **缓存**：无任何层面缓存。
- **横向扩展**：当前 0 能力 — 无负载均衡、无共享状态、无多实例协调。

### 关键数字

| 指标 | 当前值 |
|------|--------|
| 前端进程数 | 1 |
| 后端 worker 数 | 1 (uvicorn 默认) |
| Render Free 档 RAM | 512 MB |
| Render Free 档 CPU | 共享 0.1 vCPU |
| 冷启动时间 | 30–60s |
| 空闲自动休眠 | 15 分钟无请求 |
| 分析引擎单次耗时 | 0.3–1.0s |
| 单次 Agent 抓取耗时 | 30–120s |
| HTTP request timeout | 120–180s |

---

## 2. Load Assumption

### 10 用户（当前基本可用）

| 维度 | 预期表现 |
|------|---------|
| 单条分析 | 正常，< 2s |
| Batch 分析 | 正常，10 项 ~2–3s (并行) |
| Agent 抓取 | 可用但慢（30–120s），同一时刻仅 1 用户能用 |
| 冷启动 | 每 15 分钟无人后首次访问等 30–60s |
| 内存 | 安全，Chromium ~200MB + Python ~150MB < 512MB |
| 稳定性 | 可接受，偶发 timeout 可恢复 |

**问题**：如果 2 个用户同时触发 Agent 抓取，Streamlit 单进程会串行处理，第二个用户等待第一个完成后才开始。

### 100 用户（系统开始严重退化）

| 维度 | 预期表现 |
|------|---------|
| 单条分析 | **退化** — 100 个并发 `/analyze` 请求时，单 worker uvicorn 的线程池（默认 40 线程）接近饱和。CPU-bound 引擎在 GIL 下实际吞吐 ~2–3 RPS |
| Batch 分析 | **危险** — 单个 `/analyze-batch` 20 项就占 ~4s CPU，10 个并发 batch = 全部 CPU 被 GIL 锁定 |
| Agent 抓取 | **不可用** — 100 人中任何 1 人触发 Agent 就阻塞 Streamlit 进程 30–120s，其余 99 人看到白屏/超时 |
| 冷启动 | 频率降低（持续有请求），但首次大量用户涌入仍需等 |
| 内存 | **OOM 风险** — 多个 ThreadPoolExecutor 同时活跃 + Streamlit session state 累积，512MB 易超 |
| 存储 | **文件竞争** — 多线程并发写 `listings.json`，无锁保护，数据可能损坏 |

**最先崩的是**：Streamlit 进程 — Agent 路径阻塞 + 内存不足 + 用户 session state 累积。

### 1000 用户（系统完全不可用）

| 维度 | 预期表现 |
|------|---------|
| 前端 | **完全不可用** — Streamlit 单进程无法处理 1000 并发 WebSocket 连接 |
| 后端 | **完全拒绝服务** — uvicorn 单 worker 排队，请求超时链式崩溃 |
| Scraper | **不可讨论** — Chromium 实例需 200MB+，10 个并发就需 2GB |
| 存储 | **必崩** — 1000 用户并发读写同一个 JSON 文件 |
| Render | **平台限制** — Free 档限带宽/连接数，平台层拒绝连接 |

---

## 3. Frontend Scalability Risks

| 风险 | 严重度 | 说明 |
|------|--------|------|
| **Streamlit 单进程模型** | 极高 | Streamlit 每个用户连接是同一个 Python 进程内的一个 coroutine/thread。CPU-bound 任务（本地引擎、Playwright）直接阻塞所有用户。无法通过增加 Streamlit 实例横向扩展（`session_state` 不共享）。 |
| **Agent 路径同步阻塞** | 极高 | `run_real_listings_analysis` 在 Streamlit 进程内同步运行 Playwright + 分析引擎 30–120s。期间整个进程被阻塞（`st.spinner`），其他用户的请求排队等待。 |
| **进程内分析引擎** | 高 | `RENTALAI_USE_LOCAL=1` 时分析引擎在 Streamlit 进程内运行。10 个并发用户 = 引擎串行排队。 |
| **Session state 内存累积** | 中 | `st.session_state` 存储分析结果（`p2_batch_last` 含完整 envelope），长期在线用户会累积大量内存。无自动清理机制。 |
| **无静态资源 CDN** | 低 | Streamlit 的 JS bundle 和 CSS 由同一进程服务。高并发时静态资源和动态请求竞争同一端口。 |

### 扩展瓶颈核心

Streamlit 不是为多用户并发设计的。它的架构假设是"少量用户的交互式数据应用"，不是"生产级 Web 服务"。

---

## 4. Backend Scalability Risks

| 风险 | 严重度 | 说明 |
|------|--------|------|
| **单 worker uvicorn** | 极高 | `render.yaml` 中启动命令为 `uvicorn api_server:app --host 0.0.0.0 --port $PORT`，默认 1 个 worker。所有请求共享一个 Python 进程。 |
| **CPU-bound 分析引擎 + GIL** | 高 | `call_analysis_engine` 是纯 Python CPU 密集计算。`ThreadPoolExecutor` 并行受 GIL 限制，实际吞吐约 2–3 RPS（单 worker）。 |
| **`/analyze-batch` 独占资源** | 高 | 单个 batch 请求（20 项 × 4 workers）占满 CPU 数秒。期间其他请求排队。 |
| **`_api_failures` 全局状态** | 低 | `FailureTracker` 是进程内 dict。多 worker 时失效（不共享状态）。当前单 worker 不受影响，但横向扩展时需替换。 |
| **无请求队列** | 中 | 所有请求同步处理，无 Celery/RQ 等异步任务队列。长耗时请求（batch 20 项 ~4s）阻塞 worker 线程。 |

### 扩展路径

增加 uvicorn worker 数量（`--workers N`）是最直接的扩展手段，但受限于 Render Free 档 512MB RAM（每个 worker ~100MB）和 GIL（CPU-bound 任务需 ProcessPoolExecutor 或 multiprocessing）。

---

## 5. Analysis / Agent Bottlenecks

| 风险 | 严重度 | 说明 |
|------|--------|------|
| **分析引擎 CPU-bound** | 高 | `web_bridge.run_web_demo_analysis` → `module2_scoring.rank_houses_m2` 是纯 Python 字典操作 + 条件判断，~0.3–1s/property。无法通过 I/O 并行加速，只能通过多进程或编译加速（Cython/Rust）。 |
| **Agent 全链路同步** | 极高 | Agent 路径 = Playwright 抓取 (30–90s) + 数据标准化 (~0.1s) + 批量分析 (N × 0.5s)。整条链路在一个同步调用中完成，总耗时 30–120s。 |
| **无结果缓存** | 高 | 相同输入每次都重新运行引擎。同一用户连续点击"Analyze"按钮 = 重复计算。无 LRU cache 或 Redis 缓存。 |
| **`_AREA_DATA_CACHE` 只读安全** | 安全 | `module2_scoring._load_area_data()` 使用模块级全局变量做只读缓存，线程安全（首次加载后不再写入）。 |
| **无异步任务模型** | 高 | 无"提交任务 → 轮询结果"模式。所有分析在 HTTP 请求生命周期内同步完成。超时 = 结果丢失。 |

### 扩展瓶颈核心

Agent 路径是单个请求占用最多资源的流程（CPU + 内存 + 时间），且无法拆分为异步任务。

---

## 6. Scraper Bottlenecks

| 风险 | 严重度 | 说明 |
|------|--------|------|
| **Playwright Chromium 进程内运行** | 极高 | 每次 Agent 抓取启动一个 Chromium 实例（~200MB RAM），在 Streamlit 进程中运行。512MB 总内存下，1 个 Chromium + Python 已接近极限，2 个并发必然 OOM。 |
| **无浏览器实例复用** | 高 | 每次请求都 `browser_page_for_scraper_config(config)` 创建新实例。3–10s 的启动开销无法避免。 |
| **反爬风险** | 高 | Rightmove/Zoopla 有反爬机制。高频请求会触发验证码/IP 封禁。当前无 proxy rotation、无 rate limiting、无请求间隔控制。 |
| **每个用户请求都触发抓取** | 高 | Agent 路径没有"最近 N 分钟内已抓取则复用"逻辑。10 个用户搜索同一区域 = 10 次 Playwright 抓取相同页面。 |
| **无独立 worker** | 高 | Scraper 不是独立服务，内嵌在 Streamlit 进程中。无法独立扩展、独立监控、独立重启。 |

### 扩展瓶颈核心

Scraper 是内存消耗最大、耗时最长、最容易被外部（反爬）阻断的单一组件，且与前端进程耦合。这是整个系统最脆弱的点。

---

## 7. Data / Computation Risks

| 风险 | 严重度 | 说明 |
|------|--------|------|
| **listings.json 文件存储** | 高 | 所有 listing 持久化到单个 JSON 文件。并发写无锁保护。Render Free 档磁盘不持久化（重部署丢失）。文件增长无上限。 |
| **无缓存层** | 高 | 分析引擎、scraper 结果、标准化数据均无缓存。相同输入重复计算。 |
| **全量文件读写** | 中 | `_read_json_file` 每次读取整个 `listings.json`，`_write_json_file` 每次覆写。文件增长到 10MB+ 时单次读写成为瓶颈。 |
| **无 TTL / 过期机制** | 中 | 抓取的 listing 数据永不过期。用户可能看到过时房源信息。 |
| **无去重聚合优化** | 低 | `dedupe_normalized_listings` 是 O(n) 遍历，对当前规模（单次 ≤ 50 listing）影响可忽略。但若全量历史数据参与去重，会成为瓶颈。 |

---

## 8. Top 5 Critical Bottlenecks

按"最先会炸"排序：

| 排名 | 瓶颈 | 影响范围 | 触发条件 | 预计承载极限 |
|------|------|---------|---------|-------------|
| **1** | **Streamlit 单进程 + Agent 阻塞** | 全前端 | 任意 1 个用户触发 Agent 抓取 | ~1 个并发 Agent 用户 |
| **2** | **Chromium 内存压力** | 前端进程 | Agent 抓取触发 Playwright | 1 个并发 Chromium 实例 (512MB 档) |
| **3** | **uvicorn 单 worker** | 全后端 API | 并发 `/analyze` 或 `/analyze-batch` | ~3–5 RPS (CPU-bound GIL 限制) |
| **4** | **无结果缓存** | 全链路 | 重复相同输入的分析请求 | 每次都重算，线性增长 |
| **5** | **listings.json 文件并发** | 数据层 | 多线程同时写入持久化 | 数据损坏风险 |

---

## 9. What Will Break First

### 最先崩的：Streamlit 前端进程

**原因：**

1. Streamlit 是单进程模型，所有用户共享同一个 Python 进程。
2. Agent 路径在进程内同步运行 Playwright（~200MB 内存 + 30–120s 阻塞），期间所有其他用户的请求排队。
3. Render Free 档仅 512MB RAM，Python 进程本身 ~150MB + Chromium ~200MB = 已用 ~350MB，几乎无余量。
4. 第 2 个并发 Agent 请求 = OOM kill 或极端串行等待（> 4 分钟）。

**崩溃表现：**
- 用户 A 触发 Agent 抓取 → 用户 B/C/D 看到页面无响应（Streamlit WebSocket 不回复）。
- 如果 Streamlit 进程被 OOM kill，Render 会重启服务（冷启动 30–60s），所有用户断线。
- 从用户视角：页面白屏、分析超时、刷新后重新等待冷启动。

### 第二个崩的：FastAPI 后端

即使前端问题解决（将分析改为 HTTP 调用后端），uvicorn 单 worker 在 10+ 并发分析请求下也会因 GIL 导致响应时间线性增长。

---

## 10. What Can Wait vs What Cannot

### 进入下一阶段前必须处理

| 问题 | 原因 |
|------|------|
| **Agent 路径与前端解耦** | 单个 Agent 请求阻塞整个 Streamlit 进程，这是生产环境不可接受的。至少需要将 Playwright 抓取改为后端异步任务或独立 worker。 |
| **uvicorn 多 worker** | 启动命令改为 `--workers 2`（或使用 gunicorn + uvicorn worker class），至少让后端能处理 2–3 个并发分析请求。Render Free 档 512MB 可支持 2 个轻量 worker。 |

### 可以以后再解决

| 问题 | 原因 |
|------|------|
| listings.json → DB | 当前数据量极小（< 1000 条），文件存储尚可。用户增长到 100+ 时再迁移 SQLite/PostgreSQL。 |
| 结果缓存 (Redis/内存 LRU) | 当前重复请求频率低。先解决并发阻塞问题，再考虑缓存。 |
| Playwright 浏览器复用 | 需要进程级 context 管理，复杂度高。先通过 Scraper 独立 worker 解耦，再在 worker 内部做复用。 |
| ProcessPoolExecutor 替代 ThreadPoolExecutor | GIL 限制在当前并发量下影响有限。先增加 uvicorn worker 数量，再考虑多进程方案。 |
| CDN / 静态资源分离 | Streamlit 框架限制，无法拆分。除非迁移到 React/Vue + API 架构。 |
| 请求队列 (Celery/RQ) | 架构变更大。先解决最紧急的解耦问题，再引入异步任务模型。 |

---

## 11. Next Step

### 推荐进入：P9 Phase3 Step2 — 最小架构加固

**重点：**

1. **Agent 路径后端化** — 将 `run_real_listings_analysis` 从 Streamlit 进程内调用改为 HTTP 请求后端 API（新增 `/analyze-real` 端点），让 Playwright 和分析引擎运行在 FastAPI 进程中。这样前端只做 HTTP 请求 + 轮询/等待，不再阻塞。
2. **uvicorn 多 worker** — 启动命令改为 `gunicorn api_server:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`，后端可并行处理 2 个请求。
3. **轻量 LRU 缓存** — 对分析引擎相同输入的结果做进程内 `functools.lru_cache` 或自定义 TTL cache，避免重复计算。

这三项改动风险可控、收益明确，可以在不重构架构的前提下将系统承载能力从 ~1–3 并发用户提升到 ~10–20 并发用户。

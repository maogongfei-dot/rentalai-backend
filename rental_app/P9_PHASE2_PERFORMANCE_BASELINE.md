# P9 Phase2 Performance Baseline

RentalAI MVP 首轮性能慢点排查与基线记录。基于代码静态分析（调用链、阻塞点、超时配置）得出，结合新增的 `[PERF]` 日志提供运行时数据采集能力。

---

## 1. Current Performance Scope

### 纳入观察

| 服务 | 关键路径 |
|------|---------|
| **rentalai-api**（FastAPI） | `/analyze`、`/score-breakdown`、`/risk-check`、`/explain-only`、`/analyze-batch` |
| **rentalai-ui**（Streamlit） | 表单分析（local engine / HTTP）、Agent 真实抓取 + 分析 |
| **Analysis engine** | `web_bridge.run_web_demo_analysis` → `scoring_adapter.generate_ranking_api_response` |
| **Scraper pipeline** | `run_multi_source_pipeline` → Rightmove/Zoopla Playwright 抓取 |

### 不纳入本轮优化

- Playwright 浏览器安装/build 时间（属部署层）
- Streamlit 框架自身渲染性能（无法控制）
- 冷启动时间（Render 免费档固有特性）

---

## 2. Frontend Performance Findings

### 架构特点

Streamlit 是 Python 服务端渲染框架。每次用户交互触发 **整个脚本的完整重执行**（top-to-bottom rerun），不存在传统 SPA 的首屏/懒加载概念。

### 发现

| 风险点 | 严重度 | 说明 |
|--------|--------|------|
| **脚本顶层 import 链** | 中 | `app_web.py` 在顶层导入 `web_ui.*`、`api_analysis`、`alert_utils` 等模块。首次加载时 Python 解释器需 parse 全部依赖。在 Render 免费档（512MB RAM、冷启动）上可感知。 |
| **Streamlit 全量 rerun** | 低 | 每次点击按钮触发 `app_web.py` 重执行。但多数 import 已被 Python 缓存，实际开销在毫秒级。 |
| **无重复 API 请求** | — | 前端不存在 useEffect 式自动轮询。API 请求仅在用户主动点击 Analyze / Batch 按钮时触发。 |
| **Agent 真实抓取阻塞 UI** | 高 | `run_real_listings_analysis` 在 Streamlit 进程内同步执行 Playwright 抓取 + 分析引擎。期间 UI 被 `st.spinner` 阻塞，用户无法交互。一次抓取可能 30-120 秒。 |

### 最值得优先盯的点

**Agent 真实抓取同步阻塞**：这是前端体验最大的性能瓶颈。

---

## 3. Backend Performance Findings

### 请求处理架构

```
POST /analyze
  → modular_analyze_response(body, endpoint)
    → run_standard_pipeline(body, endpoint)
      → normalize_api_input(body)          ← ~0ms（纯 Python dict 操作）
      → normalize_web_form_inputs(coerced) ← ~0ms
      → call_analysis_engine(input_data)   ← ★ 核心耗时
        → web_bridge.run_web_demo_analysis
          → scoring_adapter.generate_ranking_api_response(state)
            → rank_houses_m2(state)         ← Module2 评分
            → build_compare_explain(state)  ← 解释生成
            → build_decision_hints(state)   ← 决策提示
    → extract_*_payload(engine_out)        ← ~0ms（dict 切片）
```

### 发现

| 风险点 | 严重度 | 说明 |
|--------|--------|------|
| **分析引擎是同步 CPU 密集** | 中 | `run_web_demo_analysis` 在调用线程中完成全部计算。FastAPI 的 `def` 路由跑在线程池中，不会阻塞 event loop，但单请求耗时直接决定响应延迟。 |
| **stdout 抑制开销** | 低 | `web_bridge.py` L122-127 将 `sys.stdout` 重定向到 `io.StringIO()` 以避免 emoji 编码错误。少量 GC/IO 开销，但不是瓶颈。 |
| **`/analyze-batch` 串行循环** | 高 | `analyze_batch_request_body` 中 `for i, item in enumerate(props)` **逐项串行调用** `call_analysis_engine`。10 个房源 = 10× 单次引擎时间。无并行、无缓存。 |
| **`/risk-check` 调用 contract_risk** | 低 | `extract_risk_payload` 额外调用 `calculate_structured_risk_score`。纯 Python 规则匹配，~1ms 量级。 |
| **无外部网络依赖** | — | 分析引擎是纯本地计算，不依赖数据库或第三方 API。超时风险来自 CPU 而非网络。 |

### 最值得优先盯的点

**`/analyze-batch` 串行循环**：N 个房源的总耗时 ≈ N × 单次引擎耗时。当 N=20 且单次 ~0.5s 时，总耗时 ~10s；加上 Render 免费档 CPU 限制，可能超过默认 timeout。

---

## 4. Scraper / Analysis Performance Findings

### Scraper 慢点

| 风险点 | 严重度 | 预计耗时 | 说明 |
|--------|--------|---------|------|
| **Playwright 浏览器启动** | 高 | 3-10s | 每次调用 `run_rightmove_pipeline` / `run_zoopla_pipeline` 都启动 Chromium 实例。在容器化环境中尤其慢。 |
| **页面加载 + 渲染等待** | 高 | 5-30s/页 | 等待 JavaScript 渲染完成、列表元素出现。Rightmove/Zoopla 页面较重。 |
| **串行多平台** | 高 | 累加 | `run_multi_source_pipeline` 逐个平台串行调用。2 个平台 = 2× 单平台时间。 |
| **反爬延迟** | 中 | 不确定 | 目标网站可能返回验证码/空结果，导致重试或超时。 |

### Analysis Bridge 慢点

| 风险点 | 严重度 | 说明 |
|--------|--------|------|
| **Listing → batch payload 映射** | 低 | `listings_dicts_to_batch_properties` 是纯 Python dict 操作，~0ms。 |
| **批量分析** | 高 | 映射后调用 `analyze_batch_request_body`，同样走串行引擎循环。 |

### 结论

**Scraper 是整条链路中耗时最大的单一环节**，预计 30-120 秒。但它只在 Agent 真实抓取路径触发，不影响手动输入分析。

---

## 5. Timeout / Failure Risk Map

```
                   ┌─────────────────────────────────────────────┐
                   │         Streamlit UI (app_web.py)           │
                   │                                             │
                   │  ┌──────────┐    ┌───────────────────────┐  │
                   │  │ Analyze  │    │  Agent Real Analysis  │  │
                   │  │ (1-3s)   │    │  (30-120s)            │  │
                   │  └─────┬────┘    └──────────┬────────────┘  │
                   │        │                    │               │
                   └────────┼────────────────────┼───────────────┘
                            │                    │
              HTTP 120s     │                    │ in-process
              timeout       │                    │
                            ▼                    ▼
                   ┌─────────────────┐  ┌────────────────────┐
                   │  FastAPI API    │  │  Scraper Pipeline   │
                   │  /analyze ~1s   │  │  Playwright 30-90s  │
                   │  /batch ~N×1s   │  │  per source         │
                   └────────┬────────┘  └────────┬───────────┘
                            │                    │
                            ▼                    ▼
                   ┌─────────────────────────────────────────┐
                   │  Analysis Engine (web_bridge)           │
                   │  ~0.3-1.0s per property (CPU-bound)     │
                   └─────────────────────────────────────────┘
```

### 超时风险排序

| 排名 | 环节 | 触发条件 | 预计耗时 | timeout 保护 |
|------|------|---------|---------|-------------|
| 1 | **Agent 真实抓取** | 用户点 "Continue to Analysis" | 30-120s | 无硬超时 |
| 2 | **`/analyze-batch` 大批量** | 前端 batch JSON 提交 ≥ 10 项 | N × 0.5-1s | `requests.post(timeout=180)` |
| 3 | **Render 冷启动** | 服务 15 分钟无请求后首次访问 | 30-60s | 平台层 |
| 4 | **单条 `/analyze`** | 正常请求 | 0.3-1s | `requests.post(timeout=120)` |

---

## 6. Baseline Metrics to Track

已通过 `[PERF]` 日志埋点采集以下指标，全部输出到 stdout → Render Logs。

| 指标 | 日志格式 | 采集位置 |
|------|---------|---------|
| **API 请求端到端耗时** | `[PERF] POST /analyze -> 200 in 0.523s` | `api_server.py` HTTP 中间件 |
| **分析引擎单次耗时** | `[PERF] engine /analyze took 0.481s` | `api_analysis.py` `run_standard_pipeline` |
| **批量引擎总耗时** | `[PERF] batch engine: 5 items in 2.415s (0.483s/item)` | `api_analysis.py` `analyze_batch_request_body` |
| **前端 local engine 耗时** | `[PERF] local engine /analyze took 0.512s` | `app_web.py` `run_analysis_for_ui` |
| **前端 HTTP 请求耗时** | `[PERF] HTTP /analyze -> 200 in 0.823s` | `app_web.py` `run_analysis_for_ui` |
| **Agent 真实抓取总耗时** | `seconds: 45.2` | `real_analysis_service.py` `run_real_listings_analysis`（已有） |

### 查看方式

Render Dashboard → 对应服务 → Logs → 搜索 `[PERF]`。

---

## 7. Top 5 Optimization Priorities

| 优先级 | 慢点 | 当前预估耗时 | 优化方向 | 收益 |
|--------|------|------------|---------|------|
| **1** | `/analyze-batch` 串行循环 | N × 0.5-1s | 引入 `concurrent.futures.ThreadPoolExecutor` 并行化 | 5-20 项批量从 5-20s → 2-4s |
| **2** | Agent 多平台串行抓取 | 平台数 × 30-60s | 并行化 `run_multi_source_pipeline` 中的平台调用 | 2 平台从 60-120s → 30-60s |
| **3** | Playwright 启动开销 | 3-10s/次 | 复用浏览器实例（persistent context 或 connection reuse） | 第 2+ 次抓取省 3-10s |
| **4** | Render 冷启动 | 30-60s | 配置 health check ping 或升级到付费档 | 消除首次访问等待 |
| **5** | 前端导入链 | ~1-3s（首次） | 延迟加载非必需模块（`importlib.import_module`） | 首页加载快 1-2s |

---

## 8. Low-Risk Quick Wins

以下改进风险极低、不需要重构，可在后续步骤中快速实施：

| 改进 | 工作量 | 说明 |
|------|--------|------|
| **batch 并行化** | ~20 行 | 在 `analyze_batch_request_body` 中用 `ThreadPoolExecutor` 替换 `for` 循环 |
| **多平台抓取并行化** | ~15 行 | 在 `run_multi_source_pipeline` 中用 `ThreadPoolExecutor` 并行调度各平台 |
| **batch 请求加 item 上限** | ~5 行 | 在 `/analyze-batch` 入口限制 `len(props) <= 50`，防止极端输入拖垮服务 |
| **`[PERF]` 慢请求 warning** | ~5 行 | 在 HTTP 中间件中，耗时 > 5s 的请求升级为 `logger.warning` |

---

## 9. Next Step

1. **收集运行时数据**：部署后观察 1-3 天 Render Logs 中的 `[PERF]` 数据，确认实际引擎耗时和 batch 请求分布。
2. **进入 P9 Phase2 Step2 — 批量分析并行化**：将 `/analyze-batch` 和多平台抓取的串行循环改为线程池并行，这是投入产出比最高的优化。
3. **考虑慢请求告警**：在 HTTP 中间件中对耗时 > 5s 的请求触发 `send_alert(level="P2")`。

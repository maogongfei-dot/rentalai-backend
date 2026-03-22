# P9 Phase2 Quick Optimization Round 1

基于 `P9_PHASE2_PERFORMANCE_BASELINE.md` 中识别的 Top 5 优化优先级，执行第一轮低风险性能优化。

---

## 1. Optimization Scope

### 已优化

| 模块 | 文件 | 优化类型 |
|------|------|---------|
| `/analyze-batch` 引擎循环 | `api_analysis.py` | 串行 → 线程池并行 |
| 多平台 scraper 调度 | `multi_source_pipeline.py` | 串行 → 线程池并行 |
| API 请求监控 | `api_server.py` | 慢请求 warning + P2 alert |
| Analysis bridge | `analysis_bridge.py` | 入口校验 + 分段耗时日志 |

### 暂未动

| 模块 | 原因 |
|------|------|
| 分析引擎内部（`scoring_adapter` / `module2_scoring`） | 属于核心业务逻辑，不在本轮范围 |
| Streamlit UI 渲染 | 框架层面无法优化 |
| Playwright 浏览器复用 | 需要架构变更，超出低风险范围 |
| Render 冷启动 | 平台层面，非代码层可解决 |

---

## 2. Frontend Changes

### Streamlit 说明

RentalAI 前端是 Streamlit（Python 服务端），不存在 React/Vue 式的 `useEffect` 或重复渲染问题。API 请求仅在用户主动点击时触发，不存在自动轮询。

### 间接收益

- 前端通过 HTTP 调用 `/analyze-batch` 时，后端并行化直接缩短等待时间。
- 前端 `run_analysis_for_ui` 中的 `[PERF]` 日志（Step1 已加）可观察改善效果。

---

## 3. Backend Changes

### 3.1 `/analyze-batch` 并行化

**改动**：`api_analysis.py` — 将逐项串行 `for i, item in enumerate(props)` 替换为 `ThreadPoolExecutor` 并行执行。

**机制**：
- `_BATCH_WORKERS` 默认 4（可通过 `RENTALAI_BATCH_WORKERS` 环境变量调整）
- 单项或仅 1 个 worker 时退化为串行，避免线程池开销
- 结果按原始 index 排序，保持输出顺序不变

**预期收益**：10 项房源批量分析从 ~5-10s → ~2-3s（受 CPU 核数和 GIL 影响，实际加速比约 2-3x）。

### 3.2 批量请求项数上限

**改动**：`api_analysis.py` — 新增 `_BATCH_MAX_ITEMS = 50` 检查（可通过 `RENTALAI_BATCH_MAX` 环境变量调整）。超限返回 `validation_error`。

**预期收益**：防止极端输入（如 1000 项）拖垮服务。

### 3.3 慢请求告警

**改动**：`api_server.py` — HTTP 中间件对耗时 ≥ 5 秒的请求升级为 `logger.warning` 并触发 P2 级 `send_alert`。

**预期收益**：主动识别性能退化，不依赖人工巡检日志。

---

## 4. Scraper / Analysis Changes

### 4.1 多平台并行抓取

**改动**：`multi_source_pipeline.py` — 将串行 `for raw_src in want` 循环替换为 `ThreadPoolExecutor` 并行调度各平台 pipeline。

**机制**：
- 2+ 个 source 时并行，单 source 不启线程池
- 每个 source pipeline 独立运行，异常隔离
- 新增 `[PERF] pipeline <source> took Xs` 日志

**预期收益**：2 平台抓取从 ~60-120s（串行累加）→ ~30-60s（取较慢的一个），Agent 路径提速约 50%。

### 4.2 Analysis bridge 增强

**改动**：`analysis_bridge.py`

- **入口校验**：`limit_per_source <= 0` 时立即返回失败，不进入重型 pipeline
- **分段耗时日志**：scraper pipeline、batch analysis、总耗时各自独立记录

**预期收益**：防止无效参数浪费 30+ 秒的 Playwright 启动；线上日志可精确定位哪个阶段最慢。

---

## 5. Risk Control Notes

### 为什么这些修改是低风险

| 修改 | 风险评估 |
|------|---------|
| batch 并行化 | `analyze_property_item_for_batch` 本身是无状态函数（纯输入→输出），线程安全。`enrich_batch_result_row` / `batch_result_row` 同理。结果按 index 排序，输出顺序不变。 |
| 多平台并行 | 各平台 pipeline 独立（不共享 Playwright 实例、不共享文件句柄），异常隔离。 |
| 批量上限 | 仅增加一个前置 `len(props) > 50` 检查，不影响正常请求。 |
| 慢请求告警 | 只在日志/alert 层面新增，不改变业务返回。 |
| 入口校验 | 只拦截明显无效参数，正常调用不受影响。 |

### 故意没动的部分

| 部分 | 原因 |
|------|------|
| `web_bridge.run_web_demo_analysis` 内部 | 核心评分逻辑，任何改动可能影响分析结果 |
| `sys.stdout` 重定向 | 已知开销极小，且解决了 Windows emoji 编码问题 |
| Playwright 浏览器实例管理 | 需要进程级/全局级 context 管理，超出低风险范围 |
| API 返回结构 | 严格不变，前端不需要适配 |

---

## 6. Before / After Clues

### 观察方式

| 指标 | 日志搜索 | 优化前预期 | 优化后预期 |
|------|---------|-----------|-----------|
| batch 总耗时 | `[PERF] batch engine:` | `10 items in 5.0s (0.5s/item, workers=1)` | `10 items in 1.8s (0.18s/item, workers=4)` |
| 多平台抓取总耗时 | `[PERF] scraper pipeline took` | 两个 `[PERF] pipeline X took` 之和 | ≈ 两个中较慢的一个 |
| 单平台耗时 | `[PERF] pipeline rightmove took` | 30-60s | 不变（单平台内未优化） |
| 慢请求发现 | `[PERF][SLOW]` | 不存在 | ≥ 5s 的请求被标记 |
| 总端到端耗时 | `[PERF] run_multi_source_analysis total` | scraper + analysis 串行累加 | scraper 并行 + analysis 并行 |

### 对比方法

在 Render Logs 中搜索 `[PERF]`，对比部署前后相同操作的耗时数值。

---

## 7. Remaining Performance Issues

| 问题 | 严重度 | 说明 |
|------|--------|------|
| **分析引擎 Python GIL** | 中 | `ThreadPoolExecutor` 对 CPU-bound 代码加速有限（GIL 约束）。若引擎耗时 > 0.5s/项，并行效果有限 |
| **Playwright 启动开销** | 高 | 每次抓取仍需 3-10s 启动 Chromium，无复用 |
| **Render 免费档冷启动** | 中 | 15 分钟无请求后首次访问仍需 30-60s |
| **Agent 同步阻塞 UI** | 中 | Streamlit 进程内运行抓取+分析，UI 被 spinner 阻塞 |
| **无请求级指标聚合** | 低 | `[PERF]` 日志仅为文本，无法自动统计 P95/P99 |

---

## 8. Next Optimization Priorities

| 优先级 | 方向 | 预期收益 | 复杂度 |
|--------|------|---------|--------|
| **1** | 评估 `ProcessPoolExecutor` 替代 `ThreadPoolExecutor` 绕过 GIL | batch 真并行，理论接近线性加速 | 中（需确认引擎可 pickle） |
| **2** | Playwright 浏览器连接复用 | 第 2+ 次抓取省 3-10s | 中（需全局 context 管理） |
| **3** | 请求指标聚合（P95/avg/error rate） | 数据驱动决策 | 低（内存计数器 + `/metrics` 端点） |

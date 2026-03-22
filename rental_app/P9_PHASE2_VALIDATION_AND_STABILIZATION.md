# P9 Phase2 Validation and Stabilization

Phase2 全链路复测报告。逐文件审查了 Step1（性能基线）、Step2（第一轮优化）、Step3（超时与降级保护）中的所有代码变更，确认改善效果、排查回归风险。

---

## 1. Validation Scope

### 纳入本轮复测

| 模块 | 文件 | 检查重点 |
|------|------|---------|
| **API 中间件** | `api_server.py` | 慢请求检测、全局异常处理、FailureTracker |
| **批量分析** | `api_analysis.py` | ThreadPoolExecutor 并行、50 项上限、结果排序 |
| **多平台 pipeline** | `multi_source_pipeline.py` | 并行调度、per-source timeout、outer timeout 处理 |
| **分析桥** | `analysis_bridge.py` | 入口校验、分段耗时日志、degraded 标记 |
| **前端真实分析** | `real_analysis_service.py` | 整体硬超时、timeout 合成信封 |
| **前端 UI** | `app_web.py` | 本地引擎慢请求警告、结构化错误、HTTP timeout |
| **报警** | `alert_utils.py` | send_alert、FailureTracker 线程安全 |

### 未纳入本轮复测

- 分析引擎内部（`scoring_adapter`、`module2_scoring`）— 未修改，不在 Phase2 范围。
- Playwright scraper 内部逻辑 — 未修改。
- Streamlit 框架层面性能 — 不可控。

---

## 2. Frontend Validation Result

### 当前状态：稳定

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 重复 API 请求 | **无** | Streamlit 仅在按钮点击时触发请求，无 useEffect/轮询 |
| HTTP timeout 保护 | **通过** | 单条 120s、batch 180s，均在 `requests.post(timeout=...)` 中设置 |
| 本地引擎慢请求检测 | **通过** | > 10s 时记录 `[PERF][SLOW]` 警告 |
| 本地引擎错误格式 | **通过** | 改为 `"Analysis engine error: ..."` 结构化消息 |
| Agent 真实分析超时 | **通过** | `_REAL_ANALYSIS_TIMEOUT=180s` 硬上限，超时返回合成信封 |
| 超时后 UI 响应 | **通过** | 返回 `_synthetic_failure_envelope`，Streamlit 可正常显示 |

### 已确认改善点

1. Agent 真实抓取路径不再有无限挂死风险（180s 硬超时）。
2. 本地引擎异常返回结构化错误消息，而非裸 `str(e)`。
3. 所有关键 API 调用都有 `[PERF]` 耗时日志。

### 仍存在的问题

- Agent 同步分析期间 UI 被 `st.spinner` 阻塞，用户无法取消（Streamlit 框架限制）。

### 回归风险：无

前端逻辑仅在 error handling 和日志层面有改动，业务返回结构不变。

---

## 3. Backend Validation Result

### 当前状态：稳定

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 全局异常处理 | **通过** | 所有 500 错误返回 `{"error": "internal_error", "message": "..."}` + P1 alert |
| 慢请求检测 | **通过** | ≥ 5s 触发 `[PERF][SLOW]` warning + P2 alert |
| FailureTracker 线程安全 | **通过** | 使用 `threading.Lock` 保护 `_counts` dict |
| batch 并行化正确性 | **通过** | `_process_one` 是无状态纯函数，线程安全；结果按 index 排序 |
| batch 上限 | **通过** | > 50 项返回 `validation_error` |
| batch 单项异常隔离 | **通过** | `analyze_property_item_for_batch` 内部 `try/except` 不会向 `fut.result()` 泄漏异常 |
| /health 增强 | **通过** | 返回 timestamp + api_version |
| /alerts 端点 | **通过** | 暴露当前连续失败计数 |

### 已确认改善点

1. `/analyze-batch` 从串行变为线程池并行，10 项预计从 ~5-10s 降至 ~2-3s。
2. 慢请求主动告警，无需人工巡检日志。
3. 极端输入（> 50 项 batch）被快速拒绝。

### 仍存在的问题

- Python GIL 限制 CPU-bound 并行真实加速比（ThreadPoolExecutor 约 2-3x，非线性）。
- 无 `/metrics` 端点聚合请求级统计（P95/avg）。

### 回归风险：无

所有改动在调用边界之外（线程池、日志、校验），未修改 `call_analysis_engine` 或评分逻辑内部。

---

## 4. Scraper / Analysis Validation Result

### 当前状态：可接受风险

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 多平台并行调度 | **通过** | 2+ 个 source 使用 ThreadPoolExecutor，单 source 退化为串行 |
| per-source timeout | **通过** | 默认 120s，超时返回结构化错误 |
| as_completed 外层 timeout | **修复** | 本轮发现并修复：外层 TimeoutError 会跳出 for 循环，新增 except 块收集未完成 futures |
| 异常隔离 | **通过** | 每个 source pipeline 独立 try/except，一个平台失败不影响其他 |
| degraded 模式 | **通过** | pipeline 部分失败时 `degraded=True`，分析仍基于已获取数据运行 |
| 入口校验 | **通过** | `limit_per_source <= 0` 时立即返回，不启动 Playwright |
| 分段耗时日志 | **通过** | scraper pipeline、batch analysis、total 各有独立 `[PERF]` 日志 |
| Playwright 内部 timeout | **已有** | 选择器等待 45s、浏览器启动有 try/except 保护 |

### 已确认改善点

1. 多平台抓取从串行累加变为并行取较慢者，Agent 路径预期提速约 50%。
2. 单平台 hang 不会拖垮整条链路（120s 硬超时 + 其余平台正常继续）。
3. 部分失败时系统不崩溃，返回已有数据的分析结果 + degraded 标记。

### 本轮修复

**`as_completed` 外层 timeout 处理缺失**：`as_completed(futures, timeout=T)` 的 `TimeoutError` 从 `for` 循环本身抛出，不被内层 `try/except` 捕获。如果所有 source 都卡在 timeout 边界，整个 pipeline 会抛未处理异常。已修复为外层 `except TimeoutError` 块，收集所有未完成 futures 为 timeout 结果。

### 仍存在的问题

- Playwright 每次抓取仍需 3-10s 启动 Chromium（无实例复用）。
- 无 circuit breaker：持续超时的 source 仍会被每次请求尝试。
- Render 免费档冷启动（30-60s）不可控。

### 回归风险：极低

修复的 `as_completed` 外层 timeout 处理是纯新增 except 块，不改变正常执行路径。

---

## 5. Before / After Summary

### 确定有效的改善

| 改善 | 证据 | 确定程度 |
|------|------|---------|
| **batch 分析并行化** | 代码从 `for` 循环改为 `ThreadPoolExecutor`，日志可观察 `workers=N` | 确定有效 |
| **多平台抓取并行化** | 代码从串行 `for src in want` 改为 `ThreadPoolExecutor` | 确定有效 |
| **Agent 路径不再无限挂死** | `real_analysis_service.py` 硬超时 180s + `multi_source_pipeline` per-source 120s | 确定有效 |
| **慢请求自动告警** | `api_server.py` 中间件 ≥ 5s 触发 P2 alert | 确定有效 |
| **部分失败不全挂** | `degraded` 标记 + per-source 异常隔离 + 合成信封 | 确定有效 |
| **无效输入快速拒绝** | batch 50 项上限 + `limit_per_source > 0` 校验 | 确定有效 |

### 需要后续运行时观察的

| 改善 | 说明 |
|------|------|
| batch 实际加速比 | GIL 约束下 ThreadPoolExecutor 对 CPU-bound 代码的真实提速比需通过 `[PERF]` 日志确认 |
| 多平台并行实际时间 | Playwright 在 Render 上的实际表现（冷启动 + 并行浏览器实例内存压力）需线上观察 |

---

## 6. Remaining Performance / Stability Risks

| 优先级 | 风险 | 影响 |
|--------|------|------|
| **1** | Python GIL 限制 CPU-bound 并行 | batch 加速比可能低于预期 |
| **2** | 无 circuit breaker | 持续超时的 source 每次都浪费 120s |
| **3** | Render 冷启动 | 首次访问 30-60s 不可控 |
| **4** | Streamlit UI 同步阻塞 | Agent 分析期间用户无法交互 |
| **5** | 无请求指标聚合 | 只有文本日志，无 P95/P99 数据 |

这些风险均不阻塞当前 MVP 稳定运行，适合在后续 Phase3 中逐步解决。

---

## 7. Phase2 Final Verdict

### Phase2 Stabilized

**原因：**

1. Phase2 的三轮变更（性能基线、第一轮优化、超时/降级保护）全部通过代码级复测，未发现回归问题。
2. 发现并修复了一处潜在风险（`as_completed` 外层 timeout 未捕获），该修复仅添加 except 块，不影响正常路径。
3. 所有改动在调用边界层面（线程池、日志、校验、超时包装），核心业务逻辑（评分、API 结构、UI 渲染）完全未动。
4. 超时控制和降级保护确保系统在异常场景下不会崩溃或无限挂死。
5. `[PERF]` 日志和 `send_alert` 提供了运行时可观测性基础。

---

## 8. Recommended Next Phase

### P9 Phase3 — 运行时可观测性增强与进阶稳定性

建议方向：

1. **内存级请求指标与 `/metrics` 端点**：添加请求计数器、平均耗时、timeout/error 计数，为数据驱动优化提供基础。
2. **Circuit breaker for flaky sources**：持续超时的 source 自动跳过 N 分钟，避免无谓等待。
3. **ProcessPoolExecutor 评估**：绕过 GIL 限制，评估 batch 分析是否可用多进程真并行。
4. **Render 冷启动缓解**：配置 health check ping 保活或评估付费档。

建议先从第 1 项开始 — `/metrics` 端点是后续一切数据驱动决策的前提。

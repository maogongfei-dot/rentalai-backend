# P9 Phase4 Async Rules

---

## Always Async

以下流程类型 **必须** 走异步路径（`POST /tasks` + poll）：

1. **涉及 Playwright / 浏览器自动化的流程。** Chromium 启动 + 页面抓取耗时 10–60 秒，内存占用 200–400 MB。在 Streamlit 进程中同步执行会阻塞所有用户并可能 OOM。
2. **多平台聚合分析（`run_multi_source_analysis`）。** 涉及多个 scraper 并行 + 数据聚合 + batch 分析引擎，总耗时 30–120 秒。
3. **任何预期耗时 > 10 秒的请求。** 超过此阈值的同步请求会触发 Render / PaaS 的请求超时（通常 30–60 秒），导致用户看到 502/504。

---

## Prefer Async

以下流程类型 **建议** 走异步路径，但当前阶段可保持同步：

1. **大批量 `/analyze-batch`（> 20 条）。** 当前走 `ThreadPoolExecutor` 并行，单次通常 < 10 秒。当批量数增大或分析逻辑变重时，应迁移到异步。
2. **未来可能引入的 LLM 调用。** 如果 Agent 路径加入 GPT/Claude 等 API 调用，响应时间不可控，应走异步。
3. **数据导出 / 报告生成。** 如果后续增加 PDF 报告或 CSV 导出功能，文件生成可能耗时较长。

---

## Keep Sync

以下流程 **必须保持同步**，不应异步化：

1. **`POST /analyze`（单条分析）。** 纯 CPU 计算，耗时 < 1 秒，同步返回是最佳体验。
2. **`POST /score-breakdown`、`/risk-check`、`/explain-only`。** 与 `/analyze` 相同——轻量计算，即时返回。
3. **`GET /health`、`GET /alerts`、`GET /tasks`、`GET /tasks/{id}`。** 查询接口必须同步，否则无法实现轮询。
4. **意图解析（`parse_rental_intent`）。** 纯规则解析，< 50ms，无外部依赖。
5. **表单校验、数据格式化、session state 操作。** 前端内部逻辑，不涉及 I/O。

---

## Anti-Patterns

以下写法 **禁止** 在 RentalAI 项目中使用：

### 1. 在 Streamlit 进程中直接运行 Playwright

```python
# ❌ 错误
from data.pipeline.analysis_bridge import run_multi_source_analysis
result = run_multi_source_analysis(...)  # 在 Streamlit 进程中同步执行
```

正确做法：通过 `POST /tasks` 提交到 FastAPI 后端。

### 2. 长任务不设超时

```python
# ❌ 错误
result = some_long_running_function()  # 无 timeout，可能无限挂起
```

正确做法：所有外部调用和长任务必须有 timeout。分析任务使用 Semaphore acquire timeout + analysis_bridge 内部 per-source timeout。

### 3. 绕过 Semaphore 直接启动后台线程

```python
# ❌ 错误
threading.Thread(target=run_multi_source_analysis, ...).start()  # 无并发控制
```

正确做法：所有后台任务必须通过 `_TASK_SEMAPHORE` 控制并发。

### 4. 在异步函数中修改全局状态

```python
# ❌ 错误
def _run_task(task_id, params):
    global_cache[key] = result  # 后台线程修改全局状态，无锁保护
```

正确做法：所有状态变更通过 `TaskStore._update`（内含 `_lock`）进行。

### 5. 前端直接写死轮询逻辑而不复用标准函数

```python
# ❌ 错误
while True:
    time.sleep(3)
    resp = requests.get(f"{base}/tasks/{task_id}")
    # ... 手写解析逻辑
```

正确做法：调用 `run_real_listings_analysis_async(..., on_status=callback)`，复用标准提交 + 轮询 + 结果解析逻辑。

# P9 Phase1 Monitoring Baseline

RentalAI MVP 的最小监控基线。无外部监控服务依赖，全部基于 Python `logging` 和平台日志。

---

## 1. Frontend Monitoring

### 架构说明

RentalAI 前端是 **Streamlit**（Python 服务端渲染），不是浏览器端 SPA。因此：

- **没有** `window.onerror` / `unhandledrejection` — 不适用
- HTTP 请求由 **Python `requests` 库**（服务端）发出，不在浏览器 Network 面板中
- 错误捕获通过 Python `try/except` + `logging` 模块实现

### 已实现的捕获

| 捕获点 | 位置 | 日志内容 |
|--------|------|---------|
| 单条 Analyze HTTP 请求失败 | `app_web.py` `run_analysis_for_ui()` | `API request failed \| url=... \| error=...` |
| 单条 Analyze JSON 解析失败 | 同上 | `Invalid JSON from API \| url=... \| error=...` |
| Batch JSON 请求失败 | `app_web.py` batch 区 | `Batch request failed \| url=... \| error=...` |
| 进程内引擎异常 | `run_analysis_for_ui()` | 错误字符串返回给 UI 显示 |

### 查看方式

**Render Dashboard → rentalai-ui → Logs**（实时日志流）。搜索 `[ERROR] rentalai.ui`。

---

## 2. API Monitoring

### 如何识别请求失败

前端（Streamlit 服务端）的 `requests.post` 在以下情况记录 `ERROR` 级别日志：

- HTTP 状态码非 2xx（`raise_for_status()` 触发 `RequestException`）
- 网络连接失败 / 超时
- 响应体非合法 JSON

### 打印信息

```
2026-03-22 10:15:32 [ERROR] rentalai.ui: API request failed | url=https://rentalai-api-xxxx.onrender.com/analyze | error=HTTPSConnectionPool...
```

包含：日志时间、级别、logger 名、请求 URL、异常信息。

---

## 3. Backend Monitoring

### 日志输出

| 项 | 说明 |
|----|------|
| **Logger** | `rentalai.api`（Python `logging` 模块） |
| **格式** | `%(asctime)s [%(levelname)s] %(name)s: %(message)s` |
| **级别** | INFO 及以上 |
| **位置** | stdout → Render 自动捕获 |

### 全局异常捕获

`api_server.py` 中注册了 FastAPI `@app.exception_handler(Exception)`：

- 捕获所有未处理异常
- 日志输出：`Unhandled exception on POST /analyze: <error>\n<traceback>`
- HTTP 响应：`500 {"error": "internal_error", "message": "..."}`

未被业务代码 `try/except` 捕获的异常不再返回 FastAPI 默认的 HTML 500 页面，而是结构化 JSON + 服务端完整 traceback 日志。

### 查看方式

**Render Dashboard → rentalai-api → Logs**。搜索 `[ERROR] rentalai.api`。

---

## 4. Health Check

### 当前返回内容

```
GET /health
```

```json
{
  "status": "ok",
  "service": "rentalai-api",
  "api_version": "P2-Phase5",
  "timestamp": "2026-03-22T10:15:32.123456+00:00"
}
```

### 如何使用

| 判断 | 条件 |
|------|------|
| 服务存活 | HTTP 200 + `status: "ok"` |
| 服务异常 | HTTP 502/504 或连接超时 |
| 冷启动中 | 连接超时但 Render 状态为 Live → 等 60 秒重试 |
| 版本确认 | `api_version` 字段 |
| 时钟偏移检查 | `timestamp` 字段（UTC） |

---

## 5. First Debug Path

### 用户报告问题时

**第 1 步：确认范围**

- 前端白屏 / 502？→ 看 UI 服务
- 分析结果报错？→ 区分 local engine 还是 HTTP API
- 特定接口报错？→ 看后端服务

**第 2 步：查看平台日志**

| 问题类型 | 先查 |
|---------|------|
| 前端 UI 异常 | Render → rentalai-ui → Logs，搜 `Traceback` 或 `[ERROR]` |
| API 请求失败 | Render → rentalai-ui → Logs，搜 `rentalai.ui` |
| 后端 500 | Render → rentalai-api → Logs，搜 `rentalai.api` 或 `Unhandled exception` |
| 服务不可达 | `curl /health` → 502 则查 build 日志；超时则冷启动 |

**第 3 步：复现与定位**

- 本地运行 `uvicorn api_server:app` + `streamlit run app_web.py` 复现
- 查看 traceback 中的具体函数和行号
- 确认是引擎逻辑（`api_analysis.py`）、数据层（`data/`）还是 UI 层（`web_ui/`）

---

## 6. Current Limitations

| 限制 | 说明 |
|------|------|
| **无持久化日志** | 日志仅存在于 Render 平台实时流中，实例重建后丢失 |
| **无报警** | 没有 Slack / Email / PagerDuty 通知 |
| **无用户级错误追踪** | 无法关联错误到具体用户 session |
| **无请求级指标** | 无响应时间、QPS、错误率统计 |
| **无 Sentry / APM** | 未集成第三方监控平台 |
| **Streamlit 请求不可见** | 浏览器 Network 面板看不到 API 请求（服务端发出） |

---

## 7. Next Step

1. **观察期**：用当前日志基线运行 1-3 天，收集真实错误模式。
2. **错误聚合**（P9 Phase1 Step3）：若发现重复模式，可添加简易计数器或写入 JSON 文件。
3. **简易报警**（P9 Phase2）：如接入 Render Notifications、或添加 webhook 到 Slack。
4. **APM 集成**（P9 Phase3+）：若项目进入正式运营，考虑 Sentry Python SDK 或 Render 付费 Log Drain。

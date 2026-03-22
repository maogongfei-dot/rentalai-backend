# P9 Phase1 Alerting System

RentalAI MVP 的轻量报警系统。不依赖 Sentry / Datadog 等外部服务，全部基于 Python `logging` + 可选 webhook。

---

## 1. Alert Levels

| 等级 | 含义 | 触发条件 | 响应要求 |
|------|------|---------|---------|
| **P0** | 致命 — 整站不可用 | 后端无法启动；所有 API 挂掉；前端白屏 | 立即处理 |
| **P1** | 严重 — 核心功能异常 | 任何 API 返回 500；连续 3 次请求失败；scraper 主流程崩溃 | 当天处理 |
| **P2** | 一般 — 非核心异常 | 单个接口偶发失败；某个页面报错 | 本周处理 |
| **P3** | 轻微 — 体验问题 | UI 小问题；非关键日志错误 | 记录即可 |

---

## 2. Backend Alerts

### 触发点

| 事件 | 级别 | 实现位置 |
|------|------|---------|
| 任何未捕获异常（500） | P1 | `api_server.py` `_global_exception_handler` |
| 同一 endpoint 连续 ≥ 3 次 500 | P1 | `FailureTracker` 自动触发 |

### 机制

1. **`send_alert(message, level, source)`** — 统一入口（`alert_utils.py`）
2. P0/P1 级别使用 `logger.critical`，P2/P3 使用 `logger.warning`
3. 日志格式：`[ALERT P1] 500 on POST /analyze: KeyError... | source=api-server | ts=...`
4. 若环境变量 `RENTALAI_ALERT_WEBHOOK` 已配置 → 后台线程 POST JSON 到该 URL

### 连续失败追踪

- `FailureTracker` 以 endpoint 路径为 key 计数
- 成功请求（非 5xx）自动重置对应计数器
- 阈值 **3** — 达到时触发 P1 级别 alert
- 运行时可通过 `GET /alerts` 查看各 endpoint 当前连续失败数

### 查看方式

- **Render Dashboard → rentalai-api → Logs**，搜索 `[ALERT`
- **`GET /alerts`** 返回当前 failure counts + threshold

---

## 3. Frontend Alerts

### 架构说明

RentalAI 前端是 Streamlit（Python 服务端），不是浏览器 SPA。因此：
- `window.onerror` / `unhandledrejection` 不适用
- HTTP 请求由 Python `requests` 在服务端发出
- 错误捕获通过 `try/except` + `FailureTracker` 实现

### 触发点

| 事件 | 级别 | 实现位置 |
|------|------|---------|
| 单条 Analyze HTTP 请求失败 | 记录 + 计数 | `app_web.py` `run_analysis_for_ui()` |
| Batch 请求失败 | 记录 + 计数 | `app_web.py` batch 区 |
| 同一 endpoint 连续 ≥ 3 次失败 | P1 alert | `FailureTracker` 自动触发 |
| 成功请求 | 重置计数 | 同上 |

### 查看方式

**Render Dashboard → rentalai-ui → Logs**，搜索 `[ALERT` 或 `[ERROR] rentalai.ui`。

---

## 4. API Failure Detection

### 判断逻辑

```
每次 API 请求:
  成功 → record_success(endpoint) → 重置该 endpoint 计数
  失败 → record_failure(endpoint) → 计数 +1
         如果计数 == threshold(3) → send_alert(P1)
```

### 当前参数

| 参数 | 值 | 可调 |
|------|-----|------|
| **threshold** | 3 次连续失败 | `FailureTracker(threshold=N)` |
| **scope** | 按 endpoint 路径独立计数 | — |
| **reset** | 任意成功请求即重置 | — |

### 追踪实例

| 位置 | 变量名 | source 标记 |
|------|--------|------------|
| 后端 `api_server.py` | `_api_failures` | `api-server` |
| 前端 `app_web.py` | `_ui_api_failures` | `streamlit-ui` |

---

## 5. Current Alert Channels

| 渠道 | 状态 | 说明 |
|------|------|------|
| **stdout / logging** | 已启用 | 所有 alert 通过 `logging.critical` / `logging.warning` 输出 |
| **Render Logs** | 已启用 | stdout 自动捕获到平台日志面板 |
| **Webhook** | 就绪（待配置） | 设置 `RENTALAI_ALERT_WEBHOOK` 即可推送到 Slack / Discord |
| **`GET /alerts`** | 已启用 | 运行时查看各 endpoint 连续失败计数 |

### Webhook 配置

```bash
# Slack Incoming Webhook
RENTALAI_ALERT_WEBHOOK=https://hooks.slack.com/services/T.../B.../xxx

# Discord Webhook (Slack-compatible)
RENTALAI_ALERT_WEBHOOK=https://discord.com/api/webhooks/.../slack
```

配置后，P0/P1 级别 alert 将自动 POST `{"text": "[ALERT P1] ..."}` 到该 URL。

---

## 6. How to Respond

### 收到 alert 后的排查路径

**第 1 步：确认范围**
- 搜索 `[ALERT` 关键字，读取 level / source / endpoint
- P0/P1 → 立即排查；P2/P3 → 记录、非紧急

**第 2 步：检查服务状态**
- `curl https://<API_URL>/health` — 200 则服务存活
- `curl https://<API_URL>/alerts` — 查看哪些 endpoint 在连续失败

**第 3 步：定位根因**
- Render → 对应服务 → Logs → 搜索同时段的 `Traceback` 或 `[ERROR]`
- 根据 traceback 中的文件名和行号定位具体模块

**第 4 步：判断严重性**
- 单个 endpoint 失败、其他正常 → P2，可安排修复
- 多个 endpoint 同时失败 → P1，优先处理
- `/health` 返回非 200 → P0，服务整体异常

---

## 7. Limitations

| 限制 | 说明 |
|------|------|
| **非实时推送** | 除非配置 webhook，alert 只存在于日志中 |
| **无持久化** | 失败计数存在内存中，实例重启后归零 |
| **无聚合** | 无法统计一段时间内的错误总数或趋势 |
| **无用户维度** | 无法关联错误到具体用户 session |
| **阈值固定** | 当前阈值 = 3，无法动态调整（需改代码） |
| **Streamlit 进程模型** | Streamlit 每个用户 session 可能有独立计数（Render 单进程模式下共享） |

---

## 8. Next Step

1. **配置 webhook**：创建 Slack / Discord Incoming Webhook，设置 `RENTALAI_ALERT_WEBHOOK` 环境变量，即可获得被动通知能力。
2. **错误聚合**（P9 Phase2）：将 alert 历史写入文件或简易 KV，支持 `/alerts/history` 查询。
3. **请求指标**（P9 Phase2）：添加 `response_time` / `request_count` 基础计数。
4. **APM 集成**（P9 Phase3+）：若项目进入正式运营，考虑 Sentry Python SDK（免费 tier 5k events/month）。

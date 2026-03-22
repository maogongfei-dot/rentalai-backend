# P9 Phase1 Issue Triage Board

RentalAI MVP 上线后的问题分级、排查入口与优先级框架。

---

## 1. Current Live Services

### 已上线

| 服务 | 平台 | 状态 |
|------|------|------|
| **rentalai-api**（FastAPI） | Render Web Service | 在线 — `/health`、`/analyze`、`/analyze-batch`、模块化 API |
| **rentalai-ui**（Streamlit） | Render Web Service | 在线 — 产品 UI + 进程内分析引擎 |

### 未上线 / 降级

| 模块 | 状态 | 说明 |
|------|------|------|
| Agent 真实抓取（Playwright） | **条件可用** | 取决于 Playwright Chromium 在 Render 上是否 build 成功。失败时 Agent Parse 仍可用，仅 "Continue to Analysis"（真实抓取）不可用 |
| 持久化数据盘 | 未配置 | `listings.json` 在 ephemeral 磁盘，实例重建丢失 |
| 认证 / CORS 收紧 | 未实施 | `allow_origins=["*"]`，无登录保护 |
| 定时抓取 / Worker | 未部署 | 无 cron job 或后台 Worker |

---

## 2. First-Line Error Categories

| 编号 | 类别 | 典型现象 | 排查入口 |
|------|------|---------|----------|
| **E1** | Frontend UI / page load | 白屏、502、Streamlit "Please wait..." 卡死 | Render → rentalai-ui → Logs |
| **E2** | Frontend API request failure | 页面红色错误 "API request failed" / "Invalid JSON" | Render → rentalai-ui → Logs（`requests` 异常） |
| **E3** | Backend health / startup | `/health` 返回非 200、502、连接超时 | Render → rentalai-api → Logs |
| **E4** | Backend business API failure | `/analyze` 返回 500、traceback | Render → rentalai-api → Logs |
| **E5** | CORS / env / config issue | 侧栏 API URL 显示 localhost、请求被拦截 | Render Dashboard → 环境变量检查 |
| **E6** | Scraper runtime issue | Agent "Continue" 后长时间无响应、OOM kill | Render → rentalai-ui → Logs（`playwright` 相关） |
| **E7** | Performance / timeout | 首次访问 30-60 秒无响应、分析请求超时 | 免费档冷启动特征；非 bug |
| **E8** | Deployment config drift | 新 push 后服务 build 失败、Root Dir 错误 | Render → Build Logs |

---

## 3. Severity Levels

| 等级 | 含义 | 响应时间 | 示例 |
|------|------|---------|------|
| **P0** | 整站不可用 | 立即处理 | 两个服务均 502；UI 和 API 同时 crash |
| **P1** | 核心功能不可用 | 当天处理 | 进程内分析报错（Use local engine 路径）；`/health` 持续失败 |
| **P2** | 非核心功能异常 | 本周处理 | Agent 抓取 OOM；HTTP API 路径失败但 local 路径正常；Batch JSON 报错 |
| **P3** | 体验问题 / 已知限制 | 记录即可 | 冷启动慢；反爬导致空结果；无认证；CORS 未收紧 |

---

## 4. Triage Priority Rules

### 优先修

- **P0**：整站不可用 → 立即查 Render Logs，必要时回滚 commit
- **P1**：核心分析路径断裂 → 检查引擎 import / 数据文件 / 环境变量

### 可延后

- **P2**：Agent 抓取 / Playwright 相关 → 记录 build 日志，排入 Docker 化计划
- HTTP API 路径失败但 local 路径正常 → 后端服务冷启动问题，等 60 秒重试

### 只记录不立刻修

- **P3**：冷启动慢、反爬空结果、CORS 全开、无认证
- 这些是已知限制，不影响 MVP 演示

### 决策流程

```
报错 → 确认类别（E1-E8）
     → 判断严重度（P0-P3）
     → P0/P1：立即查 Render Logs → 定位 → 修复或回滚
     → P2：记录 → 本周排期
     → P3：写入 Issue Board → 后续版本处理
```

---

## 5. First Response Checklist

### 用户报错后第一时间看什么

1. **确认报错类别**：是前端白屏？页面上的红色提示？还是后端返回异常？
2. **确认是否所有用户都受影响**：如果只是冷启动超时，等 60 秒重试。

### 前端先查

1. Render Dashboard → **rentalai-ui** → **Logs**
2. 搜索关键词：`Traceback`、`Error`、`Killed`、`ModuleNotFoundError`
3. 如果是 Playwright 相关（`browser`、`chromium`）→ P2，不阻塞主站

### 后端先查

1. Render Dashboard → **rentalai-api** → **Logs**
2. `curl https://<API_URL>/health` → 200 表示存活
3. 如果 502/504 → 检查 build 是否成功，服务是否在 sleep

### Scraper 先查

1. Render Dashboard → **rentalai-ui** → **Logs**（Scraper 在 UI 服务进程内）
2. 搜索关键词：`playwright`、`OOM`、`Killed`、`TimeoutError`
3. 如果 build 日志无 `Chromium ... downloaded` → Playwright 未安装成功

---

## 6. Current Suspected Risk List

按优先级排序：

| # | 风险 | 严重度 | 当前状态 | 下一步 |
|---|------|--------|---------|--------|
| 1 | Playwright Chromium 系统库缺失 | P2 | 首次 build 后才知 | 观察 build 日志；失败则进入 Docker 化 |
| 2 | 免费档 512 MB 内存 + Chromium OOM | P2 | 抓取时可能触发 | 限制 `limit_per_source` ≤ 5 |
| 3 | 免费档冷启动 30-60 秒 | P3 | 已知特征 | 演示前手动唤醒；或升级 plan |
| 4 | CORS `["*"]` + 无认证 | P3 | MVP 可接受 | 推广前收紧为 UI 域名 + 加 API Key |
| 5 | `area_module.py` 相对路径依赖 cwd | P3 | `rootDir: rental_app` 正确时可工作 | 后续统一为 `Path(__file__)` 基准 |
| 6 | `listings.json` ephemeral 磁盘 | P3 | 实例重建丢数据 | 后续加 Render Disk |
| 7 | Rightmove / Zoopla 反爬 | P3 | 业务风险 | 有 fallback 提示 |

---

## 7. Next Action

1. **部署后首轮巡检**：按 `P9_PHASE1_STABILITY_REVIEW_CHECKLIST.md` 逐项打勾。
2. **观察 1-3 天**：重点盯 Render Logs 中是否出现 P0/P1 级别异常。
3. **收集反馈**：分享给测试用户，记录真实使用中遇到的问题。
4. **进入 P9 Phase1 Step2**：基于收集到的问题，制定第一轮稳定性修复计划。

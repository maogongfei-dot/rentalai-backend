# P8 Phase2 Go-Live Runbook

本文档为 RentalAI **最小可上线版本（MVP）** 的最终上线执行手册，汇总所有前序文档的结论，提供可直接执行的部署顺序、验证清单、回滚方案和最终就绪判定。

---

## 1. Final Deployment Scope

### 本次上线包含

| 服务 | 平台 | 说明 |
|------|------|------|
| **rentalai-api**（FastAPI） | Render Web Service | 分析接口：`/health`、`/analyze`、`/analyze-batch`、模块化 API |
| **rentalai-ui**（Streamlit） | Render Web Service | 产品 UI + 进程内分析引擎 + Agent + 真实抓取（Playwright） |

### 不包含

- 独立 Scraper Worker / 消息队列
- 持久化数据盘（可选后续添加）
- 用户认证 / API Key 鉴权
- 生产级 CORS 收紧
- 定时抓取 cron job
- 第三方 LLM / 地图 API 集成

### MVP 上线边界

以「**演示可用**」为标准：公网可访问 UI、可进行单条分析和 Agent 驱动的真实抓取+分析、结果正常展示。不保证高并发、数据持久化、安全加固。

---

## 2. Final Deployment Order

> **平台**：Render。**Blueprint 文件**：`render.yaml`（双服务一次性创建）或 `render.backend.yaml` + `render.frontend.yaml`（分步创建）。

### Step 1 — 推送代码

确保 Git 远程分支包含以下关键文件：

- `render.yaml`（仓库根 `python_learning/`）
- `rental_app/api_server.py`
- `rental_app/app_web.py`
- `rental_app/requirements.txt`
- `rental_app/.env.example`

### Step 2 — 部署 API 服务

1. Render Dashboard → **New** → **Blueprint**，选 `render.backend.yaml`（或 `render.yaml`，先只关注 API）。
2. 连接 Git 仓库、选择分支。
3. 确认：**Root Directory** = `rental_app`，**Build** = `pip install -r requirements.txt`，**Start** = `uvicorn api_server:app --host 0.0.0.0 --port $PORT`，**Health check** = `/health`。
4. 无需手动添加环境变量（`PORT` 平台注入）。
5. 点击 Deploy，等待 build + deploy 完成。

### Step 3 — 验证 API 上线

```
curl -s https://<rentalai-api-xxxx>.onrender.com/health
```

预期返回：`{"status":"ok","service":"rentalai-api","api_version":"P2-Phase5"}`。

> 免费档首次请求可能需要 30–60 秒唤醒。

### Step 4 — 部署 UI 服务

1. Render Dashboard → **New** → **Blueprint**（使用 `render.frontend.yaml`）或在已有 Blueprint 中启用 UI 服务。
2. 确认：**Root Directory** = `rental_app`，**Build** = `pip install -r requirements.txt && playwright install chromium`，**Start** = `streamlit run app_web.py --server.port $PORT --server.address 0.0.0.0`。
3. **设置环境变量**：

   | Key | Value |
   |-----|-------|
   | `RENTALAI_USE_LOCAL` | `1` |
   | `RENTALAI_API_URL` | Step 3 获得的 API 公网 URL（无尾部斜杠） |

4. 点击 Deploy，**重点观察 build 日志**——确认 `playwright install chromium` 成功完成。

### Step 5 — 验证 UI 上线

1. 浏览器打开 `https://<rentalai-ui-xxxx>.onrender.com`。
2. 确认 Streamlit 首页加载。
3. 检查侧栏 **API base URL** 显示公网 API 地址（而非 `127.0.0.1`）。

### Step 6 — 冒烟测试

按以下顺序验证核心路径：

1. **进程内单条分析**：保持 `Use local engine` 开启 → 填写表单 → **Analyze Property** → 确认返回评分和分析结果。
2. **HTTP 单条分析**：关闭 `Use local engine` → **Analyze Property** → 确认结果来自公网 API。
3. **Agent 抓取+分析**：Agent 区输入 `Looking for a 2-bed flat in London under 1800` → **Parse** → **Continue to Analysis** → 等待 30–90 秒 → 确认结果卡片出现。
4. **Batch JSON（HTTP）**：折叠区 → Run batch request → 确认打到公网 API。

### Step 7 — 记录与收尾

- 记录两个公网 URL（API 和 UI）。
- 确认 Render Dashboard 中两个服务状态均为 **Live**。
- 可选：为 UI 服务添加 **Disk** + 配置 `RENTALAI_LISTINGS_PATH`。

---

## 3. Environment Variables Checklist

### Backend（rentalai-api）

| 变量 | 必填 | 说明 |
|------|------|------|
| `PORT` | 平台注入 | 无需手动设置 |

> 后端当前不读取其他 `RENTALAI_*` 变量。

### Frontend（rentalai-ui）

| 变量 | 必填 | 说明 |
|------|------|------|
| `PORT` | 平台注入 | 无需手动设置 |
| `RENTALAI_USE_LOCAL` | 建议 `1` | 进程内引擎模式 |
| `RENTALAI_API_URL` | **是**（条件） | 公网 API URL；缺失时仅影响 HTTP 路径（关闭 local engine 时） |

### 可选变量

| 变量 | 说明 |
|------|------|
| `RENTALAI_LISTINGS_PATH` | 持久化路径 |
| `PLAYWRIGHT_BROWSERS_PATH` | Chromium 缓存目录 |

### 阻止上线的变量缺失

- 无绝对阻塞。`RENTALAI_API_URL` 缺失时进程内路径（`RENTALAI_USE_LOCAL=1`）仍可用；仅 HTTP batch/单条分析失效。

---

## 4. Platform Execution Checklist

### Render — rentalai-api

| 配置项 | 值 |
|--------|----|
| Runtime | Python 3 |
| Root Directory | `rental_app` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn api_server:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |
| Plan | Free（演示）/ Starter（生产） |
| 环境变量 | 无需手动添加 |

### Render — rentalai-ui

| 配置项 | 值 |
|--------|----|
| Runtime | Python 3 |
| Root Directory | `rental_app` |
| Build Command | `pip install -r requirements.txt && playwright install chromium` |
| Start Command | `streamlit run app_web.py --server.port $PORT --server.address 0.0.0.0` |
| Health Check Path | `/` |
| Plan | Free（演示）/ Starter（生产） |
| `RENTALAI_USE_LOCAL` | `1` |
| `RENTALAI_API_URL` | `https://rentalai-api-xxxx.onrender.com` |

### Scraper

无独立服务。Scraper 随 **rentalai-ui** 部署，`buildCommand` 已包含 `playwright install chromium`。

---

## 5. Go-Live Verification Checklist

### 后端验证

- [ ] `GET /health` 返回 HTTP 200 + `{"status":"ok",...}`
- [ ] `POST /analyze` 用合法 body 返回分析结果（非错误）
- [ ] Render Dashboard 服务状态为 **Live**
- [ ] build 日志无 error（warning 可接受）

### 前端验证

- [ ] Streamlit 首页 `https://<UI_URL>/` 加载成功
- [ ] 侧栏 **API base URL** 显示公网 API 地址
- [ ] 进程内分析（`Use local engine` 开启）返回结果
- [ ] build 日志中 `playwright install chromium` 成功

### 前后端联通验证

- [ ] 关闭 `Use local engine` → **Analyze Property** → 返回结果（HTTP 打到公网 API）
- [ ] Batch JSON 折叠区 → **Run batch request** → 返回结果

### Scraper 验证

- [ ] Agent 输入 → **Parse** → **Continue to Analysis** → spinner 启动
- [ ] 等待完成：出现结果卡片 **或** 显示 "No listings found"（反爬导致空结果，不崩溃即可）

### 日志查看点

- Render Dashboard → 每个服务 → **Logs** tab
- 关注：Python traceback、OOM kill 信号、Playwright launch failure

---

## 6. Rollback / Fallback Plan

### 前端部署失败

| 场景 | 处理 |
|------|------|
| Build 失败（Playwright 缺系统库） | Render 自动保持上一个成功版本（如有）；若首次部署无上一版本，需切换到 Docker 运行时（`mcr.microsoft.com/playwright/python`） |
| Build 成功但运行时崩溃 | 查看 Logs → 回滚到上一次 Deploy（Render Dashboard → **Manual Deploy** → 选上一个 commit） |
| 环境变量配错 | 修改环境变量 → 服务自动重启 |

### 后端部署失败

| 场景 | 处理 |
|------|------|
| Build 失败 | 检查 `requirements.txt` 依赖是否与 Python 版本兼容 → 修改后重新 push |
| 运行时 `/health` 返回非 200 | 查看 Logs → 回滚 commit |

### Scraper 暂不可用

**允许主站先上线。** Scraper 不可用仅影响 Agent 「真实抓取+分析」路径。以下功能不受影响：

- Streamlit 首页加载
- 进程内单条分析（`Use local engine`）
- HTTP 单条分析 / Batch JSON
- Agent intent 解析（Parse）

用户在 Agent 点击 Continue to Analysis 时会看到 "No listings found" 或错误提示，但 **不会导致整站崩溃**。

### 部分上线策略

| 状态 | 是否可先上线 |
|------|-------------|
| API 成功 + UI 失败 | 可以。API 独立提供 HTTP 分析服务，可用 curl / Postman 验证。 |
| API 成功 + UI 成功 + Playwright 失败 | 可以。UI 全部分析功能可用，仅 Agent 真实抓取路径不可用。 |
| API 失败 | 不建议。先修 API，再部署 UI。 |

---

## 7. Final Blocking Issues

### Must fix before go-live

**无硬阻塞项。** 所有代码路径、环境变量体系、部署配置在审查中均已通过。唯一的未知项（Playwright build 兼容性）只能通过首次部署来验证，不属于代码层面需要修复的问题。

### Can defer after go-live

| 优先级 | 问题 | 说明 |
|--------|------|------|
| **High（上线后尽快）** | CORS 收紧 | 当前 `allow_origins=["*"]`；公网推广前需限制为 UI 域名 |
| **High（上线后尽快）** | 认证 / API Key | Streamlit 和 API 均无登录保护 |
| **Medium** | 持久盘 | `listings.json` 在 ephemeral 磁盘，实例重建丢失 |
| **Medium** | 免费档升级 | 双服务冷启动 + Chromium 内存压力 |
| **Medium** | Scraper → Worker 拆分 | 同步抓取阻塞 Streamlit |
| **Low** | `area_module.py` 路径统一 | 当前 `rootDir` 正确时可工作 |
| **Low** | `requirements-api.txt` 瘦化 | API 安装含不必要的 Streamlit/Playwright |

---

## 8. Final Verdict

**Ready for go-live.**

### 理由

1. **代码路径全通**：Frontend → Backend、Frontend → Analysis Bridge、Frontend → Scraper 三条主路径在架构上已打通，无路由不匹配、无缺失 import、无硬编码阻塞。
2. **部署配置完备**：`render.yaml`（双服务）、`render.backend.yaml`（仅 API）、`render.frontend.yaml`（仅 UI）三套 Blueprint 均与代码入口一致。
3. **环境变量体系完整**：`.env.example` 覆盖所有代码读取的变量，`render.yaml` 中 `envVars` 与文档一致。
4. **健康检查就绪**：API `/health` 已存在；UI `/` Streamlit 首页可作健康检查。
5. **降级可用**：Playwright 失败时，分析功能（进程内 + HTTP）不受影响；仅 Agent 真实抓取路径降级。

### 说明

§7 中 "Can defer" 的 High 项（CORS、认证）是 **公网正式推广前** 必须处理的安全项，但不阻止 **MVP 演示级上线**。

---

## 9. Immediate Next Action

1. **确认 Git 远程已推送**：包含 `render.yaml`、所有 `rental_app/` 代码和本文档。
2. **在 Render 创建 Blueprint**（推荐使用 `render.yaml` 一次性创建双服务）。
3. **等待 API 服务上线** → 验证 `/health`。
4. **在 UI 服务中填写 `RENTALAI_API_URL`** → 等待 UI 服务上线。
5. **按 §5 验证清单逐项确认**。
6. 记录公网 URL，MVP 上线完成。

---

## 附录：仓库内所有部署相关文件索引

| 文件 | 位置 | 用途 |
|------|------|------|
| `render.yaml` | 仓库根 | 双服务 Render Blueprint |
| `render.backend.yaml` | 仓库根 | 仅 API Blueprint |
| `render.frontend.yaml` | 仓库根 | 仅 UI Blueprint |
| `rental_app/Procfile` | 应用根 | Heroku 风格单进程（默认 API） |
| `rental_app/requirements.txt` | 应用根 | Python 依赖 |
| `rental_app/.env.example` | 应用根 | 环境变量模板 |
| `rental_app/api_server.py` | 应用根 | FastAPI 入口 |
| `rental_app/app_web.py` | 应用根 | Streamlit 入口 |
| `rental_app/P8_PHASE2_BACKEND_DEPLOY_RUNBOOK.md` | 应用根 | 后端部署详细步骤 |
| `rental_app/P8_PHASE2_FRONTEND_DEPLOY_RUNBOOK.md` | 应用根 | 前端部署详细步骤 |
| `rental_app/P8_PHASE2_SCRAPER_DEPLOY_PREP.md` | 应用根 | Scraper 部署准备 |
| `rental_app/P8_PHASE2_INTEGRATION_STATUS.md` | 应用根 | 整站联调状态 |
| `rental_app/P8_PHASE2_GO_LIVE_RUNBOOK.md` | 应用根 | 本文件 |
| `rental_app/P8_PHASE2_LAUNCH_CHECKLIST.md` | 应用根 | 精简打勾清单 |

# P8 Phase1 Deployment Plan

## 1. Chosen Deployment Architecture

**选定：双 Web 服务（同一 PaaS、同一仓库），抓取与 Streamlit 同进程**

- **服务 A**：**FastAPI**（`api_server.py`）— 对外提供 `/health`、`/analyze`、`/analyze-batch` 等。
- **服务 B**：**Streamlit**（`app_web.py`）— 对外提供产品 UI；**Agent / 真实多平台抓取 / Playwright** 在 **该 Python 进程内** 同步执行（与当前代码一致）。
- **抓取**：**不**单独拆成第三个服务（最小改动、与 `web_ui/real_analysis_service.py` 现状一致）。

**为何选它**

1. 项目 **无** `package.json` / 无静态 SPA，**不能**用「Vercel 静态前端 + 纯 API」套用主流 Jamstack。
2. Streamlit 必须是 **长期运行的 Python Web 进程**；与 FastAPI **分离** 只需两条启动命令，**无需**改分析引擎或 Agent 链路。
3. 抓取已嵌入 Streamlit 用户路径；拆 Worker 需队列与存储改造，**超出「最小可上线」** 范围（见 `P8_PHASE1_DEPLOYMENT_AUDIT.md`）。

---

## 2. Service Split

| 组件 | 部署位置 | 说明 |
|------|-----------|------|
| **Frontend** | **Streamlit Web Service**（`rentalai-ui`） | 入口 `app_web.py` |
| **Backend** | **FastAPI Web Service**（`rentalai-api`） | 入口 `api_server.py` |
| **Scraper** | **与 Streamlit 同服务、同进程** | Playwright 在 UI 服务构建阶段安装 Chromium，运行时由 pipeline 调用 |
| **环境变量** | 两服务 **不完全共用** | API 服务可无额外变量；UI 需 `RENTALAI_API_URL`（HTTP 联调时）、`RENTALAI_USE_LOCAL`、`RENTALAI_LISTINGS_PATH`（可选） |
| **独立服务** | 仅 **API** 与 **UI** 两个 Web 服务 | 抓取非独立进程 |

---

## 3. Environment Variables Mapping

### Streamlit（前端 / UI 服务）

| 变量 | 是否必配 | 说明 |
|------|-----------|------|
| `PORT` | 平台注入 | Render / Heroku 等自动设置；启动命令已使用 `$PORT` |
| `RENTALAI_USE_LOCAL` | 建议 `1` | 单条 Analyze 与 Agent/抓取走进程内逻辑；与当前 README 默认一致 |
| `RENTALAI_API_URL` | 条件必配 | 仅当关闭「Use local engine」或需 HTTP 调 batch 时，填 **API 服务公网 URL** |
| `RENTALAI_LISTINGS_PATH` | 可选 | 持久化 JSON 到挂载盘路径 |
| `STREAMLIT_SERVER_*` | 可选 | 官方 Streamlit 配置（端口一般由 `$PORT` 覆盖） |
| `PLAYWRIGHT_BROWSERS_PATH` | 可选 | 只读文件系统或自定义浏览器缓存目录时 |

### FastAPI（后端服务）

| 变量 | 是否必配 | 说明 |
|------|-----------|------|
| `PORT` | 平台注入 | `uvicorn ... --port $PORT` |

当前 **`api_server.py` 未读取** `RENTALAI_*`；CORS 为 `allow_origins=["*"]`，上线后建议收紧（后续步骤，本计划不改代码）。

### 抓取（逻辑层）

| 变量 | 说明 |
|------|------|
| 无独立进程变量 | 使用 UI 服务环境；`playwright install chromium` 在 **build** 阶段完成 |

### 在部署平台中需要配置的

1. **必做（双服务联通）**：在 **Streamlit 服务** 将 `RENTALAI_API_URL` 设为 **FastAPI 服务的 https 公网地址**（首次部署 API 后复制）。Render Blueprint 中已用 `sync: false` 提示在控制台填写。
2. **可选**：`RENTALAI_LISTINGS_PATH` + 平台持久盘（避免实例重建丢 `listings.json`）。

---

## 4. Deployment Platform Recommendation

| 部分 | 推荐 | 原因 |
|------|------|------|
| **整体** | **Render**（Blueprint：`render.yaml`） | 一条蓝图定义 **两个 Python Web 服务**、`rootDir` 支持 monorepo、与当前 **无 Docker** 约束一致；免费档适合演示（有冷启动与超时限制）。 |
| **前端（Streamlit）** | Render Web Service | 需长驻 Python，非静态托管。 |
| **后端（FastAPI）** | Render Web Service | 与 UI 同平台便于配环境变量与联调。 |
| **抓取** | 不单独部署 | 随 Streamlit 服务；若未来拆 Worker，再选 **Render Background Worker** 或自建队列（非本阶段）。 |

**不推荐为首选项**：**Vercel** 托管 Streamlit/Playwright 长进程不省事；**Railway** 可用但本仓库已提供 **Render** 专用蓝图，避免多平台重复配置。

---

## 5. Required Deployment Files

### 已有

- `rental_app/requirements.txt`
- `rental_app/README.md`、`.env.example`
- `P8_PHASE1_DEPLOYMENT_AUDIT.md`、`P8_PHASE1_RUNTIME_ENTRY_GUIDE.md`

### 本步新增

- **`render.yaml`**（仓库根 `python_learning/render.yaml`，`rootDir: rental_app`）
- **`rental_app/Procfile`**（Heroku 风格单进程示例，默认 API 一行）
- **`rental_app/P8_PHASE1_DEPLOYMENT_PLAN.md`**（本文件）

### 仍缺（后续阶段）

- **Dockerfile**（Playwright 系统依赖复杂时，Render 上可考虑 **Docker 运行时**；当前按计划不强制）
- **生产级** 认证、CORS 收紧、持久盘与备份策略的自动化描述
- **`package.json`**：项目无 Node 前端，**不需要**

---

## 6. Deployment Order

1. **部署 `rentalai-api`**（或先应用整个 Blueprint，但以 API 先健康为准）。
2. 浏览器或 `curl` 访问 `https://<api>/health` 确认就绪。
3. 在 **`rentalai-ui`** 环境变量中设置 **`RENTALAI_API_URL`** = 上一步公网 URL（无尾部斜杠）。
4. **部署 / 重启 `rentalai-ui`**，打开 Streamlit URL；侧栏验证 API 地址（若使用 HTTP 模式）。
5. **联调**：关闭 Use local engine 时单条分析、batch JSON 请求应打到公网 API；**真实抓取**仍在本机进程内，与 API 是否可达无关。

---

## 7. Remaining Risks

1. **Playwright 构建超时或缺系统库**：`playwright install chromium` 在 PaaS 构建阶段可能失败或超时；需加长超时或改用 Docker 运行时（见 Render 文档）。
2. **Streamlit 服务无持久盘**：默认 `data/listings.json` 在 ephemeral 磁盘上，**重建实例会丢**；生产需 **Disk** + `RENTALAI_LISTINGS_PATH`。
3. **双服务冷启动 / 免费档休眠**：首次访问慢；演示可接受，生产需升级 plan 或保活策略。
4. **抓取耗时**：用户一次操作可能触发双站抓取 + 分析，**超过** 平台 HTTP 超时风险在「仅 API」路径较低，在「UI 同步抓取」路径仍存在。
5. **安全**：无登录、CORS 全开、公网暴露 Streamlit — **仅适合演示**，非零信任生产。

---

## 8. Next Action

1. 在 Render 连接本仓库，选择 **`render.yaml`** 创建 Blueprint（若仓库根无该文件，请将 `render.yaml` 置于 Git 根或调整 Dashboard 中的 Blueprint 路径 / `rootDir`）。
2. 首次创建后，在控制台填写 **`rentalai-ui`** 的 `RENTALAI_API_URL`。
3. 验证 `/health` 与 Streamlit 首页；再测 **Continue to Analysis**（观察构建日志中 Playwright 是否成功）。
4. 若 UI 构建失败，按 Render「Python + Playwright」排错文档处理，或进入 **P8 下一阶段：Docker 化 UI 服务**。

---

## 附录：`package.json` 与构建命令

- 本项目 **没有** `package.json`，**无** `npm run build` / `npm start`。
- **构建**：`pip install -r requirements.txt`；UI 服务额外 **`playwright install chromium`**。
- **启动**：API 为 `uvicorn api_server:app --host 0.0.0.0 --port $PORT`；UI 为 `streamlit run app_web.py --server.port $PORT --server.address 0.0.0.0`。

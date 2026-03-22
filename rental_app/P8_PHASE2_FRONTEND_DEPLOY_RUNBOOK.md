# P8 Phase2 Frontend Deploy Runbook

本文档对应 **Phase2 Step2：将 Streamlit 前端部署上线**，使用户可通过公网访问 UI 并连接已部署的 **FastAPI 后端**。

> **前提**：Step1 已完成后端部署，你手中有一个 **可访问的 API 根地址**（例如 `https://rentalai-api-xxxx.onrender.com`）。

---

## 1. Deployment Target

| 项 | 说明 |
|----|------|
| **平台** | **Render** Web Service（与 Phase1 方案一致） |
| **原因** | Streamlit 是长驻 Python 进程，非静态站点——不能用 Vercel/Netlify 静态托管。Render 的 Python Web Service 原生支持 `pip` + `streamlit` + 平台注入 `$PORT`。 |

---

## 2. Frontend Entry

| 项 | 说明 |
|----|------|
| **入口文件** | `rental_app/app_web.py` |
| **build command** | `pip install -r requirements.txt && playwright install chromium` |
| **start command** | `streamlit run app_web.py --server.port $PORT --server.address 0.0.0.0` |
| **依赖文件** | `rental_app/requirements.txt`（含 Streamlit、Playwright 等） |
| **无 package.json** | 前端不是 Node 工程，无 `npm` 构建步骤 |

> **Playwright**：`playwright install chromium` 在 build 阶段执行；若构建超时或缺系统库，需在 Render Dashboard 调高超时，或改为 Docker 运行时（见 §7 风险）。

---

## 3. Required Environment Variables

| 变量 | 必填 | 用途 |
|------|------|------|
| **`PORT`** | **平台注入** | Render 自动设置；`startCommand` 使用 `$PORT` |
| **`RENTALAI_API_URL`** | **是**（条件） | 侧栏关闭 **Use local engine** 或使用 HTTP batch 时，Streamlit 用此地址请求 FastAPI。**填 Step1 拿到的公网 URL（无尾部斜杠）** |
| **`RENTALAI_USE_LOCAL`** | 建议 `1` | `1/true/yes`：单条 Analyze、Agent、真实抓取走进程内引擎（**不经 HTTP**）。默认 `1` 与本地开发一致 |
| **`RENTALAI_LISTINGS_PATH`** | 可选 | 持久化 `listings.json` 到挂载盘路径；不设则用临时目录内 `data/listings.json`，实例重建会丢 |
| **`PLAYWRIGHT_BROWSERS_PATH`** | 可选 | 自定义 Chromium 缓存目录（只读文件系统时需要） |

### 如何连接线上后端

- **变量名**：`RENTALAI_API_URL`
- **代码位置**：`app_web.py` 第 593 行 — `os.environ.get("RENTALAI_API_URL", "http://127.0.0.1:8000")`
- **运行时行为**：侧栏 **API base URL** 输入框默认取该值；用户可在界面上覆写（临时 session 级别）。
- **本地开发**：不设置此变量时，默认 `http://127.0.0.1:8000`（本地 uvicorn）。
- **线上部署**：设为 **`https://rentalai-api-xxxx.onrender.com`**（你的 API 公网地址）。

---

## 4. Pre-Deploy Checks

- [ ] **后端已上线**：`curl https://<API_URL>/health` 返回 `{"status":"ok",...}`。
- [ ] **仓库已推送**：远程分支包含 `rental_app/app_web.py`、`rental_app/requirements.txt` 和本 Runbook 所述改动。
- [ ] **本地已试跑**：`cd rental_app && streamlit run app_web.py`，Streamlit 首页加载正常。
- [ ] **若使用 Blueprint `render.frontend.yaml`**：文件在仓库根、`rootDir: rental_app` 与目录结构一致。

---

## 5. Deployment Steps（Render）

1. **打开** [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**（使用 `render.frontend.yaml`），或手动 **New Web Service**。
2. **连接** Git 仓库，选中分支。
3. **服务类型**：**Web Service**，**Runtime**：**Python 3**。
4. **Root Directory**：**`rental_app`**。
5. **Build Command**：**`pip install -r requirements.txt && playwright install chromium`**。
6. **Start Command**：**`streamlit run app_web.py --server.port $PORT --server.address 0.0.0.0`**。
7. **环境变量**：

   | Key | Value |
   |-----|-------|
   | `RENTALAI_USE_LOCAL` | `1` |
   | `RENTALAI_API_URL` | 后端公网 URL，例如 `https://rentalai-api-xxxx.onrender.com`（**无尾部斜杠**） |

8. **Health Check Path**（可选填 `/`）。
9. **点击 Deploy**，等待构建完成。
10. 复制 **UI 公网 URL**（形如 `https://rentalai-ui-xxxx.onrender.com`）。

---

## 6. API Connection Check

### 部署后验证流程

1. **打开 UI 公网 URL**：确认 Streamlit 首页加载。
2. **查看侧栏 API base URL**：应显示 **`https://rentalai-api-xxxx.onrender.com`**（来自 `RENTALAI_API_URL`），**而非** `http://127.0.0.1:8000`。若仍显示 localhost，说明环境变量未生效——检查 Render Dashboard。
3. **关闭 Use local engine**，点击 **Analyze Property**（用 Demo 数据或手动填合法表单）：
   - 成功：返回评分与分析结果。
   - 失败（网络错误）：检查 API 服务是否休眠、URL 是否正确、CORS 是否阻拦（当前 `allow_origins=["*"]`，理论上不阻拦）。
4. **测试 Agent（进程内）**：保持 **Use local engine** 开启，Parse → Continue → 等待抓取 + 分析完成。此路径 **不走 HTTP**，验证 Playwright 在该环境是否可运行。
5. **测试 Batch JSON（HTTP）**：折叠区 → **Run batch request**（关闭 local）→ 确认打到公网 API。

---

## 7. Known Risks

1. **Playwright 构建失败**：`playwright install chromium` 可能在 Render Python 运行时中 **缺系统库** 或 **超过构建超时**。缓解：在 Dashboard 增加超时或改 Docker 运行时。
2. **免费档冷启动 / 休眠**：首次访问慢（Streamlit + 后端双冷启动）；演示可接受。
3. **抓取稳定性**：Rightmove/Zoopla 的反爬策略在云 IP 上可能更严格——抓取返回空结果属业务风险，不影响分析引擎。
4. **无持久盘**：`listings.json` 在 ephemeral 磁盘，实例重建丢数据。
5. **无认证**：Streamlit 公网暴露，无登录保护——仅适合演示。

---

## 8. Next Step

1. **冒烟测试**：按 §6 流程走通「进程内分析」与「HTTP API 分析」两条路径。
2. **可选**：添加 Render **Disk** + 配置 `RENTALAI_LISTINGS_PATH` 实现持久化。
3. 进入 **Phase2 Step3：全链路端到端验证**（UI → API → 抓取 → 分析 → 结果展示）。

---

## 附录：仓库内相关文件

| 文件 | 作用 |
|------|------|
| `render.frontend.yaml` | 仅含 **rentalai-ui** 的 Render Blueprint |
| `render.yaml` | API + UI 双服务 Blueprint |
| `rental_app/.env.example` | 环境变量完整模板 |
| `rental_app/P8_PHASE2_BACKEND_DEPLOY_RUNBOOK.md` | 后端部署 Runbook（Step1） |

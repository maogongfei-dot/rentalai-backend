# P8 Phase2 Backend Deploy Runbook

本文档对应 **Phase2 Step1：仅将 FastAPI 后端部署上线**，获取可公网访问的 **API 根地址**（不要求部署 Streamlit 或 Playwright）。

---

## 1. Deployment Target

| 项 | 说明 |
|----|------|
| **平台** | **Render**（与 Phase1 `P8_PHASE1_DEPLOYMENT_PLAN.md` 一致） |
| **原因** | 已有 Blueprint 形态配置；Python Web Service 原生支持 `pip` + `uvicorn` + 平台注入 **`PORT`**；免费档适合先验证 API。 |

**备选**：Heroku / Fly.io 等支持 `Procfile` + `web: uvicorn ... $PORT` 的平台；命令与下文 **Start command** 相同。

---

## 2. Backend Entry

| 项 | 说明 |
|----|------|
| **入口文件** | `rental_app/api_server.py`（ASGI 实例名 **`app`**） |
| **启动命令** | `uvicorn api_server:app --host 0.0.0.0 --port $PORT` |
| **依赖文件** | `rental_app/requirements.txt`（与 UI 共用；后端不 import Playwright，但安装包中含 `streamlit`/`playwright` 不影响 API 启动） |
| **工作目录** | 构建与进程的工作目录应使 `import api_server`、`import web_bridge` 成功：**`rental_app`** 为包根（Render 使用 **`rootDir: rental_app`**） |

---

## 3. Required Environment Variables

| 变量 | 必填 | 用途 |
|------|------|------|
| **`PORT`** | **是**（平台注入） | Render/Heroku 等自动设置；**勿**在代码里写死监听端口。启动命令使用 **`$PORT`**。 |
| 其他 `RENTALAI_*` | **否** | 当前 **`api_server.py` 不读取** 业务环境变量；分析为进程内引擎调用。 |

**可选（运维/监控约定，代码未读）**：`RENTALAI_ENV=production` 等，仅作标签。

---

## 4. Pre-Deploy Checks

- [ ] 仓库已推送远程，且包含 **`rental_app/api_server.py`**、**`rental_app/requirements.txt`**。
- [ ] 若使用 **`render.backend.yaml`**：文件在 **Git 仓库根**（与 `python_learning` 结构一致）；若仓库根仅为 `rental_app`，则 **删除** yaml 内 **`rootDir: rental_app`**。
- [ ] 本地已试跑：`cd rental_app && uvicorn api_server:app --host 127.0.0.1 --port 8000`，且 **`curl http://127.0.0.1:8000/health`** 返回 JSON。

---

## 5. Deployment Steps（Render）

1. **打开** [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**（或 **Web Service** 手动创建，参数与下表一致）。
2. **连接** 含本仓库的 Git 提供方，选中 **分支**。
3. **若用 Blueprint**：指定 Blueprint 文件为仓库根目录的 **`render.backend.yaml`**（仅 API）；若用完整栈，可仍用 **`render.yaml`** 但先在控制台 **仅启用/先发布** API 服务（或临时删掉 UI 服务块 — 不推荐改主文件时，**优先使用 `render.backend.yaml`**）。
4. **服务类型**：**Web Service**，**Runtime**：**Python 3**。
5. **Root Directory**：**`rental_app`**（与 yaml 中 `rootDir` 一致；若仓库根已是 `rental_app` 则留空）。
6. **Install / Build**：与 yaml 一致 — **`pip install -r requirements.txt`**（Render 通常合并到 Build；无单独 npm）。
7. **Start command**：**`uvicorn api_server:app --host 0.0.0.0 --port $PORT`**
8. **环境变量**：一般 **无需** 手动添加（`PORT` 自动）；若平台要求显式添加，可设 `PORT` 为 Render 提供的值（通常自动生成）。
9. **Health check path**：**`/health`**
10. **部署完成后**：在服务页面复制 **公网 URL**（形如 `https://rentalai-api-xxxx.onrender.com`），即为 **第一个线上 API 根地址**。

**手动创建 Web Service（不用 Blueprint）时**：将上述 **Build**、**Start**、**Health check** 与 **rootDir** 填入对应字段即可。

---

## 6. Health Check

| 项 | 值 |
|----|-----|
| **地址** | **`GET {API_ROOT}/health`** 例如 `https://<your-service>.onrender.com/health` |
| **成功响应示例** | HTTP 200，JSON 类似：`{"status":"ok","service":"rentalai-api","api_version":"P2-Phase5"}` |

**说明**：不访问数据库、不启动 Playwright、不跑分析引擎逻辑（仅返回常量结构）。

---

## 7. Known Risks

- **冷启动 / 休眠**（免费档）：首次请求可能 **数十秒** 超时，健康检查可能暂时失败。
- **依赖体积**：`requirements.txt` 含 Streamlit、Playwright，**构建时间偏长**；后续可拆 **`requirements-api.txt`** 做瘦镜像（非本 Runbook 范围）。
- **CORS `allow_origins=["*"]`**：公网 API 易被任意前端调用；生产应收紧。
- **无鉴权**：`/analyze` 等接口 **无 API Key**，勿对不可信网络暴露敏感场景。

---

## 8. Next Step

1. 将得到的 **`https://...`** 写入 **Streamlit 部署** 的环境变量 **`RENTALAI_API_URL`**（Phase2 后续步骤）。
2. 本地或 CI 用 **`curl`** 对公网 **`/health`** 与 **`POST /analyze`**（最小合法 body）做一次 **冒烟测试**。
3. 进入 **Phase2 Step2：前端（Streamlit）部署与联调**（见后续文档）。

---

## 附录：仓库内相关文件

| 文件 | 作用 |
|------|------|
| `render.backend.yaml` | 仅含 **rentalai-api** 的 Render Blueprint |
| `render.yaml` | 含 API + UI 双服务 |
| `rental_app/Procfile` | `web: uvicorn api_server:app --host 0.0.0.0 --port $PORT` |

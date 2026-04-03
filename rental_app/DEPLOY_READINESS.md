# Phase 6 — 部署可行性检查 & 上线前结构梳理（第 1 步）

本文档只做**准备检查**与**最小说明**，不涉及公网实际部署与业务功能变更。

---

## 1. 前后端结构（当前仓库 `rental_app/`）

| 角色 | 入口 / 访问方式 | 说明 |
|------|-----------------|------|
| **后端** | **`run.py`** → `uvicorn api_server:app` | FastAPI 应用定义在 **`api_server.py`**（`app = FastAPI(...)`）。 |
| **前端（静态）** | **无独立 dev server**；由 FastAPI **挂载** `web_public/` | 浏览器访问 **`/`**、**`/login`** 等，静态资源 **`/assets/*`**。根目录由 `api_server` 内 `web_public` 相对路径解析。 |
| **可选旧 UI** | **`app_web.py`**（Streamlit） | 与主站**不同进程**；需单独部署或本地 `streamlit run`。 |

| 文件 | 是否存在 | 用途 |
|------|----------|------|
| **`requirements.txt`** | ✅ | 主安装：`pip install -r requirements.txt` |
| **`requirements-docs.txt`** | ✅ | 文档/可选工具，非运行时必装 |
| **`runtime.txt`** | ✅ | 建议 Python 版本（如 `python-3.11.8`），供 Render 等识别 |
| **`web_public/package.json`** | ✅ | **无 npm 依赖**；仅 `npm run build` 执行 `scripts/inject-api-base.mjs`（跨域/分域时注入 API base 到 HTML meta） |
| **`.env`** | 可选（勿提交） | 模板：**`.env.example`**；**`run.py`** 启动前自动加载同目录 `.env`（stdlib，无 python-dotenv） |

---

## 2. 环境变量（部署相关）

| 变量 | 说明 |
|------|------|
| **`PORT`** | PaaS 注入；**`config.get_bind_port()` 会读取**；若设置则 **`get_bind_host()` 默认 `0.0.0.0`**（便于对外监听） |
| **`RENTALAI_HOST` / `RENTALAI_PORT`** | 显式覆盖绑定 |
| **`RENTALAI_DEBUG`** | `1/true/yes` 时 debug 日志；**生产建议 `0` 或不设** |
| **`RENTALAI_RELOAD`** | 热重载；**生产勿设为 1** |
| **`ALLOWED_ORIGINS`** | CORS；**分域部署时建议显式配置**（逗号分隔）；未设时 `*`（宽松） |
| **`RENTALAI_RECORDS_DB_PATH` / `RENTALAI_TASK_STORE_PATH`** | 持久化路径（无盘实例重建会丢数据） |
| **`RENTALAI_PERSISTENCE_ANALYSIS_HISTORY_JSON`** | 服务端 JSON 分析历史路径（可选覆盖） |
| **`RENTALAI_ENV`** | `development`（默认）或 `production`：影响有效调试日志、`get_uvicorn_reload()` 在生产默认关 |
| **`RENTALAI_PUBLIC_API_HOST`** | 未设 **`RENTALAI_API_URL`** 时，与 **`RENTALAI_PORT`/`PORT`** 拼出 Streamlit 默认 API 根（默认主机 `127.0.0.1`） |
| `RENTALAI_API_URL` | **Streamlit** 调 FastAPI 的完整根 URL；不设则用 `RENTALAI_PUBLIC_API_HOST` + 绑定端口 |

详见 **`.env.example`**。

### Phase 6 第 2 步 — 前后端可切换配置（摘要）

- **后端**：`config.py` 集中 **`PORT` / `RENTALAI_PORT`、`RENTALAI_HOST`、`RENTALAI_DEBUG`、`RENTALAI_RELOAD`、`RENTALAI_ENV`**；`run.py` 用 **`get_effective_debug()`**（生产未显式开调试时不刷 DEBUG 日志）。
- **前端**：**`web_public/assets/api_config.js`** 从 **`<meta name="rentalai-api-base">` / `vite-rentalai-api-base`** 读 API 根，空则同源；**`rentalai-env`** 可覆盖 **`window.RENTALAI_ENV`**，否则按 hostname 推断。构建时 **`scripts/inject-api-base.mjs`** 可写入 meta（含可选 **`RENTALAI_ENV`**）。

---

## 3. 建议命令

### 后端（主产品）

```bash
cd rental_app
pip install -r requirements.txt
# 可选：playwright install chromium
python run.py
```

等价（需在 `rental_app` 目录下，保证 import 路径）：

```bash
uvicorn api_server:app --host 0.0.0.0 --port 8000
```

生产/PaaS：由平台注入 **`PORT`**，勿手动写死 `8000`；**`Procfile`** / **`render.yaml`** 已示例 **`python run.py`**。

### 前端（静态）

- **同机部署（推荐 Demo）**：**不单独启动前端**；打开 **`http://<host>:<port>/`** 即可。
- **Vercel 等仅静态**：在 **`web_public/`** 下 `npm install`（无依赖则极快）→ **`npm run build`**（可选注入 API base）→ 按 **`vercel.json`** 路由；API 需指向已部署后端（meta 或构建 env，见 **`scripts/inject-api-base.mjs`**）。
- **运行时**：默认 **`web_public/assets/api_config.js`** 使用**同源相对路径**（`RENTALAI_API_BASE=""`），与 API 同域时无需改代码。

---

## 4. 本地/部署风险点（最小整理结论）

| 项 | 现状 | 是否阻碍部署 |
|----|------|----------------|
| **localhost** | `config.py` 默认无 `PORT` 时监听 `127.0.0.1`；**有 `PORT` 时默认 `0.0.0.0`** | 否；PaaS 正常 |
| **硬编码 API 域名** | **`api_config.js`** 默认同源；分域由 **meta / 构建注入** | 否 |
| **绝对路径** | `api_server` 用 **`Path(__file__).parent / "web_public"`**，随部署目录变化 | 否（工作目录需为 `rental_app` 或等价） |
| **DEBUG** | 仅当 **`RENTALAI_DEBUG`** 为真 | 否；生产不设即可 |
| **CORS 默认** | 未设 `ALLOWED_ORIGINS` 时为 `*` | 分域前端时需**显式配置** |
| **会话 / SQLite** | 内存 token、本地 SQLite/JSON | **多实例/无持久盘**会丢数据；属产品/运维约束，非本步代码大改范围 |

**架构未改**；第 1 步修正 **`.env.example`** 中 `PORT` 说明；第 2 步将端口/API 默认值收拢到 **`config.py`** 与 **`api_config.js` + HTML meta**。

---

## 5. 结论（Phase 6 第 1 步）

| 问题 | 结论 |
|------|------|
| **是否基本可部署？** | **是**——单进程 FastAPI + 静态 `web_public`、**`requirements.txt`**、**`run.py`**、**`Procfile`/`render.yaml`**（若使用）已具备。 |
| **部署前必须补什么？** | 平台 **`PORT`**、**`pip install -r requirements.txt`**；若静态与 API **不同域**：**`ALLOWED_ORIGINS`** + 前端 **build 注入或 meta**；若需持久数据：**磁盘路径环境变量**。 |
| **建议后端启动** | **`python run.py`**（工作目录 **`rental_app`**） |
| **建议前端方式** | **同源**：无需单独前端进程；**分域**：`web_public` 下 **`npm run build`** + 配置 API base |

更细的 Render 蓝图与风险见 **`P10_PHASE5_DEPLOYMENT.md`**、**`DEPLOYMENT_PLAN.md`**。

---

## Phase 6 — 第 3 步：本地启动与脚本

- **说明**：**`LOCAL_RUN.md`** — 依赖、`python run.py`、静态页访问方式、可选 **`.env`**、冒烟命令。
- **脚本**：**`start_local.bat`**（Windows，`rental_app` 根目录）、**`scripts/run_backend.bat`**、**`scripts/run_backend.sh`**（bash）。

# P10 Phase5 Deployment

## 1. Current Stack

| 层级 | 技术 |
|------|------|
| **公网产品（Phase3）** | **FastAPI**（`api_server.py`）同源提供 JSON API + 静态页（`web_public/`）：`/`, `/login`, `/register`, `/history`, `/result/{task_id}` |
| **启动入口** | `python run.py` → Uvicorn，读取 **`PORT`** / **`RENTALAI_*`**（见 `config.py`） |
| **可选旧界面** | **Streamlit**（`app_web.py`），与 Phase3 站点独立，需单独进程 |
| **异步分析** | 内存 **TaskStore** + 线程队列；抓取依赖 **Playwright + Chromium** |
| **持久化** | **SQLite**（`analysis_records` / `users` / `task_records` 等）、可选 **JSON**（`.task_store.json`） |

结论：主栈为 **FastAPI + Uvicorn**，符合「Python Web」类部署。

## 2. Chosen Platform

**Render**（Web Service + Blueprint `render.yaml`）

**原因（最低风险、与仓库现状一致）：**

- 仓库已具备 **`render.yaml`**、**`Procfile`**、**`run.py`**，与 Render 的 **`PORT`** 注入和 **`python run.py`** 启动方式已对齐。
- 单进程即可发布 **Phase3 全站**，无需再搭 Node 或分离静态 CDN。
- **Railway / Streamlit Cloud** 等未在本步新增第二套配置，避免分叉。

> 若仓库根目录是 **`python_learning`**：在 Render 使用 Blueprint 时保持 **`rootDir: rental_app`**。若仓库根就是 **`rental_app`**：删除 `render.yaml` 里各服务的 **`rootDir`** 字段。

## 3. Required Files

| 文件 | 作用 |
|------|------|
| `render.yaml` | Blueprint：API 服务构建/启动；可选 Streamlit 服务 |
| `rental_app/run.py` | 统一入口；加载 `.env`；`PORT` 存在时默认监听 `0.0.0.0` |
| `rental_app/config.py` | `HOST`/`PORT`/`RELOAD`/`DEBUG` 等 |
| `rental_app/Procfile` | `web: python run.py`（Heroku 风格平台备用） |
| `rental_app/requirements.txt` | Python 依赖 |
| `rental_app/runtime.txt` | 锁定 Python 版本（Render 识别） |
| `rental_app/.env.example` | 变量说明（勿提交真实 `.env`） |

**Phase5 对 `render.yaml` 的调整**：`rentalai-api` 的 **`buildCommand`** 增加 **`playwright install chromium`**，与线上 **`/tasks`** 真实抓取一致（构建时间变长属预期）。

## 4. Environment Variables

| 变量 | 部署时说明 |
|------|------------|
| **`PORT`** | Render/Heroku **自动注入**；**勿手动覆盖**（除非你知道在做什么） |
| **`RENTALAI_HOST`** | 一般 **不设**；有 `PORT` 时 `run.py` 默认 `0.0.0.0` |
| **`RENTALAI_RELOAD`** | 生产 **不设或 `0`**（禁用热重载） |
| **`RENTALAI_DEBUG`** | 生产建议 **`0`** |
| **`RENTALAI_SECRET_KEY`** | 预留；当前内存 token **未使用**该项，可填占位便于后续扩展 |
| **`RENTALAI_RECORDS_DB_PATH`** | 可选；挂载 Render **Persistent Disk** 后指向盘内路径，减轻 SQLite 丢失 |
| **`RENTALAI_TASK_STORE_PATH`** | 同上，持久化 `.task_store.json` |
| **`PLAYWRIGHT_BROWSERS_PATH`** | 可选；自定义 Chromium 缓存目录 |

Streamlit 服务（若部署）仍需 **`RENTALAI_API_URL`** = `https://<rentalai-api>.onrender.com`（无尾斜杠）。

## 5. Run Command

- **Render**：`startCommand: python run.py`（已由平台注入 `PORT`）。
- **本地**：`cd rental_app && python run.py`（默认 `127.0.0.1:8000`）。

## 6. Public Access Goal

部署 **`rentalai-api`** 成功后，公网地址形如：

`https://rentalai-api.onrender.com`（具体以 Dashboard 为准）

用户应能：

- 打开 **`/`** 首页  
- **`/register` / `/login`**  
- 登录后提交分析 → **`/result/{task_id}`**  
- **`/history`** 查看本人记录  

（分析耗时与 Playwright/目标站点可用性有关，与本地一致。）

## 7. Current Data Risks

| 存储 | 位置 | 部署后风险 |
|------|------|------------|
| **Bearer token** | 服务端 **内存** `_AUTH_TOKENS` | 进程重启 / 多实例 → **立即失效或不一致**；免费实例 **冷启动** 后用户需重新登录 |
| **SQLite** | 默认 `rental_app/.rentalai_records.db` | 无持久盘时 **重部署/换实例** 可能 **清空用户与历史** |
| **TaskStore JSON** | 默认 `rental_app/.task_store.json` | 同上；与内存任务状态 **不跨实例** |
| **进行中任务** | 内存队列 + 线程 | 实例休眠后 **任务中断**；仅适合 demo |

**本步不强制改架构**；若要严肃运营：持久盘 + 单实例 / 或后续外置 DB 与队列。

## 8. Limitations

- **免费 Web Service 休眠**：首访冷启动 **数十秒**，且 **登录态随进程清空**。  
- **Playwright 构建/运行** 占用大，构建失败时需调高超时或查 Render 日志。  
- **多实例**（水平扩展）与当前 **内存 session + 本地 SQLite** **不兼容**，请勿在未改存储前扩容多副本。  
- **CORS** 当前为宽松配置；若拆前后域需再收紧。

## 9. Next Step

1. 在 Render 为 **`rentalai-api`** 挂载 **Persistent Disk**，设置 **`RENTALAI_RECORDS_DB_PATH`** / **`RENTALAI_TASK_STORE_PATH`**。  
2. 将会话改为 **Redis 或 DB**（或粘性会话 + 单实例）。  
3. 增加 **部署后冒烟脚本**（HTTP 检查 `/health`、`/`、`/login`）。  
4. 按需 **关闭或拆分** Streamlit 服务，降低免费额度占用。

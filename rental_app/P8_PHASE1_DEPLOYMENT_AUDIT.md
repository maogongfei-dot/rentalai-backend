# P8 Phase1 Deployment Audit

本文件基于 **2025-03-21** 对仓库内 **`rental_app/`**（RentalAI 可运行代码根目录）的扫描生成；仓库上级另有 `python_learning/area_data.json` 等文件，**不属于** `rental_app` 包内依赖，下文单独说明。

**Step2（部署前基础整理）补充**：已新增 **`README.md`**、**`.env.example`**、**`P8_PHASE1_RUNTIME_ENTRY_GUIDE.md`**；`listing_storage` 支持可选环境变量 **`RENTALAI_LISTINGS_PATH`**。仍以本文 §6–§8 为阻塞项主清单，细节以新文档为准。

**Step3（部署方案）补充**：已新增 **`P8_PHASE1_DEPLOYMENT_PLAN.md`**、仓库根 **`render.yaml`**（双 Web 服务）、**`rental_app/Procfile`**（单进程 API 示例）。未改分析 / Agent / 抓取业务代码。

**Step4（部署前联调清单）补充**：已新增 **`P8_PHASE1_PREDEPLOY_CHECKLIST.md`**；`.env.example` 补充 **`PORT`** 说明（平台注入、与 `render.yaml` 一致）。

**Phase2 Step1（后端部署 Runbook）**：已新增 **`P8_PHASE2_BACKEND_DEPLOY_RUNBOOK.md`**、仓库根 **`render.backend.yaml`**（仅 API）；`api_server.py` 头注释补充生产启动方式。

**Phase2 Step2（前端部署 Runbook）**：已新增 **`P8_PHASE2_FRONTEND_DEPLOY_RUNBOOK.md`**、仓库根 **`render.frontend.yaml`**（仅 Streamlit UI）；`app_web.py` 侧栏 API 提示改为环境变量感知；`.env.example` 补充 `RENTALAI_API_URL` 本地/线上双示例。

**Phase2 Step3（整站联调 + Scraper 部署准备）**：已新增 **`P8_PHASE2_SCRAPER_DEPLOY_PREP.md`**（Scraper 运行要求与部署方案）、**`P8_PHASE2_INTEGRATION_STATUS.md`**（整站联调状态与最终部署顺序）。结论：整站代码路径已打通，唯一未验证项为 Playwright Chromium 在 PaaS 上的 build 兼容性。

**Phase2 Step4（Go-Live 收尾）**：已新增 **`P8_PHASE2_GO_LIVE_RUNBOOK.md`**（最终上线执行手册：部署顺序、验证清单、回滚方案、就绪判定）、**`P8_PHASE2_LAUNCH_CHECKLIST.md`**（精简可打勾上线清单）。**最终结论：Ready for go-live。**

---

## 1. Current Project Structure

### 前端位置

- **无**独立 Node 前端工程：未发现 `package.json`、`vite.config.*`、`next.config.*`、`src/main.tsx` 等。
- **实际「可访问网站」UI** 为 **Streamlit 单页应用**：
  - 入口：**`rental_app/app_web.py`**
  - 启动说明见文件头注释：`streamlit run app_web.py`，默认 `http://localhost:8501`
- 展示与交互组件集中在 **`rental_app/web_ui/`**（卡片、batch 区、Agent 入口等）。

### 后端位置

- **HTTP API** 入口：**`rental_app/api_server.py`**（FastAPI `app`）
- 启动说明见文件头：`uvicorn api_server:app --reload --host 127.0.0.1 --port 8000`，且注明 **需在 `rental_app` 目录下执行**（保证 `web_bridge` 等模块 import 路径正确）。
- 业务分析逻辑主要在 **`rental_app/api_analysis.py`**、**`rental_app/web_bridge.py`** 及引擎相关模块（与 API/UI 共享进程内调用路径）。

### 抓取模块位置

- **Playwright 与浏览器会话**：**`rental_app/data/scraper/playwright_runner.py`**
- **站点抓取器**：**`rental_app/data/scraper/rightmove_scraper.py`**、**`rental_app/data/scraper/zoopla_scraper.py`**（及 `base_scraper.py`、`listing_scraper.py` 等）
- **编排管道**：**`rental_app/data/pipeline/`**（如 `rightmove_pipeline.py`、`zoopla_pipeline.py`、`multi_source_pipeline.py`、`analysis_bridge.py`）
- **命令行调试入口（脚本）**：**`rental_app/scripts/`**  
  例如：`run_rightmove_pipeline.py`、`run_zoopla_pipeline.py`、`run_multi_source_pipeline.py`、`run_multi_source_analysis.py`、`run_rightmove_scrape.py`、`run_zoopla_probe.py` 等（用于本地/CI 式运行，非 HTTP 路由暴露）。

### 关键目录说明

| 目录 | 作用 |
|------|------|
| `web_ui/` | Streamlit 用 UI 组件与 Agent/真实抓取调度封装 |
| `data/scraper/` | Playwright 与各门户列表抓取 |
| `data/pipeline/` | 抓取 → 归一 → 聚合 → 分析桥接 |
| `data/normalizer/`、`data/schema/` | Listing 归一与标准模型 |
| `data/storage/` | 本地 JSON 持久化（`listings.json`） |
| `scripts/` | Pipeline / 抓取调试 CLI |
| `docs/` | 各阶段设计说明（非部署配置） |

---

## 2. Deployment Entry Points

### Frontend entry

- **`app_web.py`** → `streamlit run app_web.py`（工作目录应为 **`rental_app`**）。

### Backend entry

- **`api_server.py`** → `uvicorn api_server:app --host 0.0.0.0 --port 8000`（生产需把 host/port/工作目录写清；当前注释为本地 `127.0.0.1`）。

### Scraper entry

- **库方式**：由 `data/pipeline/*`、`web_ui/real_analysis_service.py` 等在 **同一 Python 进程内** import 并调用 Playwright。
- **脚本方式**：`scripts/run_*.py`（适合运维/定时任务/手工，而非用户 HTTP 一键触发时的唯一形态）。

### 推荐启动命令（已知、最小可演示）

在 **`rental_app`** 目录：

```bash
pip install -r requirements.txt
playwright install chromium   # requirements 注释已说明
```

终端 1（API，可选，用于「关闭 Use local engine」时的 HTTP 调用）：

```bash
uvicorn api_server:app --host 0.0.0.0 --port 8000
```

终端 2（Streamlit UI）：

```bash
streamlit run app_web.py --server.address 0.0.0.0 --server.port 8501
```

环境变量（代码中已出现）：

- **`RENTALAI_API_URL`**：Streamlit 侧请求 API 的 base（默认 `http://127.0.0.1:8000`）。
- **`RENTALAI_USE_LOCAL`**：为 `1/true/yes` 时，单条 **Analyze Property** 走进程内引擎，不请求 HTTP。

---

## 3. Existing Deployment Files

| 文件 / 类型 | 状态 | 说明 |
|-------------|------|------|
| **`rental_app/requirements.txt`** | **已存在** | 含 streamlit、fastapi、uvicorn、requests、playwright |
| **`rental_app/requirements-docs.txt`** | **已存在** | 文档类依赖，与核心运行可分离 |
| **`package.json` / 前端构建链** | **缺失** | 无独立 SPA；Streamlit 即前端运行时 |
| **`.env` / `.env.example`** | **缺失** | 无集中环境变量模板；仅代码内 `os.environ.get(...)` |
| **仓库根 `README.md`（python_learning）** | **未发现**（本次扫描） | 启动说明分散在 `app_web.py`、`api_server.py`、`web_ui/README.md` 等 |
| **`Dockerfile`** | **缺失** | |
| **`docker-compose.yml`** | **缺失** | |
| **`Procfile`** | **缺失** | |
| **`vercel.json` / `render.yaml` / `railway.json`** | **缺失** | |
| **nginx 配置** | **缺失** | |

---

## 4. Frontend-Backend Integration Status

### 通信方式

1. **Streamlit（`app_web.py`） + 进程内 Python 调用**  
   - **Analyze Property** 在 `RENTALAI_USE_LOCAL` 为真时：直接 `web_bridge` / `api_analysis` 链，**无 HTTP**。  
   - **Agent Continue** 与 **Run real multi-source analysis**（P7）：经 **`web_ui/real_analysis_service.run_real_listings_analysis`** → **`data.pipeline.analysis_bridge.run_multi_source_analysis`**，**全进程内**，不经过 FastAPI。

2. **Streamlit → FastAPI（HTTP）**  
   - 关闭 **Use local engine** 时：**Analyze Property** 使用 **`requests.post`** 调侧栏选择的端点（`/analyze` 等）（见 `app_web.py` 中 `run_analysis_for_ui`）。  
   - **Batch 折叠区** 中 **Run batch request**：使用 **`requests.post({API}/analyze-batch)`**（仅当非 local 且 JSON 合法）。  
   - Base URL 来自侧栏，默认 **`RENTALAI_API_URL` 或 `http://127.0.0.1:8000`**。

3. **FastAPI（`api_server.py`）**  
   - 提供 `/health`、`/analyze`、`/analyze-batch` 等；**CORS** 当前为 **`allow_origins=["*"]`**（便于本地联调，生产需收紧）。  
   - **不包含** 多平台 Playwright 抓取的独立 HTTP 路由（抓取在 Streamlit/脚本进程内触发）。

### 是否已适合直接「上线为公网产品」

- **分析 API 本身**：可作为 **无状态后端** 部署（需注意超时与并发）。  
- **当前 Streamlit 产品形态**：与 **Playwright、本地 JSON 存储、长耗时抓取** 强绑定；**不等同于**「静态前端 + 纯 REST」的常见 SaaS 结构。  
- **结论**：**API 层具备可拆分部署潜力**；**整站按现有功能原样一键上无服务器（serverless）平台不现实**，更适合 **单台长驻主机** 或 **拆成 API 服务 + 异步抓取 Worker** 后再做轻量前端。

---

## 5. Scraper Deployment Recommendation

### 建议：**与「用户请求同步」的抓取不要默认与无状态 Web 同进程硬绑；中长期宜独立 Worker 或任务队列**

**理由（结合当前实现）：**

1. **Playwright + Chromium**  
   - 镜像体积大，需 **`playwright install chromium`**；在 PaaS 上常需自定义 buildpack 或 Docker。  
   - 对 **CPU/内存** 与 **启动时间** 敏感。

2. **请求耗时**  
   - Agent / 真实多源路径在 **一次用户交互** 内完成 **双站抓取 + 批量分析**，易超过 **常见 HTTP/Serverless 超时**（如 30s–60s）。  
   - Streamlit 会话内 `st.spinner` 可容忍较长等待，但 **多实例 + 同步抓取** 会放大资源争用。

3. **合规与稳定性**  
   - 对第三方站点抓取受 **robots/条款/反爬** 影响；生产上常希望 **限流、重试、隔离**，Worker 更易加策略。

4. **与现有代码的贴合方式（最小改动思路）**  
   - **现阶段最小可上线**：**同一台 Linux VM** 上跑 **Streamlit +（可选）Uvicorn**，抓取仍在 Streamlit 进程触发 — **可工作**，但要接受 **单点、长请求、难水平扩展**。  
   - **稍进阶**：**FastAPI 仅暴露分析与健康检查**；**抓取由 systemd/cron/Celery/RQ 等 Worker** 执行，结果写入共享存储或 DB，UI 轮询/订阅 — **当前仓库尚未实现该队列与存储抽象**，属于后续阶段。

**不推荐**：在未改架构前，将 **Playwright 抓取** 直接塞进 **短时 Serverless 函数** 作为默认路径。

---

## 6. Blocking Issues Before Deployment

以下为 **按当前代码真实状态** 归纳的上线前阻塞或高风险项（不含「建议优化」类）：

1. **无双进程/反代/进程守护的标准化交付物**  
   - 无 Dockerfile / compose / systemd 单元 / 平台 `render.yaml` 等，**生产启动方式依赖人工文档**，易与「必须在 `rental_app` 下启动」的约束冲突。

2. **Playwright 浏览器依赖未纳入自动化安装说明（仓库级）**  
   - `requirements.txt` 仅注释提醒 `playwright install chromium`；**无**一键部署脚本或 CI 步骤时，**新环境必踩坑**。

3. **长耗时、重资源操作跑在 Streamlit 进程内**  
   - 真实多源抓取 + batch 分析 **阻塞** 应用进程；**多用户并发** 时易导致 **线程/进程与浏览器实例** 争用；**无**队列与超时策略的统一配置。

4. **持久化为本地 JSON 文件（`data/listings.json`）**  
   - 路径相对包内 `data/`（`listing_storage.py` 中 `DEFAULT_LISTINGS_PATH`）；**多副本部署** 时若无 **共享卷**，各实例数据 **不一致**；**无备份/迁移** 策略说明。

5. **缺少 `.env.example` 与统一 README**  
   - `RENTALAI_API_URL`、`RENTALAI_USE_LOCAL` 等 **无文档化清单**；运维 **易漏配** 或 **默认指向 127.0.0.1** 导致联调失败。

6. **`area_module.py` 等处的 `area_data.json` 使用方式偏「当前工作目录」**  
   - 与 `module2_scoring._load_area_data`（基于包路径）不一致；**若工作目录非 `rental_app`**，可能出现 **数据文件找不到** 的隐性 bug。

7. **公网暴露 Streamlit 时的安全与认证**  
   - 当前为 **Demo 级** 应用；**无** 登录、RBAC、速率限制；直接挂公网 **不符合** 典型生产安全基线（属产品级阻塞，视上线范围而定）。

8. **第三方站点抓取的法律与稳定性风险**  
   - 非纯技术阻塞，但 **上线前需产品/法务确认**；反爬变化可导致 **功能突然不可用**。

---

## 7. Recommended Production Architecture

### 推荐（**当前项目最小可上线版本**）：**单机全栈（一台 Linux VM）+ 反向代理**

**组成：**

- **一台** 2vCPU+ / 4GB+ RAM 的 Linux 服务器（或等价单容器，若后续自建 Dockerfile）。  
- 同一镜像/环境中：  
  - **Uvicorn**：`api_server:app`（对内或经 nginx 对外 `/api`）。  
  - **Streamlit**：`app_web.py`（经 nginx 对外 `/` 或子路径，需注意 Streamlit 的 baseUrl 配置）。  
- **系统级**：`playwright install chromium`、持久化目录挂载 **`rental_app/data/`**（至少保证 `listings.json` 可写）。  
- **环境变量**：设置 **`RENTALAI_API_URL`** 指向对外可达的 API 基址（若 UI 使用 HTTP 模式）。

**原因：**

- **最少改造**：与现有「Streamlit + 可选 FastAPI + 进程内/同机抓取」一致。  
- **规避** Serverless 超时与 Playwright 冷启动问题。  
- **单写盘** 与当前 **JSON 存储** 模型一致，避免立刻引入 DB。

**不推荐作为「第一步」**：Vercel 静态前端 + Render 无状态 API + 无定制镜像的「默认」Serverless 抓取 — **与当前 Playwright 同步抓取模型冲突**。

**后续演进（非本阶段必做）**：API 与 UI 分离部署 + **抓取 Worker** + 数据库/对象存储替代 `listings.json`。

---

## 8. Next Fixing Priorities

按优先级（建议先做前 5 项）：

1. **在 `rental_app` 增加根级 `README.md`**：写清 **工作目录、`pip install -r requirements.txt`、`playwright install chromium`、双终端启动命令、环境变量表**。  
2. **新增 `.env.example`**：列出 `RENTALAI_API_URL`、`RENTALAI_USE_LOCAL` 及未来可能扩展的存储路径等（仍不强制改业务代码）。  
3. **统一进程守护与监听地址说明**：生产用 `0.0.0.0`、反向代理、HTTPS；避免文档仅写 `127.0.0.1`。  
4. **明确持久化策略**：单实例 + 挂载卷，或 **P8 之后** 迁移存储；在文档中写明 **禁止无共享盘多副本** 写同一 JSON。  
5. **抓取超时与并发**：在后续阶段为 Worker/队列或 Streamlit 侧增加 **可配置超时与并发上限**（当前同步模型易在生产爆资源）。  
6. **收紧 CORS 与公网认证**（若 API 对外）：替换 `allow_origins=["*"]`，并加最小认证或内网访问。  
7. **修正/统一 `area_data.json` 加载路径**（若评分链路依赖）：避免依赖启动 cwd。  
8. **（可选）P8 Phase2** 再引入 **Dockerfile** — 本次审计按要求 **不新增**。

---

## 附录：扫描范围说明

- 已确认 **无** `package.json`、**无** 仓库级 `Dockerfile` / `docker-compose.yml` / `Procfile` / `vercel.json` / `render.yaml` / `railway.json`。  
- 部署相关依赖与入口以 **`rental_app/requirements.txt`**、**`api_server.py`**、**`app_web.py`** 为准。  
- 上级目录 **`python_learning/area_data.json`** 与 **`rental_app/data/area_data.json`** 可能并存，部署时需 **确认引擎实际加载路径**，避免静默空数据。

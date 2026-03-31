# RentalAI

## 项目简介

RentalAI 是一个**本地可跑的租房决策辅助 Demo**：用自然语言描述需求，系统做结构化解析并给出推荐房源列表，同时展示解释说明、风险提示与租/慎/不租建议。你可以收藏房源、对比、把分析快照存进浏览器历史，下次打开继续看。

**默认本地开发**：静态 UI 与 JSON API 由**同一个 FastAPI 进程**提供（无 `npm` 前端工程）。**若拆成 Vercel（静态）+ Render（API）**，见下文「部署说明」与 **`DEPLOYMENT_PLAN.md`**。

当前用户体系为 **localStorage 假登录**（名字/邮箱即可），**不连接真实数据库与鉴权**；收藏与历史按 `user_id` 存在本机浏览器里。

---

## 核心功能（当前版本）

| 功能 | 说明 |
|------|------|
| AI 输入 | 首页一句话描述租房需求，提交后 `POST /api/ai-analyze` |
| 推荐结果 | 结果页展示 `recommendations`、评分等 |
| Explain / risks / decision | 每条推荐含 `explain`、`why_good` / `why_not`、`risks`、`decision` / `decision_reason` |
| 收藏 | 按用户写入 `localStorage` 键 `fav_list_{user_id}` |
| 对比 | `/compare` 对比当前会话推荐结果中的已收藏项 |
| 历史记录 | 结果页「保存本次分析」写入 `analysis_history`；`/history` 列表、`/history-detail` 详情 |
| 本地假登录 | `/login` 输入昵称 → `current_user`；未登录访问受保护页会跳登录 |

---

## 本地运行

### 1. 依赖安装

```bash
cd rental_app
pip install -r requirements.txt
```

若需要使用 Playwright 抓取相关能力（异步任务、`RENTALAI_ZOOPLA_FETCH_MODE=playwright` 等），再执行：

```bash
playwright install chromium
```

**Phase D3（Zoopla 浏览器抓取骨架）**：`scraper/zoopla_scraper.py` 默认 **`RENTALAI_ZOOPLA_FETCH_MODE=requests`**（HTTP + BeautifulSoup）。设为 **`playwright`** 时用 Chromium 打开搜索页再复用同一套 HTML 解析；Playwright 未安装、浏览器未装或页面失败时，统一入口会 **回退到 requests**，仍失败则用 **内置 mock**，`/api/ai-analyze` + `dataset=zoopla` 仍可跑。

探针（验证能否拿到页面 HTML）：

```bash
cd rental_app
python -c "from scraper.zoopla_playwright_scraper import test_zoopla_playwright_probe; print(test_zoopla_playwright_probe({'city':'London'}))"
```

### 2. 环境变量（可选）

**本地 Demo 验收可不创建 `.env`**，默认端口 `8000`、地址 `127.0.0.1`。

如需改端口、调试开关等，可复制模板：

```bash
cp .env.example .env
```

变量说明见仓库内 `.env.example`（`run.py` 会自动加载同目录 `.env`，无需 `python-dotenv`）。

### 3. 启动方式（推荐）

**一个终端** 即可同时提供静态页面与 API：

```bash
cd rental_app
python run.py
```

等价写法：

```bash
cd rental_app
uvicorn api_server:app --host 127.0.0.1 --port 8000
```

默认在浏览器打开：**http://127.0.0.1:8000/**

健康检查：**http://127.0.0.1:8000/health**

> 说明：没有单独的「前端 dev server」；`web_public/` 下的 HTML/CSS/JS 由 FastAPI 挂载静态文件提供。

---

## 主要页面路由（Demo）

| 路径 | 说明 |
|------|------|
| `/login` | 本地假登录 |
| `/` | AI 输入首页（需已登录） |
| `/ai-result` | 需求解析与推荐结果 |
| `/compare` | 收藏房源对比 |
| `/history` | 已保存分析列表 |
| `/history-detail` | 单条历史详情（由列表「查看详情」写入 session 后进入） |
| `/contract-analysis` | Phase 4 合同分析（`summary_view` 展示；见下「本地验证合同分析页」） |

其他（Phase3/异步任务等）：`/result/{task_id}`、`/register` 等仍由服务端提供，详见 `api_server.py`。

### 本地验证合同分析页（Phase 4）

1. 启动：`cd rental_app` → `python run.py`，浏览器打开 **http://127.0.0.1:8000/contract-analysis**（须已登录 Demo，与首页同源）。
2. **文本流程**：点「**填入示例文本**」→「**提交分析**」→ 应出现 loading → 下方「分析结果」各块有内容；`sessionStorage` 键 `rentalai_contract_analysis_last` 可看到完整 JSON。
3. **文件路径流程**（开发）：切换到文件模式 → 展开「开发：服务端路径」→ 点「**填入示例路径（文件模式）**」→「**提交分析**」（路径指向仓库内 `contract_analysis/samples/sample_contract.txt`，仅当 API 进程工作目录能解析该相对路径时成功）。
4. **上传流程**：文件模式 → 选择本地 `.txt`/`.pdf`/`.docx` →「**提交分析**」（multipart 调 `POST /api/contract/analysis/upload`）。
5. 命令行冒烟（仅后端 JSON）：`python scripts/contract_analysis_api_smoke.py`。

---

## 技术说明（简要）

- **后端**：Python 3，**FastAPI** + **Uvicorn**；`web_public/assets` 挂载为 **`/assets`**，各路由返回 `web_public/*.html`。
- **前端**：原生 HTML/CSS/JS，无构建步骤。
- **数据**：Demo 分析结果在 **sessionStorage**（`ai_analyze_last`）；用户与收藏/历史在 **localStorage**。

### 合同分析（Phase 3，可选子模块）

与房源推荐主流程独立，规则引擎在包 **`contract_analysis/`**。最小说明、输入输出、Phase 4 接入建议见 **`contract_analysis/README.md`**；HTTP 入口示例 **`POST /api/contract/phase3/analyze-text`**（另有 Phase B 管线 **`/api/contract/analyze-text`**，勿混淆）。

**Phase 4 最小 HTTP**（`summary_view` + `raw_analysis`）：先启动服务后执行 **`python scripts/contract_analysis_api_smoke.py`**，或打开 **`/contract-analysis`** 用页面内「填入示例文本 / 示例路径」联调；详见上文「本地验证合同分析页」与 **`contract_analysis/README.md`**。

---

## 可选：Streamlit 旧界面

与主站独立，需**另开终端**：

```bash
cd rental_app
streamlit run app_web.py
```

默认 **http://localhost:8501**。与 FastAPI 联调时可在 `.env` 中配置 `RENTALAI_API_URL`（见 `.env.example`）。

---

## 部署说明（Vercel 前端 + Render 后端）

适用：**静态页**部署到 **Vercel**，**FastAPI** 部署到 **Render**；二者分域时浏览器会跨域调用 API。后端 CORS 由 **`ALLOWED_ORIGINS`** 配置（逗号分隔）；未设置时默认为 `*`（本地/开发便利），**生产请在 Render 控制台填入 Vercel 站点 origin**（见 `.env.example`）。

### 1. 前端（Vercel）

| 项 | 值 |
|----|-----|
| 部署目录 | `rental_app/web_public`（仓库根若在上一级则选 `rental_app/web_public`） |
| 构建 | **`npm install && npm run build`**（见 `web_public/package.json`；`build` 运行 `scripts/inject-api-base.mjs`，按环境变量写入各页 `<meta name="rentalai-api-base">`）。未设置 `RENTALAI_API_BASE` 时构建为 no-op，meta 保持空 = 同源。 |
| 路由 | `web_public/vercel.json` 将 `/login`、`/ai-result` 等重写到对应 `.html`，**避免刷新 404** |

**API 根地址（环境变量，推荐）**：在 Vercel Project → Environment Variables（**Build**）设置 **`RENTALAI_API_BASE`** = `https://你的-render-服务.onrender.com`（无尾部斜杠）。兼容别名：`VITE_RENTALAI_API_BASE`、`NEXT_PUBLIC_RENTALAI_API_BASE`、`VITE_API_BASE_URL`（见 `web_public/.env.example`）。

也可在发布前手动编辑 HTML 中的 `<meta name="rentalai-api-base" content="...">`。

`assets/api_config.js` 会设置 `window.RENTALAI_API_BASE` 与 **`window.rentalaiApiUrl(path)`**；`ai_home.js` 通过其请求 **`POST /api/ai/query`**（勿在业务脚本里写死后端域名）。

### 2. 后端（Render）

| 项 | 值 |
|----|-----|
| Root Directory | `rental_app` |
| Build | `pip install -r requirements.txt`（按需加 `&& playwright install chromium`） |
| Start | `python run.py`（与 `Procfile` 一致）；等价可直接 `uvicorn api_server:app --host 0.0.0.0 --port $PORT` |
| Health | `GET /health` → JSON 含 `success`、`service`、`status`（见 `api_server.py`） |

环境变量见 **`.env.example`**；平台会注入 **`PORT`**，`config.py` 已读取。**生产必填建议**：`ALLOWED_ORIGINS`（前端公网 origin）；可选 `RENTALAI_DEBUG=0`。

### 3. 部署后如何测通

1. 浏览器打开 Render 上的 `https://…/health`。
2. 打开 Vercel 站点 `/`，确认已配置 API base（meta 或构建注入）。
3. 输入含地区/邮编的英文需求 → **开始分析** → `/ai-result` 应展示 Query Summary、Market Summary、Top Deals、Recommendation Report。

**书面清单**：**`docs/deployment_checklist.md`**。

**命令行冒烟**（在 `rental_app` 目录，需可访问公网后端）：

```bash
# Windows PowerShell: $env:RENTALAI_API_BASE="https://..."
# bash: export RENTALAI_API_BASE=https://...
python scripts/smoke_test.py https://你的-render.onrender.com
```

更细的步骤与限制见 **`DEPLOYMENT_PLAN.md`**。  
**按表执行上线**：**`LAUNCH_CHECKLIST.md`**。

---

## 部署（同机 / Blueprint 摘要）

同进程或 Blueprint 全栈部署仍可参考仓库根 **`render.yaml`**、`P10_PHASE5_DEPLOYMENT.md`。平台通常注入 `PORT`；生产勿开启 `RENTALAI_RELOAD`。

---

## 说明

- 请勿提交含密钥的 **`.env`**；模板为 **`.env.example`**。
- 项目状态与路线图见同目录 **`PROJECT_STATUS.md`**。
- **分域部署清单**见 **`DEPLOYMENT_PLAN.md`**；**上线执行表**见 **`LAUNCH_CHECKLIST.md`**。

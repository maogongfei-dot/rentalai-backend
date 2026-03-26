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

若需要使用 Playwright 抓取相关能力（异步任务等），再执行：

```bash
playwright install chromium
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

其他（Phase3/异步任务等）：`/result/{task_id}`、`/register` 等仍由服务端提供，详见 `api_server.py`。

---

## 技术说明（简要）

- **后端**：Python 3，**FastAPI** + **Uvicorn**；`web_public/assets` 挂载为 **`/assets`**，各路由返回 `web_public/*.html`。
- **前端**：原生 HTML/CSS/JS，无构建步骤。
- **数据**：Demo 分析结果在 **sessionStorage**（`ai_analyze_last`）；用户与收藏/历史在 **localStorage**。

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

适用：**静态页**部署到 **Vercel**，**FastAPI** 部署到 **Render**；二者分域时浏览器会跨域调用 API（后端已配置宽松 CORS）。

### 1. 前端（Vercel）

| 项 | 值 |
|----|-----|
| 部署目录 | `rental_app/web_public`（仓库若根在 `rental_app` 则填 `web_public`） |
| 构建 | 无需；无 `npm run build` |
| 路由 | 使用 `web_public/vercel.json` 将 `/login`、`/ai-result`、`/history`、`/compare` 等重写到对应 `.html`，**避免刷新 404** |

**API 地址**：在 `web_public/index.html` 中设置

`<meta name="rentalai-api-base" content="https://你的-render-服务.onrender.com">`

（无尾部斜杠；留空则请求相对路径 `/api/ai-analyze`，仅在同源部署时可用。）

脚本 `assets/api_config.js` 会读取该 meta 并写入 `window.RENTALAI_API_BASE`，`ai_home.js` 用其拼接 `POST .../api/ai-analyze`。

### 2. 后端（Render）

| 项 | 值 |
|----|-----|
| Root Directory | `rental_app` |
| Build | `pip install -r requirements.txt`（按需加 `&& playwright install chromium`） |
| Start | `python run.py`（与 `Procfile` 一致） |
| Health | `/health` |

环境变量见 **`.env.example`**；平台会注入 **`PORT`**，`config.py` 已读取。

### 3. 部署后如何测通

1. 浏览器打开 Render 上的 `https://…/health`。
2. 打开 Vercel 站点首页，确认已填 `rentalai-api-base`。
3. 登录（本地假登录）→ 输入需求 → **开始分析** → 应进入结果页并看到推荐数据。

更细的步骤与限制见 **`DEPLOYMENT_PLAN.md`**。

---

## 部署（同机 / Blueprint 摘要）

同进程或 Blueprint 全栈部署仍可参考仓库根 **`render.yaml`**、`P10_PHASE5_DEPLOYMENT.md`。平台通常注入 `PORT`；生产勿开启 `RENTALAI_RELOAD`。

---

## 说明

- 请勿提交含密钥的 **`.env`**；模板为 **`.env.example`**。
- 项目状态与路线图见同目录 **`PROJECT_STATUS.md`**。
- **分域部署清单**见 **`DEPLOYMENT_PLAN.md`**。

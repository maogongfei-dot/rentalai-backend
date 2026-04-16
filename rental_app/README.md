# RentalAI

## README 角色说明（唯一主线）

本文件是当前项目的**唯一主线说明书**。后续开发、启动、排错与路线推进，以本 README 为准。

## 项目边界与入口约定（必须遵守）

### 目录边界

- 主项目目录只有：`rental_app/`
- 后续主开发目标仅围绕 `rental_app/` 内代码展开
- 根目录下的 `main.py`、`app.py`、`modules`、`backend` 等属于历史层/旧层，不作为后续主开发目标

### 启动方式（本地唯一推荐）

```bash
cd rental_app
python run.py
```

- 上述方式是本地开发与验证的唯一推荐入口
- 默认访问：`http://127.0.0.1:8000/`
- 健康检查：`http://127.0.0.1:8000/health`

### 代码入口职责

- `api_server.py`：主后端入口（核心 API + 页面路由挂载）
- `app.py`：部署 shim（兼容部署场景），不是主开发入口
- `app_web.py`：旧的/辅助的 Streamlit UI，不作为当前主产品入口

---

## 当前产品定位

- 产品 = **RentAI（长期租房主系统） + ShortRentAI（短租子板块）**
- ShortRentAI 不是替换 RentAI，而是加在平台内的扩展能力
- 当前优先级仍是把 RentAI 主系统能力闭环做稳，再并行推进 ShortRentAI 子板块

## ShortRentAI 规划

- 当前短租数据重点来源：**SpareRoom**
- 后续支持平台自有房东发布能力
- 房东发布支持素材类型：图片、视频、2D、3D/VR
- 视频看房预约属于后续平台化功能，不在当前最先开发范围

## 信任与核实系统（规划）

该模块定位为平台核心壁垒之一，核心能力包括：

- 房东评分
- 房屋质量评分
- 用户上传图片/文字证据
- 维修频率记录（例如 `monthly` / `quarterly` / `rare`）
- 合同风险与历史问题记录
- 人工审核后再生成最终评价

---

## 执行路线图（v5）

| Phase | 目标 |
|------|------|
| Phase 1 | 项目收口 |
| Phase 2 | RentAI核心闭环稳定 |
| Phase 3 | 用户系统与数据一致性 |
| Phase 4 | 数据层升级 |
| Phase 5 | Explain与决策体验升级 |
| Phase 6 | ShortRentAI子板块 |
| Phase 7 | 信任与人工核实系统 |
| Phase 8 | 平台化扩展 |
| Phase 9 | 上线基础设施 |
| Phase 10 | 高级功能 |

---

## 项目简介

RentalAI 是一个本地可运行的租房决策辅助系统：用自然语言描述需求，系统做结构化解析并给出推荐房源列表，同时展示 Explain、风险提示与租/慎/不租建议。可进行收藏、对比、分析历史回看。

默认本地开发模式为：静态 UI 与 JSON API 由同一个 FastAPI 进程提供（无独立前端 dev server）。

## 核心功能（当前版本）

| 功能 | 说明 |
|------|------|
| AI 输入 | 首页一句话描述租房需求，提交后 `POST /api/ai/query` |
| 推荐结果 | 结果页展示 `recommendations`、评分等 |
| Explain / risks / decision | 每条推荐包含 `explain`、`why_good` / `why_not`、`risks`、`decision` / `decision_reason` |
| 收藏 | 按用户写入 `localStorage` 键 `fav_list_{user_id}` |
| 对比 | `/compare` 对比当前会话推荐结果中的已收藏项 |
| 历史记录 | `/analysis-history`（访客本地；登录用户优先服务端 JSON）；`/history`、`/history-detail` 保留本地手动快照能力 |
| 账户体系 | `/login`、`/register`、`/account`；后端用户落盘 `persistence_users.json` |

---

## 本地运行

一页最短流程（依赖、命令、脚本、访问 URL）：[`LOCAL_RUN.md`](LOCAL_RUN.md)

### 1) 依赖安装

```bash
cd rental_app
pip install -r requirements.txt
```

若需要 Playwright 抓取能力（如 `RENTALAI_ZOOPLA_FETCH_MODE=playwright`），再执行：

```bash
playwright install chromium
```

Zoopla 抓取默认使用 `requests` 模式，可切换 `playwright`；失败时会按既有逻辑回退。

探针（验证是否可拿到页面 HTML）：

```bash
cd rental_app
python -c "from scraper.zoopla_playwright_scraper import test_zoopla_playwright_probe; print(test_zoopla_playwright_probe({'city':'London'}))"
```

### 2) 环境变量（可选）

本地 Demo 可不创建 `.env`，默认端口 `8000`、地址 `127.0.0.1`。如需改端口或调试开关：

```bash
cp .env.example .env
```

`run.py` 会自动加载同目录 `.env`，变量以 `.env.example` 为准。

### 3) 启动（唯一推荐）

```bash
cd rental_app
python run.py
```

等价（调试）写法：

```bash
cd rental_app
uvicorn api_server:app --host 127.0.0.1 --port 8000
```

---

## 主要页面路由（当前 Demo）

| 路径 | 说明 |
|------|------|
| `/` | 首页：房源分析、合同分析、智能入口 |
| `/assistant` | 智能入口（前端本地意图分流 + 跳转预填） |
| `/ai-result` | 需求解析与推荐结果 |
| `/contract-analysis` | 合同分析页（文本/上传） |
| `/compare` | 收藏房源对比 |
| `/analysis-history` | 统一分析历史入口 |
| `/history` | 本地保存历史列表 |
| `/history-detail` | 本地保存历史详情 |
| `/login` | 登录 |
| `/register` | 注册 |
| `/account` | 账户状态页 |

其他路由（如异步任务结果）见 `api_server.py`。

### 本地验证合同分析页

1. 启动：`cd rental_app` → `python run.py`
2. 打开：`http://127.0.0.1:8000/contract-analysis`
3. 文本流程：粘贴文本 → 提交分析，验证结果区块与 `sessionStorage` 键 `rentalai_contract_analysis_last`
4. 上传流程：提交 `.txt`/`.pdf`/`.docx`，验证 `POST /api/contract/analysis/upload`
5. 命令行冒烟：`python scripts/contract_analysis_api_smoke.py`

---

## 技术说明（简要）

- 后端：Python 3 + FastAPI + Uvicorn
- 前端：原生 HTML/CSS/JS（无打包依赖）
- 静态资源：`web_public/assets` 由 FastAPI 挂载
- 数据：Demo 级 `sessionStorage` + `localStorage` + JSON 持久化文件并存

### 用户与历史（当前状态）

- 用户持久化：`data/storage/persistence_users.json`
- 历史持久化：`data/storage/persistence_analysis_history.json`
- 登录态：最小 Bearer session placeholder（非 JWT）
- 已登录用户历史读取：`GET /api/analysis/history/records` 需要 `Authorization: Bearer`
- 已登录分析写入：按 Bearer 解析用户分桶写入（与前端 `userId` 做一致性校验）

---

## 可选：Streamlit 旧界面（非主入口）

`app_web.py` 为旧的/辅助 UI，仅在需要时使用，不作为当前主产品入口。

```bash
cd rental_app
streamlit run app_web.py
```

默认地址 `http://localhost:8501`，可通过 `.env` 的 `RENTALAI_API_URL` 与后端联调。

---

## 部署说明（Vercel 前端 + Render 后端）

适用场景：静态页部署到 Vercel，FastAPI 部署到 Render。分域部署时需正确配置 CORS（`ALLOWED_ORIGINS`）。

### Vercel（前端）

| 项 | 值 |
|----|-----|
| 部署目录 | `rental_app/web_public` |
| 构建 | `npm install && npm run build` |
| 路由重写 | `web_public/vercel.json`（避免刷新 404） |

建议在 Vercel Build 环境变量配置 `RENTALAI_API_BASE`（无尾斜杠）。

### Render（后端）

| 项 | 值 |
|----|-----|
| Root Directory | `rental_app` |
| Build | `pip install -r requirements.txt`（按需加 `playwright install chromium`） |
| Start | `python run.py`（等价 `uvicorn api_server:app --host 0.0.0.0 --port $PORT`） |
| Health | `GET /health` |

部署后最小检查：先测 Render `/health`，再测 Vercel 首页到 `/ai-result` 全链路。

---

## 参考文档

- 本地最短启动：`LOCAL_RUN.md`
- 部署计划：`DEPLOYMENT_PLAN.md`
- 上线清单：`LAUNCH_CHECKLIST.md`
- 部署检查：`DEPLOY_READINESS.md`
- 持久化说明：`persistence/README.md`
- 项目阶段状态：`PROJECT_STATUS.md`

## 备注

- 请勿提交包含密钥的 `.env` 文件
- 以 `.env.example` 作为配置模板

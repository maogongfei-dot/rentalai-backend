# RentalAI

## 1. 项目介绍

RentalAI 用规则与结构化数据帮助评估租房选项：浏览器内 **注册 / 登录** → **输入邮编或房源列表 URL** → 异步 **分析** → **结果页**（分数、Explain、风险）→ 自动 **保存到个人历史**。

## 2. 安装步骤

```bash
cd rental_app
pip install -r requirements.txt
```

若需要使用真实多平台列表抓取（异步任务 `/tasks`），再安装 Chromium：

```bash
playwright install chromium
```

可选：复制环境变量模板并编辑（`run.py` 会自动加载同目录下的 `.env`）：

```bash
cp .env.example .env
```

## 3. 启动方式

**推荐唯一入口（Phase4 产品版）：**

```bash
cd rental_app
python run.py
```

等价命令（高级用户）：

```bash
cd rental_app
uvicorn api_server:app --host 127.0.0.1 --port 8000
```

环境变量（见 `.env.example`）：`RENTALAI_HOST`、`RENTALAI_PORT` 或平台注入的 `PORT`、`RENTALAI_RELOAD`、`RENTALAI_DEBUG`、`RENTALAI_SECRET_KEY`（预留）、`RENTALAI_RECORDS_DB_PATH` 等。

## 4. 访问地址

默认：**http://127.0.0.1:8000/**

健康检查：**http://127.0.0.1:8000/health**

主要页面：

| 路径 | 说明 |
|------|------|
| `/` | 首页（分析入口） |
| `/login` | 登录 |
| `/register` | 注册 |
| `/result/{task_id}` | 分析结果 |
| `/history` | 已保存分析列表 |

## 5. 功能说明

- **分析**：登录后提交邮编或 Rightmove/Zoopla 列表 URL，后台异步抓取并批量评分（耗时取决于网络与 Playwright）。
- **结果页**：展示推荐结论、分数、房源摘要、Explain（pros/cons）、风险与折叠 Debug JSON。
- **历史记录**：结果落库后可在 `/history` 查看；**数据按登录用户隔离**。
- **用户系统**：邮箱 + 密码注册/登录；Bearer token 会话（服务端内存；进程重启需重新登录）。

---

## 进阶：Streamlit 演示界面（可选）

旧版 **`app_web.py`** 仍为可选入口，与 Phase3 静态站独立：

```bash
cd rental_app
streamlit run app_web.py
```

默认 **http://localhost:8501**。与 FastAPI 联调时需另开终端启动 `python run.py`，并配置 `RENTALAI_API_URL`（见 `.env.example`）。

更多部署、抓取脚本与历史设计文档见仓库内 `docs/`、`P8_*.md`、`P9_*.md`、`P10_*.md`。

## Deployment（Phase5 · Render）

**技术栈**：Phase3 公网产品 = **FastAPI + Uvicorn**（`python run.py`），与本地相同命令；平台注入 **`PORT`** 后自动监听 **`0.0.0.0`**。

**推荐平台**：**[Render](https://render.com)**（仓库已含 **`render.yaml`**，Blueprint 部署）。

**关键文件**

| 文件 | 说明 |
|------|------|
| `render.yaml`（仓库根） | 定义 `rentalai-api`（必选，含 `playwright install chromium`）与可选 `rentalai-ui`（Streamlit） |
| `rental_app/run.py` | 启动命令 |
| `rental_app/runtime.txt` | Python 版本 |
| `rental_app/Procfile` | 其他 PaaS 备用：`web: python run.py` |

**环境变量（摘要）**

- 平台自动：**`PORT`**
- 建议生产：**勿开启** `RENTALAI_RELOAD`；`RENTALAI_DEBUG=0`
- 持久化（可选）：`RENTALAI_RECORDS_DB_PATH`、`RENTALAI_TASK_STORE_PATH`（配合 Render Disk）

完整说明与数据风险见 **`P10_PHASE5_DEPLOYMENT.md`**。

**部署后公网入口**：仅 Phase3 时，使用 Render 上 **`rentalai-api`** 服务的 URL（例如 `https://rentalai-api.onrender.com`）即可。

---

## 说明

- Phase3 静态 UI **无** `package.json`；产品入口为 **`python run.py`**。
- 请勿提交含密钥的 **`.env`**；模板为 **`.env.example`**。

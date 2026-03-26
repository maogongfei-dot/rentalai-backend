# RentalAI — 部署方案（Vercel 前端 + Render 后端）

## 1. 推荐架构

| 层 | 平台 | 内容 |
|----|------|------|
| 静态 UI | **Vercel** | 目录 `rental_app/web_public/`（无构建，纯 HTML/CSS/JS） |
| API | **Render** | 目录 `rental_app/`，`python run.py`（FastAPI + Uvicorn） |

本地开发仍为 **单进程** `python run.py`：页面与 `/api/*` 同源，无需配置 API 地址。

## 2. 前端（Vercel）

1. 将本仓库连接 Vercel，**Root Directory** 设为：`rental_app/web_public`（若仓库根就是 `rental_app/` 则填 `web_public`）。
2. **Framework Preset**：Other / 无框架；**Build Command** 留空；**Output** 为根目录（默认）。
3. 仓库内已含 **`web_public/vercel.json`**：把 `/login`、`/ai-result` 等路径重写到对应 `.html`，避免刷新 404。
4. 在 **`index.html`** 的 `<meta name="rentalai-api-base" content="...">` 中填写 **Render 服务根 URL**（无尾部斜杠），例如 `https://rentalai-api.onrender.com`。也可用部署前脚本替换该 `content`，勿提交含密钥的无关内容。

## 3. 后端（Render）

1. 新建 **Web Service**，Root Directory：`rental_app`（与仓库结构一致）。
2. **Build Command**：`pip install -r requirements.txt`（若需 Playwright 抓取：`&& playwright install chromium`）。
3. **Start Command**：`python run.py`（与 `Procfile` 一致；平台注入 `PORT` 时 `config.py` 已读取）。
4. **Health Check Path**：`/health`。
5. 仓库根 **`render.yaml`** 可作为 Blueprint 参考；仅上 API 时可只部署 `rentalai-api` 这一类服务。

## 4. 需要准备的配置项

| 项 | 说明 |
|----|------|
| Render 公网 URL | 填到 Vercel 侧 `rentalai-api-base` meta |
| CORS | 后端已 `allow_origins=["*"]`，跨域 `POST /api/ai-analyze` 可用 |
| 环境变量 | 见 `rental_app/.env.example`；生产勿开 `RENTALAI_RELOAD` |

## 5. 部署后测试清单

1. Render：`GET https://<你的服务>/health` 返回 200。
2. Vercel：打开首页 `/`，能加载 CSS/JS。
3. 首页 meta 已指向 Render 后，登录（本地假登录）→ 输入需求 → **开始分析**，应成功跳转结果页（或报网络/CORS 可排查）。
4. 直接访问 `/login`、`/ai-result`、`/history`、`/compare` 并 **刷新**，应不出现 404。
5. 收藏、历史、对比仍为 **浏览器 localStorage**，换设备或清缓存会丢数据（预期）。

## 6. 当前限制

- **本地假登录**、**localStorage/sessionStorage** 不随账号同步到服务器。
- 前后端分域时，仅 **AI 分析请求** 经 `RENTALAI_API_BASE` 指向 Render；其它 Phase3 的 `/tasks`、`/auth/*` 若仍写死相对路径，需在同域部署或另行改造（本 Demo 主路径为 `/api/ai-analyze`）。

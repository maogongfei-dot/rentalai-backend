# RentalAI 正式上线执行表（Vercel + Render）

> 基于当前仓库真实结构整理，按顺序执行即可。更详细的架构说明见 **`DEPLOYMENT_PLAN.md`**。

---

## 一、前端上线步骤（Vercel）

### 1. 前端项目目录在哪里

- 仓库内路径：**`rental_app/web_public/`**
- 内含：`index.html`、`login.html`、`ai_result.html`、`compare.html`、`history.html`、`history_detail.html`、`assets/`、`vercel.json` 等。

### 2. Vercel 应选择哪个目录（Root Directory）

| 仓库根目录假设 | Vercel「Root Directory」填法 |
|----------------|------------------------------|
| Git 根目录是 **`python_learning`**（含 `rental_app/`） | **`rental_app/web_public`** |
| Git 根目录就是 **`rental_app`** | **`web_public`** |

### 3. Build Command

- **留空** 或 **不填**（无 npm / 无构建脚本）。

### 4. Output Directory

- **留空**（静态文件即输出根；Vercel 以 Root Directory 为站点根目录发布）。

### 5. Framework Preset

- **Other** 或 **Other / No Framework**。

### 6. 已提供的 `vercel.json`（`web_public/vercel.json`）

已将「无 `.html` 后缀的 URL」重写到实际文件，避免直接访问或**刷新**时 404：

| 访问路径 | 实际文件 |
|----------|----------|
| `/login` | `/login.html` |
| `/ai-result` | `/ai_result.html` |
| `/compare` | `/compare.html` |
| `/history` | `/history.html` |
| `/history-detail` | `/history_detail.html` |
| `/register` | `/register.html` |
| `/result/*` | `/result.html` |

根路径 **`/`** 默认对应 **`index.html`**，无需额外 rewrite。

### 7. 路由刷新问题如何处理

- 依赖上述 **`vercel.json` 的 `rewrites`**：用户访问 `/login` 等路径时由平台映射到对应 HTML。
- 部署后务必对下列路径各做一次 **F5 刷新**，确认不 404。

### 8. 前端上线后优先访问测试的页面

在浏览器地址栏依次打开（将 `https://你的项目.vercel.app` 换成真实域名）：

1. **`/login`** — 登录页能打开、样式正常  
2. **`/`** — 首页（未登录可能被 `auth_local.js` 重定向到 `/login`，属预期）  
3. **`/ai-result`** — 刷新不 404（可先不依赖数据）  
4. **`/history`** — 刷新不 404  
5. **`/compare`** — 刷新不 404  

---

## 二、后端上线步骤（Render）

### 1. 后端项目目录在哪里

- **仓库内路径：`rental_app/`**（与 `run.py`、`api_server.py`、`requirements.txt` 同级）。

### 2. Render 新建 Web Service 时 Root Directory

| 仓库根目录假设 | Render「Root Directory」 |
|----------------|----------------------------|
| Git 根为 **`python_learning`** | **`rental_app`** |
| Git 根为 **`rental_app`** | **`.`** 或留空（根即项目） |

### 3. Runtime

- **Python 3**（具体小版本以 Render 可选为准，与本地 `runtime.txt` 一致更佳）。

### 4. Build Command

- 最小：**`pip install -r requirements.txt`**
- 若需异步任务里的 Playwright 抓取（与仓库 `render.yaml` 一致）：  
  **`pip install -r requirements.txt && playwright install chromium`**  
  （首次构建较慢，属正常。）

### 5. Start Command

- **`python run.py`**  
  （与 `Procfile`、`render.yaml` 中 `rentalai-api` 一致；平台会注入 **`PORT`**，项目内 `config.py` 已读取。）

### 6. 依赖文件

- **`requirements.txt`**（位于 `rental_app/requirements.txt`）。

### 7. 健康检查

- **Health Check Path**：**`/health`**

### 8. 后端上线后如何测试 `/api/ai-analyze`

将 **`https://你的服务.onrender.com`** 换成 Render 给出的公网地址（无尾部斜杠）。

**方式 A — 浏览器控制台（需处理 CORS 时可用 curl 代替）**  
在任意页面的开发者工具 Console 中不便直接跨域测，推荐方式 B。

**方式 B — curl（推荐）**

```bash
curl -s -o NUL -w "%{http_code}" -X POST "https://你的服务.onrender.com/api/ai-analyze" ^
  -H "Content-Type: application/json" ^
  -d "{\"raw_user_query\":\"test London studio\"}"
```

期望：HTTP **200**，响应体为 JSON（含 `success` 等字段）。

**方式 C — 等前端配置好 `rentalai-api-base` 后**  
在 Vercel 站点首页提交一句需求，能进入结果页即表示链路打通。

---

## 三、API 地址替换步骤（前后端分域）

### 1. 配置文件在哪里

- **文件**：**`rental_app/web_public/index.html`**
- **位置**：`<head>` 内的 **`<meta name="rentalai-api-base" content="...">`**
- **脚本**：**`rental_app/web_public/assets/api_config.js`** 会读取该 meta，并设置 **`window.RENTALAI_API_BASE`**；**`assets/ai_home.js`** 用其拼接 **`POST {base}/api/ai-analyze`**。

> 仅首页发起 AI 分析请求；其它页面不调用该 API。

### 2. 本地开发用什么地址

- **`content=""`（空）** 即可：与 **`python run.py`** 同源，请求相对路径 **`/api/ai-analyze`**。

### 3. Render 上线后改成什么格式

- **`content` 填 Render 服务根 URL**，**不要**末尾斜杠。  
- 示例：**`https://rentalai-api-xxxx.onrender.com`**

### 4. 在 Vercel 侧「对应」的配置方式

- 本项目**未使用** Vercel 环境变量注入到静态 HTML；**标准做法**是：  
  - 部署前在 **`index.html`** 中写好 `content="https://…"`，或  
  - 用 CI/脚本在构建/发布步骤替换该 meta（若以后增加简单构建再接入）。  
- **不要把密钥写进公开仓库**；API 根地址为公开 URL 可接受。

### 5. 改完后如何验证已连上线上后端

1. 打开 Vercel 站点 **首页**，确认已登录（本地假登录）。  
2. 输入一句租房需求，点 **开始分析**。  
3. 应跳转到 **`/ai-result`**，且能看到结构化字段与推荐列表（或业务上的空结果提示）。  
4. 打开开发者工具 **Network**，选中 **`ai-analyze`** 请求，确认 Request URL 的 host 为 **Render 域名**。

---

## 四、正式上线检查清单

在对外宣传前，逐项勾选：

| # | 检查项 | 说明 |
|---|--------|------|
| 1 | 前端已成功部署 | Vercel 域名可打开，无 5xx |
| 2 | 后端已成功部署 | Render Dashboard 显示 Live；`/health` 200 |
| 3 | API 地址已替换 | `index.html` 中 `rentalai-api-base` 指向 Render 根 URL |
| 4 | 登录页可打开 | `/login` 可访问、刷新不 404 |
| 5 | AI 输入可提交 | 首页提交后进入 `/ai-result` 且无跨域/CORS 报错 |
| 6 | 结果页展示正常 | `raw_user_query`、结构化、推荐、explain/风险/决策等按数据展示 |
| 7 | 收藏 / 历史 / 对比可用 | 功能与本地一致（数据在浏览器存储） |
| 8 | 刷新页面正常 | 对 `/login`、`/`、`/ai-result`、`/history`、`/compare` 分别刷新 |
| 9 | 知悉本地限制 | **localStorage / sessionStorage** 不跨浏览器、不跨设备；**本地假登录**非真实账号体系 |

---

## 五、发布后测试顺序（最小路径）

按顺序执行一轮即可：

1. 打开 **`/login`**  
2. 输入昵称，**进入系统**（本地假登录）  
3. 在首页 **输入一句租房需求**，点 **开始分析**  
4. 在 **结果页** 确认需求、结构化结果、推荐与说明  
5. 对某条房源点 **收藏**  
6. 打开 **`/compare`**，确认收藏房源出现在对比中  
7. 在结果页点 **保存本次分析**  
8. 打开 **`/history`**，点 **查看详情** 进入 **`/history-detail`**  
9. 顶栏点 **退出登录**，确认回到 **`/login`**  
10. **重新登录**（可换昵称新建用户），确认 **收藏与历史** 与上一用户隔离（同一浏览器需注意：换用户后 localStorage 键不同，行为与本地一致）

---

## 六、相关文件索引

| 文件 | 用途 |
|------|------|
| `web_public/vercel.json` | Vercel 路径重写 |
| `web_public/index.html` | `rentalai-api-base` |
| `web_public/assets/api_config.js` | 读取 API base |
| `web_public/assets/ai_home.js` | `POST /api/ai-analyze` |
| `requirements.txt` | Python 依赖 |
| `run.py` / `Procfile` | 后端启动 |
| `DEPLOYMENT_PLAN.md` | 架构与限制补充 |
| `README.md` | 本地运行与部署摘要 |

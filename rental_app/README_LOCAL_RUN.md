# RentalAI — 本地 / Production 预演（Phase 6-B · Step 4）

最小说明；产品细节见 **`README.md`**，部署变量见 **`.env.example`**、**`DEPLOY_READINESS.md`**。

| 项 | 位置 |
|----|------|
| 后端入口 | **`run.py`**、**`api_server.py`**（`uvicorn` + FastAPI **`app`**） |
| 依赖 | **`requirements.txt`**；Python 版本 **`runtime.txt`** |
| 环境模板 | **`.env.example`** → 复制为 **`.env`**（`run.py` / `api_server.py` 自动加载） |

**同源主站**：前端为 **`web_public/`** 静态文件，由 FastAPI 挂载，**无**独立 `npm dev` 服务。

---

## PowerShell 预演顺序（建议）

1. `cd` 到 **`rental_app`**
2. `pip install -r requirements.txt`（首次或依赖变更后）
3. （可选）`Copy-Item .env.example .env`，按需设 **`RENTALAI_ENV=production`**、**`PORT`** 等
4. `.\start_backend.ps1`（或 `python run.py`）
5. 浏览器打开终端打印的地址（默认 **http://127.0.0.1:8000/**）

**仅静态构建 / 分域预演**（可选）：`.\start_frontend.ps1`（会执行 **`npm run build`**；需已装 Node）。同源访问仍以步骤 4 为准。

更短步骤见 **`LOCAL_RUN.md`**。

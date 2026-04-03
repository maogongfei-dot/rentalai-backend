# RentalAI — 本地启动（最短说明 · Phase 6 第 3 步）

面向：**同机**跑通「FastAPI + 静态页 `web_public/`」，便于联调与部署前自检。详细产品说明见 **`README.md`**。

---

## 依赖

- **Python**：见 **`runtime.txt`**（如 `python-3.11.8`）。
- 安装：`cd rental_app` → `pip install -r requirements.txt`
- **可选**：真实抓取 / Playwright 路径 → `playwright install chromium`（见 **`README.md`**）。

**无**独立前端 npm 依赖即可跑主站；仅「分域静态构建」时需要 Node，在 `web_public` 下 `npm run build`（见 **`web_public/.env.example`**）。

---

## 环境变量（可选）

- 可不建 **`.env`**：默认 **http://127.0.0.1:8000/**
- 需要改端口、调试、生产画像等：复制 **`.env.example`** → **`.env`**（`run.py` 会自动加载同目录 `.env`）。

---

## 后端（主产品）

在 **`rental_app`** 目录：

```bash
python run.py
```

亦可 **`python api_server.py`**（与 `run.py` 同样读取 `.env`、绑定 `config` 中的 host/port，文件末尾 `uvicorn.run(app, …)`）。

等价：`uvicorn api_server:app --host <见 config> --port <PORT|RENTALAI_PORT|8000>`

**脚本（任选）**

| 平台 | 文件 | 说明 |
|------|------|------|
| Windows | **`start_local.bat`**（本目录） | 双击或命令行执行 |
| Windows | **`scripts/run_backend.bat`** | 从任意位置调用时仍切到 `rental_app` |
| macOS / Linux | **`scripts/run_backend.sh`** | `bash scripts/run_backend.sh` |

---

## 前端（静态 · 无 `npm run dev`）

- **不单独启动**：与后端**同一进程**提供页面与 `/api/*`。
- 启动后端后浏览器访问：**http://127.0.0.1:8000/**（若改了端口则用对应端口）。
- 健康检查：**/health**

---

## 可选：Streamlit 旧 UI

另开终端，`cd rental_app` → `streamlit run app_web.py`（默认 **http://127.0.0.1:8501**），与主站不同进程；API 根见 **`.env.example`**（`RENTALAI_API_URL` 等）。

---

## 部署前自检（命令）

```bash
cd rental_app
python scripts/contract_analysis_api_smoke.py
```

（可选设 `RENTALAI_API_BASE` 指向你的 API 根。）

更多部署变量与结构见 **`DEPLOY_READINESS.md`**。

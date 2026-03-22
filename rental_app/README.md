# RentalAI（`rental_app`）

租赁决策演示：Streamlit 界面、FastAPI 分析接口、Playwright 列表抓取（Rightmove / Zoopla）与本地 JSON 房源存储。

**运行目录**：请在 **`rental_app`** 下执行本文所有命令（与 `api_server.py`、`app_web.py` 内注释一致），以保证 `import data.*`、`import web_bridge` 等路径正确。

---

## 1. 前置条件

- **Python**：建议 3.10+（与当前开发环境一致即可）
- **系统**：抓取功能需可运行 **Playwright Chromium**（Linux 服务器需安装依赖库，见 [Playwright 文档](https://playwright.dev/python/docs/intro)）

---

## 2. 安装依赖

```bash
cd rental_app
pip install -r requirements.txt
playwright install chromium
```

可选：复制环境变量模板（见下文），在 shell 中 `export` 所需变量，或自行写入进程管理器配置。

```bash
cp .env.example .env
# 编辑 .env 后，在 Linux/macOS 可： set -a && source .env && set +a
```

---

## 3. 环境变量（摘要）

| 变量 | 用途 |
|------|------|
| `RENTALAI_API_URL` | 侧栏关闭「Use local engine」时，Streamlit 请求 FastAPI 的根地址（默认 `http://127.0.0.1:8000`） |
| `RENTALAI_USE_LOCAL` | `1`/`true`/`yes`：单条 **Analyze Property** 走进程内分析，不连 HTTP |
| `RENTALAI_LISTINGS_PATH` | 可选；覆盖默认的 `data/listings.json` 绝对路径（持久化挂载卷时使用） |
| `STREAMLIT_SERVER_*` | 官方 Streamlit 配置（端口、监听地址等） |

完整说明与占位符见 **`.env.example`**。

---

## 4. 启动顺序与本地最小联调

### 4.1 仅界面 + 进程内分析（最常见本地演示）

1. 设置 `RENTALAI_USE_LOCAL=1`（或与侧栏勾选 **Use local engine** 一致）
2. 启动 Streamlit：

```bash
streamlit run app_web.py
```

浏览器默认 **http://localhost:8501**。  
此模式下 **Agent / 真实多平台分析** 仍会在本机启动 **Playwright**（与是否启动 FastAPI 无关）。

### 4.2 界面通过 HTTP 调用分析 API

1. **先** 启动 FastAPI（终端 1）：

```bash
uvicorn api_server:app --host 127.0.0.1 --port 8000
```

2. **再** 启动 Streamlit（终端 2），侧栏关闭 **Use local engine**，并将 **API base URL** 设为 `http://127.0.0.1:8000`（或 `export RENTALAI_API_URL=http://127.0.0.1:8000`）

```bash
streamlit run app_web.py
```

3. **Batch 折叠区** 中「Run batch request」在 **Use local engine 开启** 时会被禁用；需 HTTP batch 时请关闭 local 并确保 API 可达。

### 4.3 抓取模块（不通过 Streamlit）

抓取由 **pipeline / scraper** 在 Python 中调用；调试可用脚本（均在 `rental_app` 下）：

```bash
python scripts/run_rightmove_pipeline.py --limit 3 --no-save
python scripts/run_multi_source_analysis.py --sources rightmove,zoopla --limit 2 --no-save
```

无需单独常驻「抓取服务」进程；生产若要与 Web 解耦，见 **`P8_PHASE1_RUNTIME_ENTRY_GUIDE.md`** 与 **`P8_PHASE1_DEPLOYMENT_AUDIT.md`**。

---

## 5. 健康检查

API 启动后：

```bash
curl -s http://127.0.0.1:8000/health
```

---

## 6. 云端部署（第一版：Render Blueprint）

仓库根目录提供 **`render.yaml`**（若 monorepo 根为 `python_learning/`，文件在该根下，`rootDir: rental_app`）。若 **Git 仓库根就是 `rental_app/`**，请将 `render.yaml` 移入该根并 **删除** 各服务下的 `rootDir: rental_app` 字段，或在 Render 控制台将根目录设为 `rental_app`。

1. 将仓库连接 [Render](https://render.com) 并选择 **Blueprint**，使用上述 `render.yaml`。
2. 首次部署完成后，在 **`rentalai-ui`** 服务中设置环境变量 **`RENTALAI_API_URL`** = `rentalai-api` 的公网 URL（无尾部斜杠）。
3. Playwright 在 **UI 服务构建阶段** 执行 `playwright install chromium`；若构建失败，见 **`P8_PHASE1_DEPLOYMENT_PLAN.md`** 风险与排错。

**Heroku 风格单进程**：`rental_app/Procfile` 默认启动 FastAPI；Streamlit 需 **另起一个应用** 并替换其中 `web:` 行（见文件内注释）。

完整架构、变量映射与顺序：**`P8_PHASE1_DEPLOYMENT_PLAN.md`**。

---

## 7. 更多文档

- **Phase2 · 仅后端部署 Runbook：** **`P8_PHASE2_BACKEND_DEPLOY_RUNBOOK.md`**
- **Phase2 · 仅前端部署 Runbook：** **`P8_PHASE2_FRONTEND_DEPLOY_RUNBOOK.md`**
- **Phase2 · Scraper 部署准备：** **`P8_PHASE2_SCRAPER_DEPLOY_PREP.md`**
- **Phase2 · 整站联调状态：** **`P8_PHASE2_INTEGRATION_STATUS.md`**
- 部署前联调与上线执行清单：**`P8_PHASE1_PREDEPLOY_CHECKLIST.md`**
- 部署方案：**`P8_PHASE1_DEPLOYMENT_PLAN.md`**
- 运行入口汇总：**`P8_PHASE1_RUNTIME_ENTRY_GUIDE.md`**
- 部署审计：**`P8_PHASE1_DEPLOYMENT_AUDIT.md`**
- Web 组件说明：**`web_ui/README.md`**
- 各阶段设计：**`docs/`**

---

## 8. 说明

- **无** `package.json`：前端为 Streamlit，非独立 Node 工程；无 `npm run build` / `npm start`。
- 请勿将含密钥的 **`.env`** 提交到版本库；模板文件为 **`.env.example`**。

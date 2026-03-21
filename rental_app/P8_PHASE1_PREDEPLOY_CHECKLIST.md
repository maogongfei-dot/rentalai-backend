# P8 Phase1 Predeploy Checklist

本文档基于 **Step1–Step3** 产出（审计、运行入口、部署方案、`render.yaml`、`Procfile`）与 **当前仓库真实代码** 做部署前联调核对；**不包含**真实连线上环境或实际点击部署。

**核对基准日期**：与仓库当前状态一致；无 `package.json`（Streamlit 即「前端」运行时）。

---

## 1. Integration Check Summary

| 维度 | 状态 |
|------|------|
| **前后端联调** | **可工作**：Streamlit 通过 `RENTALAI_API_URL` + 侧栏 base URL 请求 FastAPI；路径为根路径拼接 `/analyze`、`/analyze-batch` 等，与 `api_server.py` 路由一致。默认 `RENTALAI_USE_LOCAL=1` 时单条分析不走 HTTP。 |
| **后端 ↔ 抓取/分析桥** | **架构分离**：FastAPI **仅** 暴露分析接口，**不** 在 HTTP 层调用 Playwright。抓取与 `analysis_bridge` 由 **Streamlit 进程**（`real_analysis_service`）触发。部署后「API 服务单独扩缩」**不会**自动带上抓取能力。 |
| **是否适合进入部署执行阶段** | **适合发起首次部署执行**（按 §7 在 Render 等平台操作）；**公网生产级**仍需完成 §6 High 的验证与加固。 |

---

## 2. Frontend → Backend Check

### 已通过项

- `app_web.py` 中 API 根地址来自 **`os.environ.get("RENTALAI_API_URL", "http://127.0.0.1:8000")`**，侧栏 `text_input` 默认与该值一致，**支持部署后改为 https 公网地址**。
- `run_analysis_for_ui` 使用 `url = base.rstrip("/") + path`，路径为 **`/analyze`**、**`/score-breakdown`** 等，与 FastAPI 路由 **无额外前缀**（API 不在子路径 `/api` 下）。
- `requests.post(.../analyze-batch)` 与 `api_server` 的 **`@app.post("/analyze-batch")`** 一致。
- **无前端 build 产物**：Streamlit 运行时即服务，**不存在**「构建后静态资源找不到 API」类问题；仅需保证运行进程能访问公网 API URL。

### 风险项

- **`RENTALAI_USE_LOCAL=1`（render.yaml 默认）** 时，**单条 Analyze / Agent / 真实抓取** 均 **不依赖** `RENTALAI_API_URL`；若运维误以为「设了 API URL 就全自动走公网 API」会产生**理解偏差**。
- 侧栏仍允许用户改成错误 URL；**无**运行时校验 API 是否可达（仅请求失败提示）。
- 注释与 `help` 中仍出现 **`127.0.0.1`** 示例，属文档/UI 提示，**非**硬编码请求目标。

### 需修复项（代码层，本阶段不要求）

- 无 **必须** 为联调而改的代码项。生产建议后续：**CORS 收紧**、**API 鉴权**（属 §6）。

---

## 3. Backend → Scraper / Analysis Check

### 已通过项

- 分析链 **`api_analysis` / `web_bridge`** 不依赖浏览器；FastAPI 容器内 **可不装 Playwright** 即可响应 `/analyze`、`/analyze-batch`。
- `listing_storage` 默认路径基于 **`Path(__file__)`** 解析，**非**写死本机绝对路径；可选 **`RENTALAI_LISTINGS_PATH`** 覆盖。

### 风险项

- **Streamlit 服务** `buildCommand` 含 **`playwright install chromium`**：在 Render 等环境 **可能超时或缺系统库**，导致 **UI 服务构建失败**（部署计划已预警）。
- 抓取依赖 **Chromium + 出站 HTTPS** 访问 Rightmove/Zoopla；目标网络 **封禁、反爬、Captcha** 会导致 **仅在线上复现** 的失败。
- **`area_module.py`** 仍使用相对当前工作目录的 **`area_data.json`**，与 `module2_scoring` 使用的 **`data/area_data.json`** 策略不一致；**工作目录非 `rental_app` 时** 可能静默异常（运行入口指南已说明）。

### 需修复项（本阶段不要求）

- 将抓取改为异步 Worker：**超出** Phase1 范围。
- 统一 `area_data` 路径：**建议** P8 后单独排期；本次仅文档记录。

---

## 4. Environment Variables Check

### 已覆盖变量（与代码/运维一致）

| 变量 | 读取位置 | `.env.example` |
|------|-----------|----------------|
| `RENTALAI_API_URL` | `app_web.py` | ✓ |
| `RENTALAI_USE_LOCAL` | `app_web.py` | ✓ |
| `RENTALAI_LISTINGS_PATH` | `data/storage/listing_storage.py` | ✓ |
| `STREAMLIT_SERVER_*` | Streamlit 官方 | ✓（注释） |
| `PLAYWRIGHT_BROWSERS_PATH` | Playwright 官方 | ✓（注释） |

### 缺失变量（代码未读，但平台会注入）

| 变量 | 说明 |
|------|------|
| **`PORT`** | Render/Heroku 等注入；**`render.yaml` / Procfile 已用 `$PORT`**。应用 Python 代码 **不** `os.environ["PORT"]`，**无需**写入 `.env.example` 为必填，但运维需知 **启动命令依赖平台注入**。 |

### 命名 / 作用域

- **`RENTALAI_*`** 前缀一致；无重复别名。
- FastAPI 服务当前 **无** 自定义 `RENTALAI_*` 读取项，**前后端变量集中在 Streamlit 侧**（符合当前双服务划分）。

---

## 5. Deployment Config Consistency Check

| 检查项 | 结论 |
|--------|------|
| **package.json scripts** | **不适用**：仓库 **无** `package.json`；与 `render.yaml` **无冲突**。 |
| **Python 启动命令** | `render.yaml`：`uvicorn api_server:app --host 0.0.0.0 --port $PORT`、`streamlit run app_web.py --server.port $PORT --server.address 0.0.0.0` 与 **`README.md` / `P8_PHASE1_RUNTIME_ENTRY_GUIDE.md`** 一致（仅 host 从本地 127.0.0.1 改为 0.0.0.0，符合公网）。 |
| **rootDir** | `rootDir: rental_app` 与 **仓库根 = `python_learning`** 的结构一致；若 Git 根仅为 `rental_app`，须 **删除 `rootDir`** 或移动 `render.yaml`（`render.yaml` 顶部注释已说明）。 |
| **buildCommand** | API 服务：`pip install -r requirements.txt` ✓。UI 服务：附加 `playwright install chromium` ✓（与 `requirements.txt` 一致）。 |
| **healthCheckPath** | API：`/health` ✓。UI：`/` ✓（Streamlit 根路径；若平台健康检查过严，可后续改为更稳路径，属 Low）。 |
| **文档 vs 代码** | `api_server.py` 文件头仍为本地 `127.0.0.1` **注释**，与生产 `0.0.0.0` **注释层面不一致**（Low，不影响运行）。 |

---

## 6. Remaining Blocking Issues（按严重度）

### High

1. **UI 服务构建（Playwright Chromium）在目标 PaaS 上未经验证** — 可能导致 **首次部署失败**，需一次真实构建或改用 Docker 运行时。
2. **默认无持久盘** — `listings.json` 在 ephemeral 磁盘上，**实例重建即丢**；生产或长期演示需 **Disk + `RENTALAI_LISTINGS_PATH`**。
3. **公网安全基线不足** — Streamlit/FastAPI **无认证**，CORS **`allow_origins=["*"]`**，**不适合**直接对不可信公众开放。

### Medium

4. **免费档休眠与冷启动** — 首次访问慢；长时间抓取可能逼近 **网关/客户端超时**（依平台而定）。
5. **`RENTALAI_API_URL` 在 Blueprint 中为 `sync: false`** — 若首次创建后漏配，**仅**影响「关 local + HTTP batch/单条」路径。

### Low

6. **注释中的 `127.0.0.1`、localhost** — 易误导运维，但不影响正确配置下的请求。
7. **`area_module.py` 与 cwd** — 非主链路时影响面小，但需统一启动目录或后续修路径。

---

## 7. Go-Live Execution Checklist（可执行顺序）

**适用**：Render + 根目录 `render.yaml` + `rootDir: rental_app`（与 Step3 一致）。

- [ ] **1. 代码与仓库**：确认 Git 远程包含 **`render.yaml`**（在仓库根）与 **`rental_app/`** 下完整代码；若仓库根仅为 `rental_app`，已按注释调整 `rootDir` 或 yaml 位置。
- [ ] **2. Render**：新建 **Blueprint**，选中该仓库与分支，使用 **`render.yaml`** 创建 **`rentalai-api`**、**`rentalai-ui`**。
- [ ] **3. 先观察 API 服务构建**：等待 **`rentalai-api`** build + deploy **成功**；浏览器或使用 `curl` 访问 `https://<rentalai-api>/health`，应返回 JSON `status: ok`。
- [ ] **4. 配置 UI 服务环境变量**：在 **`rentalai-ui`** 将 **`RENTALAI_API_URL`** 设为 **`https://<rentalai-api 主机名>`**（**无**尾部斜杠），与现有 `app_web` 拼接逻辑一致。
- [ ] **5. 观察 UI 服务构建**：确认 **`playwright install chromium`** 完成；若失败，记录日志并参考 Render「Python + Playwright」排错或部署计划中 Docker 备选。
- [ ] **6. 打开 UI 公网 URL**：确认 Streamlit 首页加载。
- [ ] **7. 联调 A（进程内）**：保持 **`RENTALAI_USE_LOCAL=1`**，执行 **Parse → Continue** 或 **Run real multi-source**（小 limit），确认无立即崩溃（抓取可能因网络/反爬失败，属业务风险）。
- [ ] **8. 联调 B（HTTP API）**：侧栏 **关闭** Use local engine，**API base URL** 与 `RENTALAI_API_URL` 一致；执行 **Analyze Property**（合法表单）；再测试 **Run batch request** JSON（若启用）。
- [ ] **9. 可选持久化**：为 **`rentalai-ui`** 添加 **Disk**，设置 **`RENTALAI_LISTINGS_PATH`** 指向挂载目录下文件路径。
- [ ] **10. 最终验证**：刷新页面、二次请求 `/health`、记录 **sources_run / 耗时**（侧栏或 debug caption）供后续优化。

---

## 8. Final Readiness Verdict

**Ready for deployment**

**原因**：已具备 **可执行的 Blueprint**（`render.yaml`）、与代码一致的 **启动命令**、**环境变量模板**（`.env.example`）及 **§7 操作顺序**；**无**缺失的 Python 入口或路由不匹配导致的「无法发起部署」类硬阻塞。

**说明**：§6 **High** 项为 **首次上线后高概率暴露的运维/安全风险**，须在 **公网正式推广前** 逐项验收或加固；不改变「可以按 §7 开始部署执行」的结论。

---

## 附录：本步未执行项（与任务约束一致）

- 未在真实 Render 账户执行部署或联调。
- 未修改 `api_analysis`、Agent 主流程、抓取核心逻辑。
- 未新增 `Dockerfile` / Vercel / Railway 配置。

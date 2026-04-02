# RentalAI

## 项目简介

RentalAI 是一个**本地可跑的租房决策辅助 Demo**：用自然语言描述需求，系统做结构化解析并给出推荐房源列表，同时展示解释说明、风险提示与租/慎/不租建议。你可以收藏房源、对比、把分析快照存进浏览器历史，下次打开继续看。

**默认本地开发**：静态 UI 与 JSON API 由**同一个 FastAPI 进程**提供（无 `npm` 前端工程）。**若拆成 Vercel（静态）+ Render（API）**，见下文「部署说明」与 **`DEPLOYMENT_PLAN.md`**。

**当前用户体系**：**前端会话**（`localStorage`：Bearer + 用户 id/邮箱，或本地演示 `current_user`）与 **Phase 5 第三轮后端 JSON 用户表**（`persistence_users.json`，见 `persistence/README.md`）并存——**`/auth/register` / `/auth/login` / `/auth/me`** 读写后者；收藏与**浏览器内**统一历史仍按 **`userId` / `guest` 分桶**存本机。详见「Phase 5 第二轮」「Phase 5 第三轮」。

### 产品结构（Phase 4 第五轮）

- **首页 `/`** 为统一入口：并列 **房源分析**、**合同分析** 两条主能力（主功能卡片 + 最短引导文案），下方同页延续房源一句话表单。
- **两条主能力**：（1）**房源分析**：一句话需求 → `POST /api/ai/query` → `/ai-result` 推荐与决策；（2）**合同分析**：`/contract-analysis` 粘贴或上传租约 → 条款风险与完整性（`summary_view`）。
- **互通**：顶栏与各页链接可在两条主流程间切换（`web_public/assets/auth_local.js`）；顶栏 **「分析历史」** 指向 **`/analysis-history`**；**「智能入口」** 指向 **`/assistant`**（Phase 4 第七轮）。

**尚未落地的产品增强**（可后续迭代）：历史记录**删除/清空、搜索与筛选**；**云端同步**与**生产级**服务端鉴权（Phase 5 第二轮已为**最小本机账户**，见下文）。智能入口已支持 **前端本地关键词分流 + 跳转预填**（Phase 4 第七轮）。

### 智能入口（Phase 4 第七轮 · 收口）

- **路由**：**`/assistant`**（`web_public/assistant.html`），顶栏与首页主功能区可进入。
- **能力摘要**：**仅前端本地** `assistant_intent.js` 关键词计分（**非 LLM**、**无后端意图编排**）；支持 **`property_analysis`** → 首页房源分析、**`contract_analysis`** → 合同分析页、**`unclear`** → 留在本页 **二选一**；`assistant_prefill.js` **一次性**预填目标页输入框（**不自动提交**）。
- **草稿**：**`sessionStorage.rentalai_assistant_draft`**；意图：**`rentalai_assistant_intent`**（`property_analysis` | `contract_analysis` | `unclear`）。
- **意图识别**：**`web_public/assets/assistant_intent.js`** — `detectUserIntent`、`routeUserQuery`（写入草稿+意图并给出跳转路径）。
- **跳转与预填**：明确 intent 时 **`location.href`**；**`rentalai_assistant_navigate`**（`property`|`contract`）由目标页 `consumeAssistantHandoff` 消费后移除。首页 **`ai_home.js`** 预填 **`#ai-query`**；**`contract_analysis_page.js`** 粘贴模式预填 **`#contract-text`**。
- **预填**：**`web_public/assets/assistant_prefill.js`** — `consumeAssistantHandoff('property'|'contract')`；有正文时预填并显示绿色提示条。
- **当前未做的增强**：真正 **LLM 意图识别**、**多轮追问**、与 **用户/分析历史联动**、云端会话。
- **推荐下一步**（择一）：**用户系统接入**（真实账户与鉴权）→ 或 **历史增强**（与入口/草稿联动）→ 或 **AI 对话式入口升级**（后端编排 + LLM）。本轮不新增后端 AI 编排。

**Phase 4 第七轮（聊天式统一入口）状态**：**阶段完成**（先说需求 → 本地分流 → 跳转预填；unclear 引导与主按钮已收口）。

**Phase 4 第五轮（首页产品化收口）状态**：已完成（统一主入口、双入口卡片、引导文案、主流程互通、文档对齐）。

### Phase 5 第二轮（最小用户账户体验）— **阶段完成**

本轮目标：在**不引入生产级数据库认证中心**的前提下，具备可感知的最小账户体验。

| 能力 | 说明 |
|------|------|
| **Login / Sign Up** | 顶栏 **Login**、**Sign Up** → `/login`、`/register` |
| **登录后状态** | 顶栏展示 **邮箱（或昵称）** + **Logout**；首页 **账户条** 同步 |
| **Logout** | 顶栏与首页 **Logout**，清本会话并回到 guest 历史桶（见 `auth_user_store.js`） |
| **历史分桶** | 未登录 **`guest`**；登录后 **`userId`**。统一历史键 `rentalai_unified_analysis_history_v1__{bucket}`，手动保存键 `analysis_history__{bucket}` |
| **访客提示** | `guest_auth_hint.js`（如结果页）、`history_access_context.js`（历史列表横幅），**不拦截**、不强制登录 |
| **账户页** | **`/account`**：只读展示 auth 状态、邮箱、userId、当前桶与简短说明 |

**当前仍为最小 auth**：Token 存 **`localStorage`**（非 HttpOnly Cookie）；**无**服务端对每个 API 请求的强制用户校验。

**Phase 5 第四轮**已支持已登录用户**服务端 JSON 历史**读写与前端优先展示；**仍非**生产级同步（无强制 token 校验、无多设备合并）。**刻意未在第二轮落地**：刷新令牌、**受保护 API**、多设备一致产品化。

### Phase 5 第三轮（后端 JSON 用户与历史数据基础）— **阶段完成**

本轮目标：在**不引入生产数据库**的前提下，让后端具备**可落盘**的用户与历史数据，供后续「云端历史 / 受保护 API」演进。

| 能力 | 说明 |
|------|------|
| **用户持久化** | `data/storage/persistence_users.json`（`RENTALAI_PERSISTENCE_USERS_JSON`）；字段含 `user_id`、`email`、`password_hash` + `password_hash_algorithm`（当前 `sha256_v1`）、`created_at`（UTC ISO8601） |
| **Register / Login** | **`/auth/register`**、**`/auth/login`**、**`/auth/me`** 经 `user_auth_service` 读写上述 JSON（与旧 SQLite `records_db.users` 的账号**不自动合并**） |
| **服务端历史存储** | `data/storage/persistence_analysis_history.json`（`RENTALAI_PERSISTENCE_ANALYSIS_HISTORY_JSON`） |
| **历史写入** | 房源 **`POST /api/ai/query`**、合同 **`/api/contract/analysis/text`**、**`/file-path`**、**`/upload`** 成功后可追加记录；可选 **`userId`**，缺省 **`guest`**；**Phase 5 第六轮**起已登录写入分桶以 **Bearer** 解析为准 |
| **历史读取** | **`GET /api/analysis/history/records`** + **`Authorization: Bearer`**（**Phase 5 第五轮 Step3**）；`{ success, message, records }`；见 `server_history_api.js`；已登录前端**优先**拉取（见「双模式历史」） |

**仍为 Demo 级**：进程内 Bearer 表、**无** HttpOnly Cookie；**历史读取**须 Bearer（第五轮 Step3）；**历史写入**在第六轮已改为 **有 Bearer 时以 token 用户为分桶**（body `userId` 仅作一致性校验）。

**刻意未在第三轮落地**：PostgreSQL/SQLite 迁移、**bcrypt/Argon2**。第四轮已做前端**双模式读写**；**未**做 guest→user 自动迁移合并、分页与冲突处理（见「Phase 5 第四轮」）。

### Phase 5 第四轮（双模式历史：guest 本地 + 已登录云端优先）— **阶段完成**

本轮以前端与既有 JSON 后端收尾，**不**引入真正 HttpOnly token 校验链、**不**做完整「同步迁移」产品。

| 能力 | 说明 |
|------|------|
| **读 — 未登录** | **`/analysis-history`** 仅读 **`localStorage`** 统一摘要（`guest` 分桶）；`RentalAIAnalysisHistorySource.loadAnalysisHistory` → `mode: local_guest` |
| **读 — 已登录** | 同一页面**优先** `GET /api/analysis/history/records?userId={当前 userId}`；失败则回退本机同桶缓存；横幅与 lead 提示 **local / cloud**（`history_access_context.js`、`analysis_history_page.js`） |
| **写 — 未登录** | 分析成功后 **`RentalAIAnalysisHistoryPersist.persistAnalysisResult`** 写入本地统一摘要（房源/合同） |
| **写 — 已登录** | 同次请求对 **`POST /api/ai/query`**、合同分析接口附带 **`userId`**，由后端 **`analysis_history_writer`** 追加 JSON 行；默认**不再**写本地统一列表，避免与云端列表重复（可选 `alsoWriteLocalBackup`） |
| **时间字段** | 本地与后端均使用 **ISO8601 字符串**（`new Date().toISOString()` / UTC `datetime`），列表展示一致 |

**当前限制**：**读取**已 Bearer 保护；**写入**仍可按 body `userId` 落桶（未与本步对齐）；无分页/搜索；无多设备实时同步；**guest 与 user 桶不自动合并**；云端失败时仅回退本机。

**本轮刻意未做**：历史**写入**全面 token 化；guest 记录**一键迁移**；**分页 / 搜索**；**冲突解决**；**数据库**升级。

**推荐下一步（择一优先）**：**受保护 API（token 与 userId 绑定）** 作为安全基线 → 再 **历史体验增强**（手动刷新、分页、可选本地备份开关）；**数据库升级**在需要多实例/审计/规模时再上。

### Phase 5 第五轮 Step1（最小 session / auth 占位）— **本步完成**

| 能力 | 说明 |
|------|------|
| **存储** | `persistence/auth_session_store.py`：进程内 token→userId，**非** JWT、无过期刷新 |
| **响应** | `POST /auth/register`、`POST /auth/login` 成功时返回 `success`、`message`、`user`、`auth`（含 `token`、`auth_type: session_placeholder`），并保留 `token` / `user_id` / `email` 等兼容字段；失败时含 `auth: null` |
| **前端** | `auth_api.js` 的 `getTokenFromAuthBody` 优先读 `auth.token` |

**本步未做**：HttpOnly、多 worker 共享会话（读取接口已在 Step3 保护）。

### Phase 5 第五轮 Step2（前端保存 auth 状态）— **本步完成**

| 能力 | 说明 |
|------|------|
| **状态** | `loadUserFromStorage()` 含 `isAuthenticated`、`userId`、`email`、`authToken`（同 `rentalai_bearer`）、`authType`（`rentalai_auth_type`，默认 `session_placeholder`） |
| **写入** | 登录/注册成功经 `applySessionFromAuthBody` → `loginUser`；`logoutUser` 清 bearer + authType 与 profile |
| **UI** | 顶栏/首页带「受保护会话」提示；账户页展示 **Auth type**（非 token） |

### Phase 5 第五轮 Step3（history 读取 Bearer 保护）— **本步完成**

| 能力 | 说明 |
|------|------|
| **接口** | `GET /api/analysis/history/records` 须 **`Authorization: Bearer`**；有效 token → `auth_session_store.resolve_user_id` → 列表该用户记录 |
| **query** | `userId` 可选；若提供则须与 token 用户一致，否则 **403**；无 token **401** |
| **前端** | `server_history_api.js` 自动带 Bearer；其它分析接口本轮未改 |

### Phase 5 第五轮 Step4（前端云端历史自动带 token + 提示）— **本步完成**

| 能力 | 说明 |
|------|------|
| **API 层** | `RentalAIServerHistoryApi.getBearerTokenForHistory` + `fetchUserHistory` 统一注入 **`Authorization`**；响应带 `_httpStatus` / `_authError` |
| **source 层** | `loadAnalysisHistory`：guest 不请求；已登录无 token 则 **missing_token** 回退本地；401/403 → **auth_error** |
| **页面** | `#history-cloud-load-hint` 成功绿条；`#history-server-notice` 展示缺失会话/鉴权失败等（不崩页） |

### Phase 5 第五轮 Step5（最小受保护 API — 本轮收口）— **阶段完成**

本轮以「**受保护 API 基础成立**」为目标，**不**落地完整安全体系（无全站鉴权中间件、无生产级密码与会话）。

| 维度 | 说明 |
|------|------|
| **已具备** | `POST /auth/register`、`/auth/login` 返回 **`auth: { token, auth_type: session_placeholder }`** + 兼容字段 **`token`**；前端 **`auth_user_store`** 保存 **`authToken` / `authType`**；**`GET /api/analysis/history/records`** **必须 Bearer**；**`server_history_api` + `analysis_history_source`** 自动带 token 与 guest/cloud 双模式 |
| **会话** | 进程内 **token placeholder**（`auth_session_store`），**非** JWT；**logout** 撤销 token 并清前端 **`rentalai_*`** |
| **未做（第五轮当时）** | **JWT**、过期与 **refresh**、**全接口**强制鉴权、**bcrypt/Argon2**、**DB** 升级（**history 写入保护**见下 **第六轮 Step1**） |
| **推荐下一步（择一）** | **密码 hash / JWT** → 或 **继续产品功能**（分页、迁移 UX）；**数据库升级**在需要持久化与多实例时再做 |

### Phase 5 第六轮 Step1（history 写入 Bearer 对齐）— **本步完成**

| 能力 | 说明 |
|------|------|
| **后端** | `resolve_history_write_user_id`：guest 桶可写；**有 Bearer 时以 token 解析用户为写入分桶**；body **`userId`** 仅校验；否则跳过 JSON 追加，响应含 **`history_write: { success, message }`** |
| **路由** | **`POST /api/ai/query`**、**`/api/contract/analysis/text`**、**`/file-path`**、**`/upload`** |
| **前端** | **`analysis_history_persist.mergeAuthHeadersForFetch`** → **`ai_home.js`**、**`contract_analysis_api.js`** 自动带 **`Authorization`** |

### Phase 5 第六轮 Step2–Step5（前端自动云端保存 + 收尾）— **阶段完成**

本轮以「**登录用户分析成功后自动云端保存成立**」收口，**不**做完整安全体系升级。

| 维度 | 说明 |
|------|------|
| **Step2** | 结果页 **`persistAnalysisResult`** 按 **`history_write`**：云端成功则跳过本地重复摘要；失败回退本机并轻提示；**访客**仅本地 |
| **Step3** | **`persist_analysis_history`** 统一房源/合同落库；**`try_persist_property_analysis_snapshot`** / **`try_persist_contract_analysis_snapshot`** |
| **Step4** | 云端保存双语 **`save-banner`**；**`markCloudHistoryNeedsRefresh`**；**`/analysis-history`** 刷新按钮与 GET **`_t`** cache-bust |
| **Step5** | 文档与行为核对（`persistence/README.md`）、注释与 Step1 表述对齐 |
| **当前具备** | 受保护 **读/写** 依赖 **Bearer + session placeholder**；已登录 **自动** 写入 **`persistence_analysis_history.json`**；guest **仅 localStorage**；分析页与历史页 **最小成功/失败提示** |
| **当前限制** | 非 JWT、无过期策略、JSON 单文件、无云端删除/冲突合并；见 **`persistence/README.md`**「本轮未做」 |
| **推荐下一步（择一）** | **Token 失效统一处理 / 登录引导**（产品体验）→ 或 **云端历史删除/清空**（产品）；**数据库升级**在要多实例/持久会话时再做；**JWT** 属认证体系升级 |

### 统一分析历史（Phase 4 第六轮 + Phase 5 第四轮）

- **入口**：顶栏「分析历史」、首页主功能区与表单下快捷链 → **`/analysis-history`**。
- **存储（双模式）**：**访客**仅 **`localStorage`** 统一摘要（`rentalai_unified_analysis_history_v1__guest`）。**已登录**时列表**优先**服务端 JSON（`persistence_analysis_history.json`），本地键仍可用于回退与可选备份；分桶仍为 `__{userId}`。
- **支持类型**：（1）**房源**：`POST /api/ai/query` 结果（housing）与旧版 `ai_analyze`（legacy）；（2）**合同**：合同分析页成功返回的 `summary_view` 子集。
- **并存**：结果页**手动「保存本次分析」**仍写入 **`analysis_history__{bucket}`**，列表 **`/history`**、详情 **`/history-detail`**（**仅本地**全量快照）；与「最近自动摘要」互补。
- **限制**：访客数据无云端；已登录云端仍为 Demo 级 JSON 文件；换机不自动同步；无冲突合并。
- **Phase 4 第六轮（统一历史 + 可回看）状态**：已完成。**Phase 5 第四轮（双模式读写 + 来源提示）状态**：阶段完成。

---

## 核心功能（当前版本）

| 功能 | 说明 |
|------|------|
| AI 输入 | 首页一句话描述租房需求，提交后 `POST /api/ai/query`（见 `ai_home.js`） |
| 推荐结果 | 结果页展示 `recommendations`、评分等 |
| Explain / risks / decision | 每条推荐含 `explain`、`why_good` / `why_not`、`risks`、`decision` / `decision_reason` |
| 收藏 | 按用户写入 `localStorage` 键 `fav_list_{user_id}` |
| 对比 | `/compare` 对比当前会话推荐结果中的已收藏项 |
| 历史记录 | **统一最近分析** `/analysis-history`（访客仅本地；已登录优先云端 JSON + 来源提示；可展开详情）；**手动保存** `analysis_history__{bucket}` → `/history`、`/history-detail`（本地） |
| 账户与登录 | `/login`、`/register`（后端用户落盘 **`persistence_users.json`**）；顶栏 **Logout**；**`/account`**；未登录访问受保护页会跳 `/login` |

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
| `/login` | 登录（邮箱密码 → Bearer，或「本地演示」） |
| `/register` | 注册（邮箱密码） |
| `/account` | **最小账户页**（会话状态、邮箱、userId、历史分桶说明） |
| `/assistant` | **智能入口 / AI Assistant**（Phase 4 第七轮：自然语言草稿 → `sessionStorage` `rentalai_assistant_draft`） |
| `/` | 首页（**公开**）：**房源分析**、**合同分析** 双主入口 + **智能入口**链至 `/assistant` |
| `/ai-result` | 需求解析与推荐结果 |
| `/compare` | 收藏房源对比 |
| `/analysis-history` | **统一分析历史入口**（Phase 4 第六轮，骨架：房源 / 合同分区） |
| `/history` | 房源分析已保存列表（`localStorage`，可从分析历史进入） |
| `/history-detail` | 单条历史详情（由列表「查看详情」写入 session 后进入） |
| `/contract-analysis` | Phase 4 合同分析（`summary_view` 展示；见下「本地验证合同分析页」） |

首页「主功能」区有简短引导：选房比房、通勤与账单/性价比 → 左卡；条款风险、费用与完整性 → 右卡。

其他（Phase3/异步任务等）：`/result/{task_id}` 等仍由服务端提供，详见 `api_server.py`。

### 本地验证合同分析页（Phase 4）

1. 启动：`cd rental_app` → `python run.py`，浏览器打开 **http://127.0.0.1:8000/contract-analysis**（须已登录 Demo，与首页同源）。
2. **文本流程**：选「**粘贴文本**」→「**填入示例文本**」→「**提交分析**」→ 应出现 loading → 下方「分析结果」各块有内容；`sessionStorage` 键 `rentalai_contract_analysis_last` 可看到完整 JSON。
3. **上传流程**（主入口）：选「**上传文件**」→ 选择本地 `.txt`/`.pdf`/`.docx` →「**提交分析**」（`POST /api/contract/analysis/upload`）；错误应显示在表单下方红色提示区。
4. **文件路径流程**（仅开发）：页面底部「**开发者：显示服务端路径**」或 **`/contract-analysis?dev=1`** → 仍选「上传文件」→ 出现 ``file_path`` 框 → 可点「**填入示例路径（开发）**」再提交（`POST /api/contract/analysis/file-path`；路径须相对 `rental_app` 且进程可读）。
5. 命令行冒烟：`python scripts/contract_analysis_api_smoke.py`（详见 `contract_analysis/README.md`）。

---

## 技术说明（简要）

- **后端**：Python 3，**FastAPI** + **Uvicorn**；`web_public/assets` 挂载为 **`/assets`**，各路由返回 `web_public/*.html`。
- **前端**：原生 HTML/CSS/JS，无构建步骤。
- **数据**：Demo 分析结果在 **sessionStorage**（`ai_analyze_last`）；用户与收藏/历史在 **localStorage**。

### 合同分析（Phase 3，可选子模块）

与房源推荐主流程独立，规则引擎在包 **`contract_analysis/`**。最小说明、输入输出、Phase 4 接入建议见 **`contract_analysis/README.md`**；HTTP 入口示例 **`POST /api/contract/phase3/analyze-text`**（另有 Phase B 管线 **`/api/contract/analyze-text`**，勿混淆）。

**Phase 4 最小 HTTP**（`summary_view` + `raw_analysis`）：先启动服务后执行 **`python scripts/contract_analysis_api_smoke.py`**，或打开 **`/contract-analysis`** 联调（双栏输入/结果、七段卡片、风险等级与条款展开等，见 **`contract_analysis/README.md`**「Phase 4 第四轮：网页产品化展示」）。

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

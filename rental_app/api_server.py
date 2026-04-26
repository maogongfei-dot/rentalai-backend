"""RentalAI **当前主后端入口**（FastAPI 应用定义处）。

本文件聚合**当前主产品**的后端能力：REST/JSON API、静态资源挂载、认证与中间件等，是 FastAPI Web
主线的中心模块。

**入口角色（与 run.py / app.py / app_web.py 区分）**

- **``run.py``：** 本地**推荐**的一键启动入口；典型用法 ``cd rental_app && python run.py``。
- **``api_server.py``（本文件）：** 定义 ASGI ``app``；可直接 ``uvicorn api_server:app`` 运行，也可经
  ``run.py`` 间接拉起（行为以工作目录与路径一致为前提）。
- **``app.py``：** **部署 shim**（供部分平台/导入场景指向 ``app``），**不是**日常主开发入口说明的替代。
- **``app_web.py``：** 旧的 / 辅助 **Streamlit UI**，**不是**当前主产品界面入口。

**产品结构**

- **RentAI：** 长期租房**主系统**。
- **ShortRentAI：** 平台内**短租扩展板块**；**不替代** RentAI，与主系统并行扩展。

**产品线分层（代码内注释约定）**

路由注释区分 **RentAI**（当前实现重心：长租与常规租房分析主干）、**ShortRentAI**（未来扩展锚点）与**平台共用能力**（鉴权、历史、合同等）；仅作协作说明，不改变接口契约。

**其它启动方式（等价前提）**

亦可 ``python api_server.py``（见文件末尾 ``__main__``）、或 ``uvicorn api_server:app``；生产常见
``--host 0.0.0.0 --port $PORT``。需在能正确解析 ``rental_app`` 包路径的工作目录下执行，见下文启动引导。

历史迭代（如 P2 Phase）体现在路由与实现注释中。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# -----------------------------------------------------------------------------
# 启动引导（与 run.py 对齐）
# -----------------------------------------------------------------------------
# 在 import config、web_bridge 等业务包之前：解析 .env，使端口/密钥等与本地 run.py 一致（stdlib 实现，
# 不依赖 python-dotenv）。同时将 cwd 与 sys.path[0] 固定到本仓库的 rental_app 根目录，这样从任意 cwd 执行
# ``uvicorn api_server:app`` 时，相对路径与 ``import web_bridge`` 等行为与 ``cd rental_app && python run.py``
# 保持一致，避免「只改了 run 却没改直接 uvicorn」时的环境差异。
# -----------------------------------------------------------------------------


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "=" not in s:
            continue
        key, _, val = s.partition("=")
        key = key.strip()
        if not key or key in os.environ:
            continue
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        os.environ[key] = val


_ROOT = Path(__file__).resolve().parent
_load_env_file(_ROOT / ".env")
os.chdir(_ROOT)
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import logging
import queue
import re
import time
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import Body, FastAPI, File, Form, Query, Request, UploadFile
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, ValidationError

import threading

from alert_utils import FailureTracker, send_alert
from api_analysis import analyze_batch_request_body, modular_analyze_response
from data.storage.records_db import (
    _DB_PATH as _RECORDS_DB_PATH,
    UI_HISTORY_ANALYSIS_TYPE,
    delete_favorite_record,
    find_reusable_analysis_result,
    init_records_db,
    insert_analysis_record,
    insert_favorite_record,
    list_favorite_records,
    normalize_analysis_input_signature,
)
from persistence.analysis_history_writer import save_analysis
from persistence.history_read_service import (
    clear_public_records_for_user,
    delete_public_record_for_user,
    list_public_records,
)
from persistence.auth_http_helpers import (
    resolve_history_read_user_id,
    resolve_history_write_user_id,
    resolve_user_id_from_auth_header,
)
from persistence.auth_session_store import build_auth_payload, issue_token, resolve_user_id, revoke_token
from persistence.user_auth_service import get_public_user_by_id, register_user, verify_login
from data.explain.rule_explain import (
    build_p10_explain_for_batch_row,
    build_p10_explain_from_msa_result,
    get_representative_batch_row,
)
from data.storage.records_query_service import (
    get_recent_analysis_records,
    get_recent_property_records,
    get_recent_task_records,
    get_task_record_detail,
    get_ui_history_detail,
    get_ui_history_items,
)
from task_store import TaskStore

from api_auth_minimal import MinimalAuthBody, minimal_login_response, minimal_register_response
from config import get_cors_origins
from contract_analysis_api_payload import build_contract_analysis_ui_payload
from contract_analysis_upload_handler import ContractUploadError, analyze_contract_from_upload

logger = logging.getLogger("rentalai.api")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

_api_failures = FailureTracker(threshold=3, source="api-server")
init_records_db()
_task_store = TaskStore()

# 当前主后端 ASGI 应用：新 API、新页面挂载与中间件默认挂在此 ``app`` 上，而不是挂到 app_web.py（Streamlit）。
app = FastAPI(
    title="RentalAI API",
    description="P2 Phase5 — modular endpoints + /analyze-batch (standard recommendations)",
    version="0.6.0",
)

# =========================
# 用户识别逻辑（Phase 3 核心入口）
# =========================
def get_current_user_id(request: Request) -> str:
    """
    获取当前用户ID：
    - 优先使用 Header: X-User-Id（登录用户）
    - 否则返回 'guest'（游客）
    """
    user_id = request.headers.get("X-User-Id")
    if user_id:
        return user_id

    return "guest"

# 主前端静态页根目录：当前主产品 HTML（index、assistant、各功能页）均位于 web_public/，
# 由下述若干 @app.get 路由逐个返回 FileResponse；未在下方映射的路径若需页面应优先加 HTML 至此目录。
_WEB_PUBLIC_DIR = Path(__file__).resolve().parent / "web_public"

_cors_origins, _cors_allow_credentials = get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


_SLOW_REQUEST_THRESHOLD = 5.0  # seconds


@app.middleware("http")
async def _track_request(request: Request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - t0
    endpoint = request.url.path
    if duration >= _SLOW_REQUEST_THRESHOLD:
        logger.warning(
            "[PERF][SLOW] %s %s -> %s in %.3fs (threshold %.1fs)",
            request.method,
            endpoint,
            response.status_code,
            duration,
            _SLOW_REQUEST_THRESHOLD,
        )
        send_alert(
            "Slow request: %s %s took %.1fs" % (request.method, endpoint, duration),
            level="P2",
            source="api-server",
        )
    else:
        logger.info(
            "[PERF] %s %s -> %s in %.3fs",
            request.method,
            endpoint,
            response.status_code,
            duration,
        )
    if response.status_code < 500:
        _api_failures.record_success(endpoint)
    return response


@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception):
    endpoint = request.url.path
    tb = traceback.format_exc()
    logger.error(
        "Unhandled exception on %s %s: %s\n%s",
        request.method,
        endpoint,
        exc,
        tb,
    )
    _api_failures.record_failure(endpoint, str(exc))
    send_alert(
        "500 on %s %s: %s" % (request.method, endpoint, exc),
        level="P1",
        source="api-server",
    )
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": str(exc)},
    )


class AnalyzeRequest(BaseModel):
    """标准分析请求体（各 POST 共用）；未知字段忽略。"""

    model_config = ConfigDict(extra="ignore")

    rent: Optional[Any] = Field(default=None)
    bills_included: Optional[Any] = Field(default=None)
    commute_minutes: Optional[Any] = Field(default=None)
    bedrooms: Optional[Any] = Field(default=None)
    budget: Optional[Any] = Field(default=None)
    postcode: Optional[Any] = Field(default=None)
    area: Optional[Any] = Field(default=None)
    distance: Optional[Any] = Field(default=None)
    target_postcode: Optional[Any] = Field(default=None, description="Optional; Web UI legacy")


def _body_dict(body: AnalyzeRequest) -> dict:
    return body.model_dump(exclude_none=True)


class AuthRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    email: str
    password: str


def _extract_bearer_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        return None
    token = auth[len("Bearer ") :].strip()
    return token or None


def _get_user_id_from_request(request: Request) -> str:
    token = _extract_bearer_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="missing_bearer_token")
    user_id = resolve_user_id(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="invalid_or_expired_token")
    return user_id


def _get_favorite_scope_user_id(request: Request) -> str:
    """
    收藏用户绑定逻辑：
    - 已登录：优先使用 Bearer token 解析出的真实 user_id
    - 未登录：回退到当前游客会话 guest:<session>
    - 若没有可用游客会话，则使用 guest:anonymous

    登录用户与游客收藏不合并。
    """
    token = _extract_bearer_token(request)
    if token:
        uid = resolve_user_id(token)
        if uid:
            return uid

    raw = (request.headers.get("X-Guest-Session") or "").strip()
    if raw:
        compact = "".join(ch for ch in raw if ch.isalnum())[:48]
        if compact:
            return "guest:" + compact

    return "guest:anonymous"


def _get_task_identity(request: Request) -> str:
    """Bearer → real user id; otherwise stable guest id from X-Guest-Session (P10 Phase7)."""
    token = _extract_bearer_token(request)
    if token:
        uid = resolve_user_id(token)
        if uid:
            return uid
    raw = (request.headers.get("X-Guest-Session") or "").strip()
    if raw and re.fullmatch(r"[a-fA-F0-9\-]{8,128}", raw):
        compact = raw.replace("-", "")[:48]
        return "guest:" + compact
    return "guest:anonymous"


def _db_user_id_for_analysis(task_user_id: str | None) -> str | None:
    if not task_user_id:
        return None
    if str(task_user_id).startswith("guest:"):
        return None
    return str(task_user_id)


def _ux_prefs_from_params(params: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k in (
        "property_type",
        "bedrooms",
        "bathrooms",
        "distance_to_centre",
        "safety_preference",
    ):
        if k not in params:
            continue
        v = params.get(k)
        if v is None or v == "":
            continue
        out[k] = v
    return out


def _append_high_safety_note(explain: dict[str, Any], prefs: dict[str, Any]) -> None:
    if not isinstance(explain, dict):
        return
    sp = prefs.get("safety_preference")
    if not (isinstance(sp, str) and sp.strip().lower() == "high"):
        return
    msg = (
        "You selected a high safety preference — independently verify local crime statistics, "
        "policing coverage, and how the area feels at night."
    )
    rf = list(explain.get("risk_flags") or [])
    if msg not in rf:
        rf.append(msg)
    explain["risk_flags"] = rf


# =============================================================================
# HTTP 路由 — 当前主产品清单（只读注释：分组说明产品职责，不改变路由行为）
# 产品线：RentAI 为当前后端实现重心（长租 / 常规租房分析主链）；ShortRentAI 为规划中的短租子板块，
#        以独立注释块标出「未来接入点」。平台级模块（鉴权、历史、合同）对两侧统一服务。
# 阅读顺序：基础设施 → 用户与云历史 → RentAI 房源分析/推荐 → 合同（共用）→ 异步任务与落库 → 收藏/对比
#            → 主前端 HTML（web_public）→ 静态资源挂载
# =============================================================================


# -----------------------------------------------------------------------------
# 基础设施：存活探针与运维观测（非业务功能入口）
# -----------------------------------------------------------------------------
@app.get("/health")
def health():
    return {
        "success": True,
        "service": "rentalai-backend",
        "status": "ok",
        "api_version": "P2-Phase5",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# 内部连续失败计数（告警辅助）；正常主用户看房/分析流程不依赖此接口。
@app.get("/alerts")
def alerts_status():
    """Current consecutive-failure counts per endpoint (resets on success)."""
    return {
        "failure_counts": _api_failures.get_counts(),
        "threshold": _api_failures._threshold,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# -----------------------------------------------------------------------------
# 用户系统：注册 / 登录 / 登出（JSON 用户库 + Bearer 会话；与 web_public 登录页配合）
# 平台共用能力：会话与身份模型服务于 RentAI 与 ShortRentAI 两侧业务，而非单一子板块独占。
# -----------------------------------------------------------------------------
@app.post("/auth/register")
def auth_register(body: AuthRequest):
    """Register into JSON persistence (``persistence_users.json``); response includes legacy token fields."""
    user, err = register_user(body.email, body.password)
    if err:
        status = 409 if "already exists" in err.lower() else 400
        return JSONResponse(
            status_code=status,
            content={
                "success": False,
                "user": None,
                "auth": None,
                "message": err,
                "error": "register_failed",
            },
        )
    token = issue_token(user["user_id"])
    uid = user["user_id"]
    em = user["email"]
    ca = user["created_at"]
    nested = {"userId": uid, "email": em, "created_at": ca}
    return {
        "success": True,
        "message": "Registered successfully.",
        "user": nested,
        "auth": build_auth_payload(token),
        "user_id": uid,
        "email": em,
        "created_at": ca,
        "token": token,
    }


@app.post("/auth/login")
def auth_login(body: AuthRequest):
    """Login against JSON user store; same response shape as before plus success/user/message."""
    user = verify_login(body.email, body.password)
    if user is None:
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "user": None,
                "auth": None,
                "message": "Invalid email or password.",
                "error": "login_failed",
            },
        )
    token = issue_token(user["user_id"])
    uid = user["user_id"]
    em = user["email"]
    ca = user["created_at"]
    nested = {"userId": uid, "email": em, "created_at": ca}
    return {
        "success": True,
        "message": "Logged in successfully.",
        "user": nested,
        "auth": build_auth_payload(token),
        "user_id": uid,
        "email": em,
        "created_at": ca,
        "token": token,
    }


@app.post("/auth/logout")
def auth_logout(request: Request):
    """Invalidate the current bearer token (in-process store)."""
    token = _extract_bearer_token(request)
    if token:
        revoke_token(token)
    return {"ok": True}


def _parse_analysis_history_type_query(raw: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Return (filter property|contract|None, error_message)."""
    if raw is None or not str(raw).strip():
        return None, None
    t = str(raw).strip().lower()
    if t in ("property", "contract"):
        return t, None
    return None, "type must be property or contract"


# -----------------------------------------------------------------------------
# 历史记录 API：服务端 JSON「云历史」（需登录 Bearer；query userId 为旧客户端兼容）
# 平台共用能力：同一套历史读写供 RentAI / ShortRentAI 相关记录复用，具体业务类型由数据字段与查询参数区分。
# -----------------------------------------------------------------------------
@app.get("/api/analysis/history/records")
def api_analysis_history_records(
    request: Request,
    userId: Optional[str] = Query(
        None,
        max_length=128,
        description="Optional legacy; if sent, must match the user id from Bearer token.",
    ),
    record_type: Optional[str] = Query(
        None,
        alias="type",
        description="Optional: property | contract",
    ),
):
    """
    Phase 5 Round3 Step4 + Round5 Step3 — Read server-side JSON analysis history.

    **Scope:** Logged-in callers read history for the Bearer user id; guests read their own
    guest-session bucket (``guest:<session>`` from ``X-Guest-Session``). The two are not merged.
    Optional ``userId`` query must match that effective scope when provided (legacy clients).
    """
    flt, err = _parse_analysis_history_type_query(record_type)
    if err:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": err, "records": []},
        )
    # 历史读取逻辑：
    # - Bearer 存在时，严格读取当前登录用户自己的历史
    # - 无 Bearer 时，读取当前游客会话自己的历史
    # - 登录用户与游客历史不合并
    effective_user_id = resolve_history_read_user_id(request)

    q_uid = str(userId or "").strip()
    if q_uid and q_uid != effective_user_id:
        return JSONResponse(
            status_code=403,
            content={
                "success": False,
                "message": "userId query does not match current history scope.",
                "records": [],
            },
        )
    # 主产品历史列表读取点：
    # 统一读取当前登录用户的云端历史（按 type 可选过滤），供前端历史页拉取后渲染列表与详情展开。
    try:
        records = list_public_records(effective_user_id, record_type=flt, limit=200)
    except Exception as exc:
        logger.exception("analysis history read failed")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(exc), "records": []},
        )
    return {
        "success": True,
        "message": "ok",
        "records": records,
    }


@app.delete("/api/analysis/history/records/{record_id}")
def api_analysis_history_delete_record(request: Request, record_id: str):
    """
    Phase 5 Round7 Step1 — Delete one server-side JSON history row within the current history scope.

    **Scope:** Logged-in callers delete only from their Bearer user bucket; guests only from their
    guest-session bucket. ``record_id`` must belong to that scope; otherwise **404** or **403**.
    """
    # 用户绑定逻辑：
    # 删除时只允许操作当前历史作用域内的数据：
    # - 登录用户删自己的 user_id 桶
    # - 游客删自己的 guest:<session> 桶
    uid_auth = resolve_history_read_user_id(request)
    rid = str(record_id or "").strip()
    if not rid:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "record_id is required."},
        )
    try:
        outcome = delete_public_record_for_user(rid, uid_auth)
    except Exception as exc:
        logger.exception("analysis history delete failed")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(exc)},
        )
    if outcome == "not_found":
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": "Record not found.",
            },
        )
    if outcome == "forbidden":
        return JSONResponse(
            status_code=403,
            content={
                "success": False,
                "message": "You cannot delete this record.",
            },
        )
    return {"success": True, "message": "Deleted."}


@app.delete("/api/analysis/history/clear")
def api_analysis_history_clear(request: Request):
    """
    Phase 5 Round7 Step2 — Remove **all** server-side JSON analysis history rows for the current
    scope only (Bearer user bucket or guest-session bucket). Other users' rows are unchanged.

    Logged-in and guest histories are separate and not merged across login.
    """
    # 历史清空逻辑：
    # 仅清空当前用户自己的历史桶，不影响其他用户 / 其他游客会话
    uid_auth = resolve_history_read_user_id(request)
    try:
        n = clear_public_records_for_user(uid_auth)
    except Exception as exc:
        logger.exception("analysis history clear failed")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(exc)},
        )
    return {
        "success": True,
        "message": "ok",
        "deleted_count": n,
    }


# 当前登录用户摘要（与 token 配套；主流程「登录态」以此为准之一）
@app.get("/auth/me")
def auth_me(request: Request):
    """Resolve bearer token to a minimal public profile (JSON user store)."""
    user_id = _get_user_id_from_request(request)
    user = get_public_user_by_id(user_id)
    if user is None:
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "user": None,
                "message": "Session expired. Please log in again.",
                "error": "invalid_or_expired_token",
            },
        )
    uid = user["user_id"]
    em = user["email"]
    ca = user["created_at"]
    nested = {"userId": uid, "email": em, "created_at": ca}
    return {
        "success": True,
        "message": "ok",
        "user": nested,
        "user_id": uid,
        "email": em,
        "created_at": ca,
    }


# -----------------------------------------------------------------------------
# 测试 / 占位鉴权（内存 mock，不签发持久 token；主产品以 /auth/* 为准，本组非主流程依赖）
# -----------------------------------------------------------------------------
@app.post("/api/auth/minimal/register")
def api_auth_minimal_register(body: MinimalAuthBody):
    """
    Phase 5 Step3：占位注册（内存 mock，与 SQLite /auth/register 独立）。
    响应：{ success, user: { userId, email } | null, message }。
    """
    content, status = minimal_register_response(body)
    return JSONResponse(status_code=status, content=content)


@app.post("/api/auth/minimal/login")
def api_auth_minimal_login(body: MinimalAuthBody):
    """
    Phase 5 Step3：占位登录（内存 mock，不签发 token）。
    响应：{ success, user: { userId, email } | null, message }。
    """
    content, status = minimal_login_response(body)
    return JSONResponse(status_code=status, content=content)


# =============================================================================
# RentAI 主流程 — 房源分析、推荐、市场行情与自然语言编排（长租 / 常规租房为当前默认语义）
# =============================================================================
# 本节路由构成当前**主分析主干**：以长期租赁与常规找房场景为默认输入与数据口径；新增找房域能力优先在本节
# 内迭代，并与前端 `/`、`/assistant`、`/ai-result` 等主流程页对齐。
#
# ----- ShortRentAI future integration point（未来接入点）-----
# 后续可在不替换本条 RentAI 主链的前提下，于此区域相邻位置增加并行路由或在上游编排层做意图分流：
#   · ShortRentAI 为 RentAI 平台内的**短租扩展板块**，**不替代**主系统。
#   · 规划能力包括：SpareRoom 等数据接入；短租 / 合租 / 灵活租期的专用分析或筛选；
#     房东自发布房源；图片 / 视频 / 2D / 3D / VR 等媒体上传与展示；
#     与**信任及人工核实系统**的登记与展示联动。
# 落地前仅以注释维持扩展锚点；**不改变**现有 URL、请求体与响应语义。
# ----- end ShortRentAI future integration point -----
#
# --- 引擎模块化端点（RentAI：单套评分 / 拆解 / 批量；表单 → Module 管线）---
# 辅助 / 非当前主前端默认入口：主 web 交互页默认走 POST /api/ai/query；本组供旧 Streamlit、工具链或表单直连。
@app.post("/analyze")
def analyze(body: AnalyzeRequest = AnalyzeRequest()):
    """全量分析，data 含 score / decision / analysis / user_facing / references / trace 等。"""
    return modular_analyze_response(_body_dict(body), "/analyze")


@app.post("/score-breakdown")
def score_breakdown(body: AnalyzeRequest = AnalyzeRequest()):
    """评分拆解：components、reasons、weighted 因子、explanation_summary。"""
    return modular_analyze_response(_body_dict(body), "/score-breakdown")


@app.post("/risk-check")
def risk_check(body: AnalyzeRequest = AnalyzeRequest()):
    """风险视图：Module3 structured + 决策/引用中的风险相关切片。"""
    return modular_analyze_response(_body_dict(body), "/risk-check")


@app.post("/explain-only")
def explain_only(body: AnalyzeRequest = AnalyzeRequest()):
    """仅解释：user_facing + recommended / concerns / risks / next_steps 列表。"""
    return modular_analyze_response(_body_dict(body), "/explain-only")


# 辅助 / 批量：多属性数组分析；非单用户一句话主前端默认路径。
@app.post("/analyze-batch")
def analyze_batch(body: dict = Body(default_factory=dict)):
    """
    批量分析：`{ \"properties\": [ {...}, ... ] }`。
    逐项复用与 /analyze 相同的引擎；单项失败不拖垮整批。
    """
    return analyze_batch_request_body(body)


# --- 自然语言 → 结构化推荐（RentAI Phase1；可选多数据源 / 多轮）---
# 辅助 / 非主前端默认链路：当前 index.html 主提交通向 POST /api/ai/query；本路由为 raw_user_query 与 Dataset 实验等场景保留。
@app.post("/api/ai-analyze")
def api_ai_analyze(body: dict = Body(default_factory=dict)):
    """
    Phase1：自然语言 → 规则解析 → Module5 排序 → Top 房源。
    请求体 JSON：`{ \"raw_user_query\": \"...\" }`（兼容顶层 `query`）。
    Phase A5：可选 `dataset`: demo | realistic | multi_source（指定时以对应本地样本为主候选池）。
    Phase D2：可选 `dataset`: zoopla（fetch_zoopla → cleaner → 推荐）。
    Phase D5：可选 `dataset`: rightmove | market_combined（同上，Rightmove 或双源合并）。
    Phase C4：可选 `previous_structured_query`、`conversation_id` → 多轮 merge + 内存会话。
    """
    from ai_recommendation_bridge import (
        public_response_payload,
        run_ai_analyze,
        run_ai_analyze_multiturn,
    )

    if not isinstance(body, dict):
        body = {}
    q = (body.get("raw_user_query") or body.get("query") or "").strip()
    if not q:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "empty_query",
                "message": "raw_user_query is required",
            },
        )
    ds = body.get("dataset")
    dataset = None
    if isinstance(ds, str) and ds.strip().lower() in (
        "demo",
        "realistic",
        "multi_source",
        "zoopla",
        "rightmove",
        "market_combined",
    ):
        dataset = ds.strip().lower()
    prev_sq = body.get("previous_structured_query")
    conv_id = body.get("conversation_id")
    use_multiturn = (
        (isinstance(prev_sq, dict) and prev_sq)
        or (isinstance(conv_id, str) and conv_id.strip())
    )
    try:
        if use_multiturn:
            out = run_ai_analyze_multiturn(
                q,
                previous_structured_query=prev_sq if isinstance(prev_sq, dict) else None,
                conversation_id=conv_id if isinstance(conv_id, str) else None,
                dataset=dataset,
            )
        else:
            out = run_ai_analyze(q, dataset=dataset)
        payload = public_response_payload(out)
        return JSONResponse(content=payload)
    except Exception as exc:
        logger.exception("ai-analyze failed")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "server_error", "message": str(exc)},
        )


# --- 市场行情（RentAI：长租市场清单、统计与 deal/explain；短租专用口径可在 ShortRentAI 分流后并列扩展）---
# 辅助：结构化参数的市场查询；非主前端「一句话」默认主链路（主链路为同节的 POST /api/ai/query）。
@app.post("/api/market/combined")
def api_market_combined(body: dict = Body(default_factory=dict)):
    """
    Phase D6：Zoopla + Rightmove 统一合并查询（去重、来源标记、排序）。
    请求体可选：location, area, postcode, min_price, max_price, min_bedrooms, max_bedrooms, limit, sort_by。
    """
    from services.market_combined import get_combined_market_listings

    if not isinstance(body, dict):
        body = {}
    try:
        out = get_combined_market_listings(
            location=body.get("location"),
            area=body.get("area"),
            postcode=body.get("postcode"),
            min_price=body.get("min_price"),
            max_price=body.get("max_price"),
            min_bedrooms=body.get("min_bedrooms"),
            max_bedrooms=body.get("max_bedrooms"),
            limit=body.get("limit"),
            sort_by=body.get("sort_by"),
        )
        return JSONResponse(content=out)
    except Exception as exc:
        logger.exception("market combined failed")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "server_error", "message": str(exc), "errors": {"_": str(exc)}},
        )


# 若无 /api 前缀的重复路径（/market/*）为历史兼容别名，与 /api/market/* 等价。
@app.post("/api/market/insight")
@app.post("/market/insight")
def api_market_insight(body: dict = Body(default_factory=dict)):
    """
    Phase D7：合并房源 + 市场统计 + 摘要 + decision_snapshot（``get_market_analysis_bundle``）。
    请求体与 ``/api/market/combined`` 相同可选字段。
    返回：success, location, insight, summary, decision_snapshot。
    """
    from services.market_insight import get_market_analysis_bundle

    if not isinstance(body, dict):
        body = {}
    try:
        out = get_market_analysis_bundle(
            location=body.get("location"),
            area=body.get("area"),
            postcode=body.get("postcode"),
            min_price=body.get("min_price"),
            max_price=body.get("max_price"),
            min_bedrooms=body.get("min_bedrooms"),
            max_bedrooms=body.get("max_bedrooms"),
            limit=body.get("limit"),
            sort_by=body.get("sort_by"),
        )
        return JSONResponse(content=out)
    except Exception as exc:
        logger.exception("market insight failed")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "server_error", "message": str(exc)},
        )


@app.post("/api/market/deals")
@app.post("/market/deals")
def api_market_deals(body: dict = Body(default_factory=dict)):
    """
    Phase D8：合并房源 → insight → rank_deals → 对 Top deals 附加 ``deal_decision``。
    请求体：与 ``/api/market/combined`` 相同，另可选 ``top_n``（默认 10）。
    返回：top_deals, market_summary, decision_overview。
    """
    from services.deal_engine import build_deal_decision, rank_deals
    from services.market_insight import build_market_summary, get_market_insight

    if not isinstance(body, dict):
        body = {}
    try:
        insight = get_market_insight(
            location=body.get("location"),
            area=body.get("area"),
            postcode=body.get("postcode"),
            min_price=body.get("min_price"),
            max_price=body.get("max_price"),
            min_bedrooms=body.get("min_bedrooms"),
            max_bedrooms=body.get("max_bedrooms"),
            limit=body.get("limit"),
            sort_by=body.get("sort_by"),
        )
        listings = insight.get("listings") or []
        top_n = body.get("top_n", 10)
        try:
            top_n_int = max(1, int(top_n)) if top_n is not None else 10
        except (TypeError, ValueError):
            top_n_int = 10

        ranked = rank_deals(listings, insight, top_n=top_n_int)
        top_deals: list[dict] = []
        for row in ranked["top_deals"]:
            dec = build_deal_decision(row, insight)
            top_deals.append({**row, "deal_decision": dec})

        decision_counts = {"DO": 0, "CAUTION": 0, "AVOID": 0}
        for row in top_deals:
            d = (row.get("deal_decision") or {}).get("decision")
            if d in decision_counts:
                decision_counts[d] += 1

        seen_rf: set[str] = set()
        risk_flag_examples: list[str] = []
        for row in top_deals:
            for rf in (row.get("deal_decision") or {}).get("risk_flags") or []:
                if rf not in seen_rf:
                    seen_rf.add(rf)
                    risk_flag_examples.append(rf)

        decision_overview = {
            "decision_counts": decision_counts,
            "average_score_all": ranked["average_score"],
            "score_distribution": ranked["score_distribution"],
            "top_deal_scores": [float(r.get("deal_score") or 0) for r in top_deals[:5]],
            "risk_flag_examples": risk_flag_examples,
        }

        out = {
            "success": bool(insight.get("success", True)),
            "location": insight.get("location"),
            "query": insight.get("query"),
            "top_deals": top_deals,
            "market_summary": build_market_summary(insight),
            "decision_overview": decision_overview,
        }
        return JSONResponse(content=out)
    except Exception as exc:
        logger.exception("market deals failed")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "server_error", "message": str(exc)},
        )


@app.post("/api/market/explain")
@app.post("/market/explain")
def api_market_explain(body: dict = Body(default_factory=dict)):
    """
    Phase D9：合并房源 → insight → rank_deals → top explanations → ``build_market_recommendation_report``。
    请求体与 ``/api/market/combined`` 相同，另可选 ``top_n``（默认 10）。
    返回：market_summary, top_deals, explanations, recommendation_report。
    """
    from services.explain_engine import build_market_explain_bundle

    if not isinstance(body, dict):
        body = {}
    try:
        top_n = body.get("top_n", 10)
        try:
            top_n_int = max(1, int(top_n)) if top_n is not None else 10
        except (TypeError, ValueError):
            top_n_int = 10

        out = build_market_explain_bundle(
            location=body.get("location"),
            area=body.get("area"),
            postcode=body.get("postcode"),
            min_price=body.get("min_price"),
            max_price=body.get("max_price"),
            min_bedrooms=body.get("min_bedrooms"),
            max_bedrooms=body.get("max_bedrooms"),
            limit=body.get("limit"),
            sort_by=body.get("sort_by"),
            top_n=top_n_int,
        )
        return JSONResponse(content=out)
    except Exception as exc:
        logger.exception("market explain failed")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "server_error", "message": str(exc)},
        )


# -----------------------------------------------------------------------------
# 主产品核心分析 API（与 web_public 主前端一一对应）
# -----------------------------------------------------------------------------
# A. 当前主产品默认分析入口：主交互页（index.html）经 ai_home.js 仅向本路由族提交（首选 POST /api/ai/query）。
# B. 主要承载 RentAI 主流程：长期租房与常规自然语言房源查询编排（run_housing_ai_query）。
# C. ShortRentAI 规划为平台内扩展，宜在本函数或 orchestrator 内做参数与分支扩展，而非另行声明互斥的「全局唯二主 API」。
# D. 短租、合租、灵活租期、SpareRoom 相关需求，可在本层或编排器增加意图识别与数据源路由后再演进，响应契约与产品对齐扩展。
# E. 信任与人工核实系统可在后续于结果对象或并行服务中联动（例如房东评分、房屋问题、维修记录、合同风险摘要），与本入口返回形成组合交付。
# 路由别名：/ai/query、/market/ask 为旧客户端兼容路径，语义与 /api/ai/query 相同。
# -----------------------------------------------------------------------------
@app.post("/api/ai/query")
@app.post("/ai/query")
@app.post("/market/ask")
def api_ai_query(request: Request, body: dict = Body(default_factory=dict)):
    """
    Phase D10：自然语言房源查询编排（``run_housing_ai_query``）。
    请求体：``{ "user_text": "..." }``，兼容 ``query`` 字段。
    可选 ``userId`` / ``user_id``：若带 ``Authorization: Bearer``，历史分桶以 **token 解析用户** 为准（body 仅校验一致）；无 token 时仅写入 ``guest``。
    """
    from services.chat_orchestrator import run_housing_ai_query

    # 步骤一：请求体规范化并提取用户自然语言输入（兼容 query 字段）。
    if not isinstance(body, dict):
        body = {}
    try:
        ut = body.get("user_text") if body.get("user_text") is not None else body.get("query")
        # 步骤二：调用主分析编排引擎，生成推荐与市场维度的结构化结果。
        out = run_housing_ai_query(str(ut or ""))
        # 步骤三：解析可写入服务端分析历史的用户身份（Bearer 与 body 校验）。
        hw = resolve_history_write_user_id(request, body)
        # 主产品历史记录写入点（房源分析）：
        # 在主分析结果生成后写入历史；写入字段覆盖用户输入 input、分析结果 result，
        # 并由持久层补齐 created_at 时间戳，形成可回看链路。
        # 该写入链路属于平台共用能力，同时服务 RentAI 与 ShortRentAI。
        if hw["ok"]:
            try:
                # 步骤四（可选）：将本次运行的输入与结果摘要写入持久化历史，供账户维度回看。
                save_analysis(
                    {
                        "user_id": hw["user_id"],
                        "type": "property",
                        "input": str(ut or ""),
                        "summary": out.get("market_summary")
                        if isinstance(out, dict) and isinstance(out.get("market_summary"), dict)
                        else {},
                        "result": out,
                    }
                )
                print("Saved to cloud:", hw["user_id"])
            except Exception as e:
                print("Cloud save failed:", str(e))
        # 步骤五：封装 HTTP 响应，附带 history_write 元信息供前端展示写入状态。
        if isinstance(out, dict):
            payload = dict(out)
            payload["history_write"] = {
                "success": hw["ok"],
                "message": hw["message"] or ("ok" if hw["ok"] else ""),
            }
            return JSONResponse(content=payload)
        return JSONResponse(
            content={
                "result": out,
                "history_write": {
                    "success": hw["ok"],
                    "message": hw["message"] or ("ok" if hw["ok"] else ""),
                },
            }
        )
    except Exception as exc:
        logger.exception("ai query failed")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "server_error",
                "message": str(exc),
                "errors": {"_": str(exc)},
            },
        )


# =============================================================================
# 合同分析：文本 / 文件 / Phase3 管线并存（平台共用能力，非 RentAI 独占）
# =============================================================================
# 长租与短租合约均可能请求本族接口；web_public 合同页与下列路由共同构成「合同分支」后端。
# ShortRentAI 场景下的租约形态差异，可在 Phase3 层或上游参数中扩展，而不另立互斥入口（除非产品明确要求）。
# =============================================================================
class ContractAnalyzeTextBody(BaseModel):
    """POST /api/contract/analyze-text — 纯文本合同风险扫描（rule-based）。"""

    model_config = ConfigDict(extra="ignore")
    contract_text: str = Field(default="", description="Full or partial tenancy contract text")


# Phase B 轻量规则扫描（旧管线）；与 Phase 3 完整分析并存。产品主展示/Explain 优先走 phase3 与 /api/contract/analysis/*。
@app.post("/api/contract/analyze-text")
def api_contract_analyze_text(body: ContractAnalyzeTextBody = Body(...)):
    """
    合同文本分析入口（Phase B1，根目录 ``contract_text_analyzer``）：与 Phase 3 包 ``contract_analysis`` 区分。
    完整条款/explain/展示层请用 ``POST /api/contract/phase3/analyze-text``；说明见 ``contract_analysis/README.md``。
    """
    from contract_text_analyzer import analyze_contract_text

    ct = (body.contract_text or "").strip()
    if not ct:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "empty_contract_text",
                "message": "contract_text is required and must be non-empty",
            },
        )
    try:
        result = analyze_contract_text(ct)
        return {"ok": True, "result": result}
    except Exception as exc:
        logger.exception("contract analyze-text failed")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": "server_error", "message": str(exc)},
        )


class ContractPhase3AnalyzeBody(BaseModel):
    """POST /api/contract/phase3/analyze-text — Phase 3 合同分析（contract_analysis 包）。"""

    model_config = ConfigDict(extra="ignore")
    contract_text: str = Field(default="", description="Full or partial tenancy contract text")
    monthly_rent: Optional[float] = Field(default=None)
    deposit_amount: Optional[float] = Field(default=None)
    fixed_term_months: Optional[int] = Field(default=None)
    source_type: str = Field(
        default="text",
        description="text | txt | pdf | docx（预留；当前透传至 structured_analysis.meta）",
    )
    source_name: Optional[str] = Field(
        default=None,
        description="Optional file name or label for audit / UI",
    )


# Phase 3 合同分析：前端上传可先抽文本再 POST 本路由；文件路径场景也可在服务端调
# ``contract_analysis.analyze_contract_file_with_explain``（与 Python 入口一致）。详见 ``contract_analysis/README.md``。
@app.post("/api/contract/phase3/analyze-text")
def api_contract_phase3_analyze_text(body: ContractPhase3AnalyzeBody = Body(...)):
    """
    Phase 3 合同分析独立入口；与 ``/api/contract/analyze-text``（Phase B 管线）并存，不影响房源 MVP。

    返回 ``result`` 为两层 + 展示层（与 CLI ``plain_text`` 分段一致；JSON 可完整用于前端卡片）：

    - ``structured_analysis``：summary / risks（含 ``matched_text``、``location_hint``、``risk_category`` 等）/
      **risk_category_summary**（``category`` / ``count`` / ``highest_severity`` / ``short_summary``）/
      **risk_category_groups**（``category`` / ``risks`` 完整列表）/
      **clause_list**（条款级占位列表，``ContractClauseItem``；默认可为空）/
      **clause_risk_map**（条款—风险联动，``ClauseRiskLinkItem`` 列表；由正文重叠/关键词/location_hint 轻量匹配生成；可为空但必须存在）/
      **clause_severity_summary**（条款级风险强度汇总，``ClauseSeverityItem`` 列表；可为空但必须存在）/
      **contract_completeness**（合同完整性检查，``ContractCompletenessResult``；``build_contract_completeness`` 基于关键词强/弱命中）/
      missing_items / recommendations / detected_topics / meta
    - ``explain``：overall_conclusion / key_risk_summary /
      **clause_overview**（``clause_id`` / ``clause_type`` / ``short_clause_preview`` / ``matched_keywords``）/
      **clause_risk_overview**（按条款聚合：``clause_id`` / ``clause_type`` / ``short_clause_preview`` / ``linked_risks``）/
      **clause_severity_overview**（优先关注条款：``clause_id`` / ``clause_type`` / ``severity_score`` / ``highest_severity`` / ``linked_risk_count`` / ``short_clause_preview`` / ``linked_risk_titles``；与 ``clause_severity_summary`` 对齐）/
      **contract_completeness_overview**（单卡：``overall_status`` / ``completeness_score`` / ``missing_core_items`` / ``unclear_items`` / ``short_summary``；与 ``contract_completeness`` 对齐）/
      与结构化层一致的 **risk_category_summary** / **risk_category_groups** /
      **highlighted_risk_clauses**（``risk_title`` / ``severity`` / ``matched_text`` /
      ``location_hint`` / ``short_advice`` / ``risk_category`` / ``risk_code``）/
      missing_clause_summary / action_advice
    - ``presentation``：sections 含 ``title_en``；含 ``kind=clause_overview``、
      ``kind=clause_risk_overview``、
      ``kind=clause_severity_overview``、
      ``kind=contract_completeness_overview``（items 为单元素列表，元素为完整性卡）、
      ``kind=risk_category_summary``、
      ``kind=risk_category_groups``（items 另附 ``risk_titles`` 便于列表展示）、
      ``kind=risk_clauses`` 等；``plain_text`` 与 CLI 报告一致

    ``result`` 同时提供 Phase 4 门面键名（``analysis_result`` / ``explain_result``）与
    旧键名（``structured_analysis`` / ``explain``），内容相同，便于新前端与旧调用兼容。
    """
    from contract_analysis_service import analyze_contract_text

    ct = (body.contract_text or "").strip()
    if not ct:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "empty_contract_text",
                "message": "contract_text is required and must be non-empty",
            },
        )
    try:
        facade = analyze_contract_text(
            contract_text=ct,
            monthly_rent=body.monthly_rent,
            deposit_amount=body.deposit_amount,
            fixed_term_months=body.fixed_term_months,
            source_type=body.source_type,
            source_name=body.source_name,
        )
        result = {
            "analysis_result": facade["analysis_result"],
            "explain_result": facade["explain_result"],
            "presentation": facade.get("presentation"),
            "structured_analysis": facade["analysis_result"],
            "explain": facade["explain_result"],
        }
        lc = facade.get("legal_compliance")
        if lc is not None:
            result["legal_compliance"] = lc
        return {
            "ok": True,
            "engine": "phase3_contract_analysis",
            "result": result,
        }
    except Exception as exc:
        logger.exception("contract phase3 analyze-text failed")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": "server_error", "message": str(exc)},
        )


class ContractAnalysisMetadata(BaseModel):
    """可选元数据（合同分析文本/路径接口共用）。"""

    model_config = ConfigDict(extra="ignore")
    source_name: Optional[str] = Field(
        default=None,
        description="来源标签或原始文件名，写入 analysis_result.meta",
    )
    source_type: str = Field(
        default="text",
        description="text | txt | pdf | docx（写入 meta）",
    )
    monthly_rent: Optional[float] = Field(default=None)
    deposit_amount: Optional[float] = Field(default=None)
    fixed_term_months: Optional[int] = Field(default=None)


class ContractAnalysisTextApiBody(BaseModel):
    """POST /api/contract/analysis/text — Phase 4 最小合同文本分析。"""

    model_config = ConfigDict(extra="ignore")
    contract_text: str = Field(default="", description="合同正文（非空）")
    metadata: Optional[ContractAnalysisMetadata] = Field(
        default=None,
        description="可选：source_name、source_type、月租/押金等",
    )
    userId: Optional[str] = Field(
        default=None,
        description="可选：服务端历史分桶；缺省 guest。兼容字段名 user_id。",
    )
    user_id: Optional[str] = Field(
        default=None,
        description="同 userId（snake_case）。",
    )


class ContractAnalysisFilePathApiBody(BaseModel):
    """POST /api/contract/analysis/file-path — 服务端本地路径（.txt/.pdf/.docx），无 multipart 上传。"""

    model_config = ConfigDict(extra="ignore")
    file_path: str = Field(..., description="服务器可读的绝对路径，或相对于 rental_app 根目录的相对路径")
    metadata: Optional[ContractAnalysisMetadata] = Field(
        default=None,
        description="可选：与文本接口相同；source_type 可被文件扩展名推断覆盖",
    )
    userId: Optional[str] = Field(default=None, description="可选：服务端历史 userId")
    user_id: Optional[str] = Field(default=None, description="同 userId")


def _contract_analysis_metadata_kwargs(meta: Optional[ContractAnalysisMetadata]) -> dict[str, Any]:
    if meta is None:
        return {}
    return {k: v for k, v in meta.model_dump(exclude_none=True).items()}


def _resolve_contract_file_path_for_api(raw: str) -> Path:
    """相对路径相对于 api_server 所在目录（rental_app 根）解析。"""
    p = Path(raw.strip())
    base = Path(__file__).resolve().parent
    if not p.is_absolute():
        p = (base / p).resolve()
    else:
        p = p.resolve()
    return p


@app.post("/api/contract/analysis/text")
def api_contract_analysis_text(request: Request, body: ContractAnalysisTextApiBody = Body(...)):
    """
    Phase 4：合同文本分析（最小接口）。返回 ``result.summary_view``（首屏展示）与
    ``result.raw_analysis``（完整 ``analysis_result`` / ``explain_result`` / ``presentation``）。

    与 ``/api/contract/phase3/analyze-text`` 共用 ``contract_analysis_service``；本路由在 HTTP 层整理形状，
    不重复分析逻辑。Phase 3 兼容路由仍返回扁平 ``analysis_result`` + 旧别名。
    """
    from contract_analysis_service import analyze_contract_text

    ct = (body.contract_text or "").strip()
    if not ct:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "empty_contract_text",
                "message": "contract_text is required and must be non-empty",
            },
        )
    try:
        kw = _contract_analysis_metadata_kwargs(body.metadata)
        facade = analyze_contract_text(contract_text=ct, **kw)
        ui_payload = build_contract_analysis_ui_payload(facade)
        hw = resolve_history_write_user_id(request, body.model_dump())
        # 主产品历史记录写入点（合同分析 /text）：
        # 写入输入文本片段 + 分析结果，时间戳在存储层生成；与房源历史共用统一读取链路。
        if hw["ok"]:
            try:
                save_analysis(
                    {
                        "user_id": hw["user_id"],
                        "type": "contract",
                        "input": ct[:8000],
                        "summary": {},
                        "result": ui_payload,
                    }
                )
                print("Saved to cloud:", hw["user_id"])
            except Exception as e:
                print("Cloud save failed:", str(e))
        return {
            "ok": True,
            "engine": "contract_analysis_v1",
            "result": ui_payload,
            "history_write": {
                "success": hw["ok"],
                "message": hw["message"] or ("ok" if hw["ok"] else ""),
            },
        }
    except Exception as exc:
        logger.exception("contract analysis/text failed")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": "server_error", "message": str(exc)},
        )


@app.post("/api/contract/analysis/file-path")
def api_contract_analysis_file_path(request: Request, body: ContractAnalysisFilePathApiBody = Body(...)):
    """
    Phase 4：按**服务端本地路径**读取合同文件并分析（开发/受信环境）。生产需限制可访问目录。

    返回形状与 ``/api/contract/analysis/text`` 相同（``summary_view`` + ``raw_analysis``）。
    """
    from contract_analysis_service import analyze_contract_file

    raw_fp = (body.file_path or "").strip()
    if not raw_fp:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "empty_file_path",
                "message": "file_path is required",
            },
        )
    path = _resolve_contract_file_path_for_api(raw_fp)
    if not path.is_file():
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "file_not_found",
                "message": f"Not a readable file: {path}",
            },
        )
    try:
        kw = _contract_analysis_metadata_kwargs(body.metadata)
        facade = analyze_contract_file(file_path=path, **kw)
        ui_payload = build_contract_analysis_ui_payload(facade)
        hw = resolve_history_write_user_id(request, body.model_dump())
        # 主产品历史记录写入点（合同分析 /file-path）：
        # 写入输入来源（文件路径片段）+ 结果对象，供统一历史页按用户回看。
        if hw["ok"]:
            try:
                save_analysis(
                    {
                        "user_id": hw["user_id"],
                        "type": "contract",
                        "input": str(path)[:8000],
                        "summary": {},
                        "result": ui_payload,
                    }
                )
                print("Saved to cloud:", hw["user_id"])
            except Exception as e:
                print("Cloud save failed:", str(e))
        return {
            "ok": True,
            "engine": "contract_analysis_v1",
            "result": ui_payload,
            "history_write": {
                "success": hw["ok"],
                "message": hw["message"] or ("ok" if hw["ok"] else ""),
            },
        }
    except Exception as exc:
        logger.exception("contract analysis/file-path failed")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": "server_error", "message": str(exc)},
        )


@app.post("/api/contract/analysis/upload")
async def api_contract_analysis_upload(
    request: Request,
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(default=None),
    userId: Optional[str] = Form(default=None),
):
    """
    Phase 4：multipart 上传合同（``.txt`` / ``.pdf`` / ``.docx``）。

    - 表单字段 ``file``：上传文件（必填）。
    - 表单字段 ``metadata``：可选 JSON 字符串，形状与 ``ContractAnalysisMetadata`` 一致（``source_name``、月租/押金等；``source_type`` 仅当为 ``txt``/``pdf``/``docx`` 时生效，否则按扩展名推断）。
    - 表单字段 ``userId``（可选）：服务端 JSON 历史分桶；缺省为 ``guest``。

    成功响应与 ``POST /api/contract/analysis/text`` 相同：``result.summary_view`` + ``result.raw_analysis``。
    """
    try:
        kw: dict[str, Any] = {}
        if metadata and str(metadata).strip():
            try:
                obj = json.loads(metadata)
                if not isinstance(obj, dict):
                    raise ValueError("metadata must be a JSON object")
                kw = _contract_analysis_metadata_kwargs(ContractAnalysisMetadata(**obj))
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                return JSONResponse(
                    status_code=400,
                    content={"ok": False, "error": "invalid_metadata", "message": str(exc)},
                )
        st = kw.get("source_type")
        if st is not None and str(st).strip().lower() not in ("txt", "pdf", "docx"):
            st = None
        facade = await analyze_contract_from_upload(
            file,
            monthly_rent=kw.get("monthly_rent"),
            deposit_amount=kw.get("deposit_amount"),
            fixed_term_months=kw.get("fixed_term_months"),
            source_type=st,
            source_name=kw.get("source_name"),
        )
        ui_payload = build_contract_analysis_ui_payload(facade)
        hw = resolve_history_write_user_id(request, {"userId": userId} if userId else {})
        # 主产品历史记录写入点（合同分析 /upload）：
        # 写入上传文件名片段 + 分析结果；若无有效登录身份则不会进入账户云历史写入。
        if hw["ok"]:
            try:
                save_analysis(
                    {
                        "user_id": hw["user_id"],
                        "type": "contract",
                        "input": str(file.filename or "")[:8000],
                        "summary": {},
                        "result": ui_payload,
                    }
                )
                print("Saved to cloud:", hw["user_id"])
            except Exception as e:
                print("Cloud save failed:", str(e))
        return {
            "ok": True,
            "engine": "contract_analysis_v1",
            "result": ui_payload,
            "history_write": {
                "success": hw["ok"],
                "message": hw["message"] or ("ok" if hw["ok"] else ""),
            },
        }
    except ContractUploadError as exc:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": exc.code, "message": exc.message},
        )
    except ValueError as exc:
        logger.warning("contract analysis upload analyze failed: %s", exc)
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "analyze_failed", "message": str(exc)},
        )
    except Exception as exc:
        logger.exception("contract analysis upload failed")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": "server_error", "message": str(exc)},
        )


_CONTRACT_PDF_MAX_BYTES = max(1, int(os.environ.get("RENTALAI_CONTRACT_PDF_MAX_BYTES", str(15 * 1024 * 1024))))
_CONTRACT_PREVIEW_CHARS = max(100, int(os.environ.get("RENTALAI_CONTRACT_PREVIEW_CHARS", "500")))


@app.post("/api/contract/analyze-pdf")
async def api_contract_analyze_pdf(file: UploadFile | None = File(None)):
    """
    合同 PDF 分析（Phase B5）：multipart 字段名 file → 抽取文本 → 复用 analyze_contract_text。
    """
    from contract_pdf_extract import extract_text_from_pdf_bytes
    from contract_text_analyzer import analyze_contract_text

    # 接口接收文件逻辑：无文件或空文件名
    if file is None or not (file.filename or "").strip():
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "no_file",
                "message": "multipart field 'file' with a PDF is required",
            },
        )

    filename = (file.filename or "").strip()
    if not filename.lower().endswith(".pdf"):
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "invalid_file_type",
                "message": "only .pdf files are accepted",
            },
        )

    try:
        raw = await file.read()
    except Exception as exc:
        logger.exception("contract analyze-pdf read failed")
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "read_failed", "message": str(exc)},
        )

    if not raw:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "empty_upload",
                "message": "uploaded file is empty",
            },
        )

    if len(raw) > _CONTRACT_PDF_MAX_BYTES:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "file_too_large",
                "message": "PDF exceeds maximum size (%s bytes)" % _CONTRACT_PDF_MAX_BYTES,
            },
        )

    # PDF 文本提取：逐页 extract_text，失败页跳过；整份无法打开则 pdf_extract_failed
    try:
        extracted = extract_text_from_pdf_bytes(raw)
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "pdf_extract_failed",
                "message": str(exc),
            },
        )
    except Exception as exc:
        logger.exception("contract analyze-pdf extract failed")
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "pdf_extract_failed",
                "message": str(exc),
            },
        )

    # 错误处理：无可提取文本（常见于扫描版/纯图 PDF）
    if not (extracted or "").strip():
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "empty_extracted_text",
                "message": "no extractable text in PDF (may be scanned/image-only; OCR not supported in this phase)",
            },
        )

    # 复用与 POST /api/contract/analyze-text 相同的 analyze_contract_text 引擎
    try:
        analysis = analyze_contract_text(extracted)
    except Exception as exc:
        logger.exception("contract analyze-pdf analysis failed")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": "server_error", "message": str(exc)},
        )

    preview = extracted[:_CONTRACT_PREVIEW_CHARS]
    if len(extracted) > _CONTRACT_PREVIEW_CHARS:
        preview = preview + "…"

    return {
        "ok": True,
        "result": {
            "source_type": "pdf",
            "filename": filename,
            "extracted_text_preview": preview,
            "analysis": analysis,
        },
    }


_HOUSE_IMPORT_MAX_BYTES = max(1, int(os.environ.get("RENTALAI_HOUSE_IMPORT_MAX_BYTES", str(5 * 1024 * 1024))))


# 房源数据批量导入（JSON/CSV）；运营/调试辅助为主，主用户链路可不经过此接口。
@app.post("/api/houses/import")
async def api_houses_import(
    file: UploadFile | None = File(None),
    source: str = Form("generic"),
):
    """
    Phase A4：multipart 字段 file（.json / .csv）+ 可选 source → 解析 → clean_and_normalize → 摘要与预览（不落库）。
    """
    from house_import_service import import_house_records

    if file is None or not (file.filename or "").strip():
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "no_file",
                "message": "multipart field 'file' with a .json or .csv is required",
            },
        )

    filename = (file.filename or "").strip()
    ext = Path(filename).suffix.lower()
    if ext not in (".json", ".csv"):
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "unsupported_file_type",
                "message": "only .json and .csv files are accepted",
            },
        )

    try:
        raw = await file.read()
    except Exception as exc:
        logger.exception("houses import read failed")
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "read_failed", "message": str(exc)},
        )

    if not raw:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "empty_upload",
                "message": "uploaded file is empty",
            },
        )

    if len(raw) > _HOUSE_IMPORT_MAX_BYTES:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "file_too_large",
                "message": "file exceeds maximum size (%s bytes)" % _HOUSE_IMPORT_MAX_BYTES,
            },
        )

    src = (source or "generic").strip() or "generic"
    out = import_house_records(raw, filename=filename, source=src)
    if not out.get("ok"):
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": out.get("error", "import_failed"),
                "message": out.get("message", "import failed"),
            },
        )

    return {"ok": True, "result": out["result"]}


# =============================================================================
# 异步任务与持久化记录：多源抓取长任务、SQLite 任务/分析/收藏等（与 Streamlit / 后台 pilot 共用）
# =============================================================================

# ---------------------------------------------------------------------------
# Async task endpoints (P9 Phase3 skeleton)
# ---------------------------------------------------------------------------

class AnalyzeRealRequest(BaseModel):
    """Request body for POST /tasks — multi-source scrape + analyze."""

    model_config = ConfigDict(extra="ignore")

    sources: Optional[list[str]] = Field(default=None)
    limit_per_source: int = Field(default=10, ge=1, le=50)
    budget: Optional[float] = Field(default=None)
    target_postcode: Optional[str] = Field(default=None)
    listing_url: Optional[str] = Field(
        default=None,
        description="Optional list/search URL; when set, passed as scraper search_url (host hints source).",
    )
    property_type: Optional[str] = Field(
        default=None,
        description="flat | apartment | house | studio | other",
    )
    bedrooms: Optional[str] = Field(default=None, description="1, 2, 3, or 4+")
    bathrooms: Optional[float] = Field(default=None, ge=0.5, le=20)
    distance_to_centre: Optional[str] = Field(
        default=None,
        description="1 | 3 | 5 | any (miles, optional soft filter when listing has distance)",
    )
    safety_preference: Optional[str] = Field(
        default=None,
        description="high | medium | low (notes only; no listing-level safety data)",
    )
    headless: bool = Field(default=True)
    persist: bool = Field(default=True)


_MAX_CONCURRENT_TASKS = max(1, int(os.environ.get("MAX_CONCURRENT_TASKS", "2")))
_ANALYSIS_CACHE_ENABLED = os.environ.get("RENTALAI_ANALYSIS_CACHE_ENABLED", "1").strip().lower() not in (
    "0",
    "false",
    "no",
)
_ANALYSIS_CACHE_MAX_AGE_SECONDS = max(1, int(os.environ.get("RENTALAI_ANALYSIS_CACHE_MAX_AGE_SECONDS", "1800")))
_TASK_QUEUE: "queue.Queue[tuple[str, dict[str, Any]]]" = queue.Queue()
_WORKERS_STARTED = False
_WORKERS_LOCK = threading.Lock()


def _task_worker_loop(worker_idx: int) -> None:
    """Background worker: consume queued tasks and execute them."""
    while True:
        task_id, params = _TASK_QUEUE.get()
        try:
            logger.info(
                "[TASK][worker-%s] dequeued %s (queue_size=%s)",
                worker_idx,
                task_id,
                _TASK_QUEUE.qsize(),
            )
            _run_analysis_task(task_id, params)
        finally:
            _TASK_QUEUE.task_done()


def _task_scrape_query_and_sources(params: dict[str, Any]) -> tuple[dict[str, Any], list[str] | None]:
    """Build scraper query + optional source override when a listing/search URL is provided."""
    query: dict[str, Any] = {"headless": bool(params.get("headless", True))}
    sources: list[str] | None = params.get("sources")
    listing_url = (params.get("listing_url") or "").strip()
    if listing_url:
        query["search_url"] = listing_url
        if sources is None:
            low = listing_url.lower()
            sources = ["zoopla"] if "zoopla" in low else ["rightmove"]
    return query, sources


def _start_task_workers_once() -> None:
    global _WORKERS_STARTED
    with _WORKERS_LOCK:
        if _WORKERS_STARTED:
            return
        for i in range(_MAX_CONCURRENT_TASKS):
            threading.Thread(
                target=_task_worker_loop,
                args=(i + 1,),
                daemon=True,
                name="rentalai-task-worker-%s" % (i + 1),
            ).start()
        _WORKERS_STARTED = True
    logger.info("[TASK] started %s worker(s); max concurrent=%s", _MAX_CONCURRENT_TASKS, _MAX_CONCURRENT_TASKS)


def _run_analysis_task(task_id: str, params: dict[str, Any]) -> None:
    """Background thread target: runs multi-source analysis and updates the task store."""
    logger.info("[TASK] %s started execution", task_id)
    _task_store.mark_running(task_id, stage="scraping")
    t0 = time.perf_counter()
    prefs = _ux_prefs_from_params(params)
    analysis_input = normalize_analysis_input_signature({
        "sources": params.get("sources"),
        "limit_per_source": params.get("limit_per_source"),
        "budget": params.get("budget"),
        "target_postcode": params.get("target_postcode"),
        "listing_url": (params.get("listing_url") or "").strip() or None,
        **prefs,
    })
    rec = _task_store.get(task_id)
    user_id = rec.user_id if rec else None
    db_user_id = _db_user_id_for_analysis(user_id)
    if _ANALYSIS_CACHE_ENABLED:
        cached_result = find_reusable_analysis_result(
            analysis_type="multi_source_analysis",
            input_summary=analysis_input,
            user_id=db_user_id,
            max_age_seconds=_ANALYSIS_CACHE_MAX_AGE_SECONDS,
        )
        if isinstance(cached_result, dict):
            degraded = bool(cached_result.get("degraded"))
            out = dict(cached_result)
            out["_cache"] = {"hit": True, "source": "analysis_records"}
            _ex_cache = build_p10_explain_from_msa_result(cached_result)
            _append_high_safety_note(_ex_cache, prefs)
            out["p10_explain"] = _ex_cache
            out["representative_row"] = get_representative_batch_row(cached_result)
            _task_store.mark_success(task_id, out, degraded=degraded, elapsed=0.0)
            try:
                _rs_cache = {
                    "summary": {
                        "cache_hit": True,
                        "cacheable": True,
                        "success": True,
                        "degraded": degraded,
                        "sources_run": cached_result.get("sources_run") or [],
                        "aggregated_unique_count": cached_result.get("aggregated_unique_count"),
                        "total_analyzed_count": cached_result.get("total_analyzed_count"),
                    },
                    "reusable_result": cached_result,
                    "p10_explain": _ex_cache,
                }
                insert_analysis_record(
                    analysis_type="multi_source_analysis",
                    input_summary=analysis_input,
                    result_summary=_rs_cache,
                    source="cache_hit",
                    user_id=db_user_id,
                    explain_summary=_ex_cache.get("explain_summary"),
                    pros=_ex_cache.get("pros") or [],
                    cons=_ex_cache.get("cons") or [],
                    risk_flags=_ex_cache.get("risk_flags") or [],
                )
            except Exception:
                logger.warning("[DATA] failed to persist cache-hit record for task %s", task_id, exc_info=True)
            logger.info("[TASK] %s cache hit; skipped recompute", task_id)
            return
    logger.info("[TASK] %s cache miss; running analysis", task_id)
    try:
        from data.pipeline.analysis_bridge import run_multi_source_analysis

        _q, _sources = _task_scrape_query_and_sources(params)
        result = run_multi_source_analysis(
            sources=_sources,
            query=_q,
            limit_per_source=params.get("limit_per_source", 10),
            persist=params.get("persist", True),
            budget=params.get("budget"),
            target_postcode=params.get("target_postcode"),
            user_preferences=prefs,
        )
        elapsed = time.perf_counter() - t0
        degraded = bool(result.get("degraded"))
        _ex_run = build_p10_explain_from_msa_result(result)
        _append_high_safety_note(_ex_run, prefs)
        result_out = dict(result)
        result_out["p10_explain"] = _ex_run
        result_out["representative_row"] = get_representative_batch_row(result)
        _task_store.mark_success(task_id, result_out, degraded=degraded, elapsed=elapsed)
        analysis_summary = {
            "success": bool(result.get("success")),
            "degraded": degraded,
            "cache_hit": False,
            "cacheable": bool(result.get("success")) and not degraded,
            "pipeline_success": result.get("pipeline_success"),
            "sources_run": result.get("sources_run") or [],
            "aggregated_unique_count": result.get("aggregated_unique_count"),
            "total_analyzed_count": result.get("total_analyzed_count"),
            "error_count": len(result.get("errors") or []),
        }
        try:
            _ex_run = build_p10_explain_from_msa_result(result)
            _rs_body = {
                "summary": analysis_summary,
                "reusable_result": result if analysis_summary["cacheable"] else None,
                "p10_explain": _ex_run,
            }
            insert_analysis_record(
                analysis_type="multi_source_analysis",
                input_summary=analysis_input,
                result_summary=_rs_body,
                source="async_task",
                user_id=db_user_id,
                explain_summary=_ex_run.get("explain_summary"),
                pros=_ex_run.get("pros") or [],
                cons=_ex_run.get("cons") or [],
                risk_flags=_ex_run.get("risk_flags") or [],
            )
        except Exception:
            logger.warning("[DATA] failed to persist analysis record for task %s", task_id, exc_info=True)
        logger.info("[TASK] %s finished with %s in %.2fs", task_id, "degraded" if degraded else "success", elapsed)
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        logger.error("[TASK] %s failed: %s", task_id, exc, exc_info=True)
        _task_store.mark_failed(task_id, str(exc), elapsed=elapsed)
        try:
            insert_analysis_record(
                analysis_type="multi_source_analysis",
                input_summary=analysis_input,
                result_summary={
                    "summary": {
                        "success": False,
                        "degraded": False,
                        "cache_hit": False,
                        "cacheable": False,
                        "error": str(exc),
                    },
                    "reusable_result": None,
                    "p10_explain": {
                        "explain_summary": "Analysis did not complete; no recommendation summary is available.",
                        "pros": [],
                        "cons": [],
                        "risk_flags": [str(exc)],
                    },
                },
                source="async_task_failed",
                user_id=db_user_id,
                explain_summary="Analysis did not complete; no recommendation summary is available.",
                pros=[],
                cons=[],
                risk_flags=[str(exc)],
            )
        except Exception:
            logger.warning("[DATA] failed to persist failed analysis record for task %s", task_id, exc_info=True)
        send_alert(
            "Task %s failed: %s" % (task_id, exc),
            level="P2",
            source="api-server",
        )


# 提交长耗时异步任务（多源抓取 + 批量分析）；结果轮询 GET /tasks/{task_id}。
@app.post("/tasks")
def create_task(request: Request, body: AnalyzeRealRequest = AnalyzeRealRequest()):
    """Submit a multi-source scrape + analyze job.  Returns immediately with a task_id.

    Poll ``GET /tasks/{task_id}`` to check progress and retrieve results.
    """
    params = body.model_dump(exclude_none=True)
    summary = {
        "sources": params.get("sources"),
        "limit_per_source": params.get("limit_per_source"),
        "budget": params.get("budget"),
        "target_postcode": params.get("target_postcode"),
        "listing_url": (params.get("listing_url") or "").strip() or None,
        "property_type": params.get("property_type"),
        "bedrooms": params.get("bedrooms"),
        "bathrooms": params.get("bathrooms"),
        "distance_to_centre": params.get("distance_to_centre"),
        "safety_preference": params.get("safety_preference"),
    }
    user_id = _get_task_identity(request)
    rec = _task_store.create(input_summary=summary, user_id=user_id)
    _start_task_workers_once()
    _TASK_QUEUE.put((rec.task_id, params))
    logger.info("[TASK] queued %s (queue_size=%s)", rec.task_id, _TASK_QUEUE.qsize())
    return {"task_id": rec.task_id, "status": rec.status}


@app.get("/tasks")
def list_tasks(request: Request, mode: str = "active", limit: int = 30):
    """List tasks.

    Query params:
        mode   – ``active`` (default): queued/running only.
                 ``recent``: most recent *limit* tasks regardless of status.
        limit  – max tasks to return (default 30, max 100).
    """
    user_id = _get_task_identity(request)
    limit = min(max(limit, 1), 100)
    if mode == "recent":
        return {"tasks": _task_store.list_recent(limit=limit, user_id=user_id)}
    return {"tasks": _task_store.list_active(user_id=user_id)}


@app.get("/tasks/stats")
def task_stats(request: Request):
    """Aggregate task counts by status."""
    user_id = _get_task_identity(request)
    return _task_store.stats(user_id=user_id)


# 内部队列/Worker 粗粒度观测；排障与 pilot 用，主用户看房流程可不依赖。
@app.get("/tasks/system")
def task_system_status(request: Request):
    """Minimal queue + worker observability for ops checks."""
    user_id = _get_task_identity(request)
    stats = _task_store.stats(user_id=user_id)
    by_status = stats.get("by_status") or {}
    return {
        "queued_count": int(by_status.get("queued", 0)),
        "running_count": int(by_status.get("running", 0)),
        "success_count": int(by_status.get("success", 0)),
        "failed_count": int(by_status.get("failed", 0)),
        "degraded_count": int(by_status.get("degraded", 0)),
        "max_concurrent_tasks": _MAX_CONCURRENT_TASKS,
    }


@app.get("/tasks/{task_id}")
def get_task(request: Request, task_id: str):
    """Query the current state of an async task."""
    user_id = _get_task_identity(request)
    rec = _task_store.get(task_id)
    if rec is None or rec.user_id != user_id:
        return JSONResponse(
            status_code=404,
            content={"error": "task_not_found", "task_id": task_id},
        )
    out: dict[str, Any] = {
        "task_id": rec.task_id,
        "status": rec.status,
        "task_type": rec.task_type,
        "stage": rec.stage,
        "priority": rec.priority,
        "created_at": rec.created_at,
        "updated_at": rec.updated_at,
        "started_at": rec.started_at,
        "finished_at": rec.finished_at,
        "input_summary": rec.input_summary,
        "degraded": rec.degraded,
        "elapsed_seconds": rec.elapsed_seconds,
        "error": rec.error,
        "last_error_at": rec.last_error_at,
    }
    if rec.status in ("success", "degraded"):
        out["result"] = rec.result
    return out


# --- 落库只读查询：任务 / 分析记录 / UI 历史快照 / 房源记录（Bearer；与前端「历史」能力配合）---
# 平台共用：SQLite 记录层对 RentAI 异步任务与后续 ShortRentAI 落库约定兼容，以类型字段区分业务来源。
@app.get("/records/tasks")
def list_record_tasks(request: Request, limit: int = 30):
    """Minimal query endpoint for persisted task records."""
    user_id = _get_user_id_from_request(request)
    records = get_recent_task_records(limit=limit, user_id=user_id)
    return {
        "records": records,
        "count": len(records),
        "storage": "sqlite",
        "db_path": _RECORDS_DB_PATH,
    }


@app.get("/records/tasks/{task_id}")
def get_record_task_detail(request: Request, task_id: str):
    """Task detail endpoint for persisted task history."""
    user_id = _get_user_id_from_request(request)
    rec = get_task_record_detail(task_id, user_id=user_id)
    if rec is None:
        return JSONResponse(
            status_code=404,
            content={"error": "record_task_not_found", "task_id": task_id},
        )
    return {"record": rec, "storage": "sqlite", "db_path": _RECORDS_DB_PATH}


@app.get("/records/analysis")
def list_record_analysis(request: Request, limit: int = 30):
    """Minimal query endpoint for persisted analysis records."""
    user_id = _get_user_id_from_request(request)
    records = get_recent_analysis_records(limit=limit, user_id=user_id)
    return {
        "records": records,
        "count": len(records),
        "storage": "sqlite",
        "db_path": _RECORDS_DB_PATH,
    }


_MAX_UI_HISTORY_RAW_CHARS = 200_000


def _truncate_raw_task_snapshot(obj: Any) -> Any | None:
    if obj is None:
        return None
    try:
        s = json.dumps(obj, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return {"_serialization": "failed", "_note": "raw_task_snapshot omitted"}
    if len(s) <= _MAX_UI_HISTORY_RAW_CHARS:
        return obj
    return {
        "_truncated": True,
        "original_length": len(s),
        "preview_json_prefix": s[:_MAX_UI_HISTORY_RAW_CHARS],
    }


class UiHistorySaveBody(BaseModel):
    """Phase3：结果页保存到 SQLite analysis_records（analysis_type=p10_ui_history）。"""

    model_config = ConfigDict(extra="ignore")

    task_id: str = Field(..., min_length=4, max_length=80)
    input_value: Optional[str] = Field(default=None, max_length=2000)
    display_payload: dict[str, Any] = Field(default_factory=dict)
    raw_task_snapshot: Optional[dict[str, Any]] = None


@app.post("/records/ui-history")
def save_ui_history_record(request: Request, body: UiHistorySaveBody):
    """Persist a user-readable analysis snapshot after the Phase3 result page loads."""
    user_id = _get_user_id_from_request(request)
    tid = (body.task_id or "").strip()
    if not tid:
        return JSONResponse(
            status_code=400,
            content={"error": "invalid_task_id", "message": "task_id is required."},
        )
    dp = body.display_payload if isinstance(body.display_payload, dict) else {}
    ex = dp.get("explain") if isinstance(dp.get("explain"), dict) else {}
    header = dp.get("header") if isinstance(dp.get("header"), dict) else {}
    rk = dp.get("risk") if isinstance(dp.get("risk"), dict) else {}

    iv = (body.input_value or "").strip()
    input_summary: dict[str, Any] = {"history_task_id": tid}
    if iv:
        if iv.lower().startswith("http"):
            input_summary["listing_url"] = iv
        else:
            input_summary["target_postcode"] = iv

    raw_snap = _truncate_raw_task_snapshot(body.raw_task_snapshot)
    saved: dict[str, Any] = {
        "schema": "saved_result_payload_v1",
        "task_id": tid,
        "user_id": user_id,
        "input_value": iv,
        "display_payload": dp,
    }
    if raw_snap is not None:
        saved["raw_task_snapshot"] = raw_snap

    explain_line = (ex.get("summary") or header.get("verdict_label") or "") or ""
    explain_line = str(explain_line)[:2000] if explain_line else None
    pros = ex.get("pros") if isinstance(ex.get("pros"), list) else []
    cons = ex.get("cons") if isinstance(ex.get("cons"), list) else []
    risk_flags = rk.get("risk_flags") if isinstance(rk.get("risk_flags"), list) else []

    try:
        rid = insert_analysis_record(
            analysis_type=UI_HISTORY_ANALYSIS_TYPE,
            input_summary=input_summary,
            result_summary=saved,
            source="ui_phase3",
            user_id=user_id,
            explain_summary=explain_line,
            pros=pros,
            cons=cons,
            risk_flags=risk_flags,
        )
    except Exception as exc:
        logger.warning("[UI-HISTORY] insert failed: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "save_failed", "message": "Could not save analysis record."},
        )
    return {"ok": True, "record_id": rid, "analysis_type": UI_HISTORY_ANALYSIS_TYPE}


@app.get("/records/ui-history")
def list_ui_history(request: Request, limit: int = 50):
    """List Phase3 UI-saved analysis rows for the authenticated user."""
    user_id = _get_user_id_from_request(request)
    limit = min(max(limit, 1), 100)
    try:
        items = get_ui_history_items(limit=limit, user_id=user_id)
    except Exception as exc:
        logger.error("[UI-HISTORY] list failed: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "load_failed", "message": "Failed to load history."},
        )
    return {
        "items": items,
        "count": len(items),
        "storage": "sqlite",
        "db_path": _RECORDS_DB_PATH,
    }


@app.get("/records/ui-history/{record_id}")
def get_ui_history_one(request: Request, record_id: int):
    """Single saved snapshot (optional; primary UX still uses /result/{task_id})."""
    user_id = _get_user_id_from_request(request)
    try:
        detail = get_ui_history_detail(record_id, user_id=user_id)
    except Exception as exc:
        logger.error("[UI-HISTORY] detail failed: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "load_failed", "message": "Failed to load record."},
        )
    if detail is None:
        return JSONResponse(
            status_code=404,
            content={"error": "record_not_found", "message": "Record not found"},
        )
    return {"record": detail, "storage": "sqlite", "db_path": _RECORDS_DB_PATH}


@app.get("/records/properties")
def list_record_properties(request: Request, limit: int = 30):
    """Minimal query endpoint for persisted property records."""
    _ = _get_user_id_from_request(request)
    records = get_recent_property_records(limit=limit)
    return {
        "records": records,
        "count": len(records),
        "storage": "sqlite",
        "db_path": _RECORDS_DB_PATH,
    }


# =============================================================================
# 收藏与对比：登录用户写入 SQLite；POST /compare 为多条房源对比（Explain 摘要）
# 平台共用：房源收藏与对比能力适用于 RentAI 推荐结果及未来 ShortRentAI 列表，共用数据层与鉴权。
# =============================================================================

class FavoriteCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    listing_url: Optional[str] = None
    property_id: Optional[str] = None
    title: Optional[str] = None
    price: Optional[float] = None
    postcode: Optional[str] = None


class CompareRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    properties: list[dict[str, Any]]


def _float_opt_compare(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _build_compare_result(rows: list[dict[str, Any]]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for i, raw in enumerate(rows):
        p = raw if isinstance(raw, dict) else {}
        im = p.get("input_meta") if isinstance(p.get("input_meta"), dict) else {}
        price = _float_opt_compare(im.get("rent"))
        if price is None:
            price = _float_opt_compare(p.get("rent_pcm") or p.get("rent") or p.get("price"))
        pc = im.get("postcode") or p.get("postcode")
        pc = str(pc).strip() if pc is not None else None
        tit = im.get("title") or p.get("title")
        tit = str(tit).strip() if tit is not None else None
        _ex = build_p10_explain_for_batch_row(p)
        items.append(
            {
                "slot": i,
                "batch_index": p.get("index"),
                "title": tit,
                "listing_url": im.get("source_url") or p.get("listing_url"),
                "price": price,
                "bedrooms": _float_opt_compare(im.get("bedrooms") or p.get("bedrooms")),
                "commute_minutes": _float_opt_compare(
                    im.get("commute_minutes") or p.get("commute_minutes")
                ),
                "postcode": pc,
                "score": _float_opt_compare(p.get("score")),
                "decision_code": p.get("decision_code"),
                "explain": {
                    "explain_summary": _ex.get("explain_summary"),
                    "pros": _ex.get("pros") or [],
                    "cons": _ex.get("cons") or [],
                    "risk_flags": _ex.get("risk_flags") or [],
                },
            }
        )
    score_slots = [(i, items[i]["score"]) for i in range(len(items)) if items[i]["score"] is not None]
    price_slots = [(i, items[i]["price"]) for i in range(len(items)) if items[i]["price"] is not None]
    highest_score_slot = max(score_slots, key=lambda x: x[1])[0] if score_slots else None
    lowest_price_slot = min(price_slots, key=lambda x: x[1])[0] if price_slots else None
    return {
        "items": items,
        "summary": {
            "highest_score_slot": highest_score_slot,
            "lowest_price_slot": lowest_price_slot,
            "count": len(items),
        },
    }


@app.post("/favorites")
def add_favorite(request: Request, body: FavoriteCreate):
    # favorites 按当前收藏作用域：登录用户操作自己的收藏；游客操作 guest:<session>；两者不合并。
    user_id = _get_favorite_scope_user_id(request)
    url = (body.listing_url or "").strip() or None
    pid = (body.property_id or "").strip() or None
    if not url and not pid:
        return JSONResponse(
            status_code=400,
            content={"error": "missing_identifier", "message": "Provide listing_url and/or property_id."},
        )
    rec = insert_favorite_record(
        user_id,
        listing_url=url,
        property_id=pid,
        title=body.title,
        price=body.price,
        postcode=body.postcode,
    )
    if rec is None:
        return JSONResponse(
            status_code=409,
            content={"error": "duplicate_or_invalid", "message": "Already favorited or could not save."},
        )
    return {"favorite": rec, "storage": "sqlite", "db_path": _RECORDS_DB_PATH}


@app.get("/favorites")
def list_favorites(request: Request, limit: int = 100):
    # favorites 按当前收藏作用域：登录用户操作自己的收藏；游客操作 guest:<session>；两者不合并。
    user_id = _get_favorite_scope_user_id(request)
    limit = min(max(limit, 1), 500)
    rows = list_favorite_records(user_id, limit=limit)
    return {
        "favorites": rows,
        "count": len(rows),
        "storage": "sqlite",
        "db_path": _RECORDS_DB_PATH,
    }


@app.delete("/favorites/{favorite_id}")
def remove_favorite(request: Request, favorite_id: str):
    # favorites 按当前收藏作用域：登录用户操作自己的收藏；游客操作 guest:<session>；两者不合并。
    user_id = _get_favorite_scope_user_id(request)
    ok = delete_favorite_record(user_id, favorite_id)
    if not ok:
        return JSONResponse(
            status_code=404,
            content={"error": "favorite_not_found", "id": favorite_id},
        )
    return {"ok": True, "id": favorite_id}


@app.post("/compare")
def compare_listings(request: Request, body: CompareRequest):
    _ = _get_user_id_from_request(request)
    props = body.properties if isinstance(body.properties, list) else []
    if len(props) < 2 or len(props) > 5:
        return JSONResponse(
            status_code=400,
            content={"error": "invalid_count", "message": "Send between 2 and 5 property objects."},
        )
    return {"comparison": _build_compare_result(props)}


# =============================================================================
# 主产品 HTML 页面入口（web_public）：用户从浏览器进入的第一界面为 GET / → index.html；
# 下列路径与静态文件名一一对应，业务数据多由前端 sessionStorage/localStorage 或再调 API 注入。
# =============================================================================

# AI 需求解析后的推荐结果页（RentAI 主流程核心页面之一）
@app.get("/ai-result")
def web_ai_result():
    """Phase1 AI — 需求解析与推荐结果页（静态 HTML，数据由 sessionStorage 注入）。"""
    page = _WEB_PUBLIC_DIR / "ai_result.html"
    if not page.is_file():
        return JSONResponse(
            status_code=503,
            content={
                "error": "web_public_missing",
                "message": "Expected web_public/ai_result.html beside api_server.py.",
            },
        )
    return FileResponse(page)


# 已收藏房源两两对比
@app.get("/compare")
def web_compare():
    """Phase1 — 收藏房源对比页（静态 HTML；数据来自 localStorage + sessionStorage）。"""
    page = _WEB_PUBLIC_DIR / "compare.html"
    if not page.is_file():
        return JSONResponse(
            status_code=503,
            content={
                "error": "web_public_missing",
                "message": "Expected web_public/compare.html beside api_server.py.",
            },
        )
    return FileResponse(page)


# 声誉 / 中介核查占位（Phase 5 Step 1；静态页，不调用 AI）
@app.get("/reputation")
def web_reputation_placeholder():
    page = _WEB_PUBLIC_DIR / "reputation.html"
    if not page.is_file():
        return JSONResponse(
            status_code=503,
            content={
                "error": "web_public_missing",
                "message": "Expected web_public/reputation.html beside api_server.py.",
            },
        )
    return FileResponse(page)


# 租赁分析 / AI 聊天入口（Phase 5 Step 2；静态 + 前端 mock，不调用 /api/ai/*）
@app.get("/start")
def web_start_analysis():
    page = _WEB_PUBLIC_DIR / "start.html"
    if not page.is_file():
        return JSONResponse(
            status_code=503,
            content={
                "error": "web_public_missing",
                "message": "Expected web_public/start.html beside api_server.py.",
            },
        )
    return FileResponse(page)


# 合同检查入口（Phase 5 Step 3；静态 + 前端 mock，不调用 /api/contract/*）
@app.get("/check-contract")
def web_check_contract():
    page = _WEB_PUBLIC_DIR / "check_contract.html"
    if not page.is_file():
        return JSONResponse(
            status_code=503,
            content={
                "error": "web_public_missing",
                "message": "Expected web_public/check_contract.html beside api_server.py.",
            },
        )
    return FileResponse(page)


# 合同条款分析（接 /api/contract/* 系列）
@app.get("/contract-analysis")
def web_contract_analysis():
    """Phase 4 — 合同分析（静态 HTML；粘贴文本 / 上传文件占位，后续接 API）。"""
    page = _WEB_PUBLIC_DIR / "contract_analysis.html"
    if not page.is_file():
        return JSONResponse(
            status_code=503,
            content={
                "error": "web_public_missing",
                "message": "Expected web_public/contract_analysis.html beside api_server.py.",
            },
        )
    return FileResponse(page)


# --- 当前主产品默认落地首页（RentAI 主流程入口之一；web_public/index.html）---
@app.get("/")
def web_phase3_home():
    """P10 Phase3 — minimal product homepage (static HTML)."""
    index = _WEB_PUBLIC_DIR / "index.html"
    if not index.is_file():
        return JSONResponse(
            status_code=503,
            content={
                "error": "web_public_missing",
                "message": "Phase3 UI not found. Expected web_public/index.html beside api_server.py.",
            },
        )
    return FileResponse(index)


# 异步长任务结果展示（task_id 由客户端从路径读取）
@app.get("/result/{task_id}")
def web_phase3_result(task_id: str):
    """P10 Phase3 — task result page (static HTML; task_id read client-side from path)."""
    page = _WEB_PUBLIC_DIR / "result.html"
    if not page.is_file():
        return JSONResponse(
            status_code=503,
            content={
                "error": "web_public_missing",
                "message": "Phase3 UI not found. Expected web_public/result.html beside api_server.py.",
            },
        )
    return FileResponse(page)


# --- 智能助理 / 对话式统一入口（与 POST /api/ai/query 等 RentAI 编排配合；前端意图分流可在此演进）---
# 与上文「ShortRentAI future integration point」同属产品扩展锚点：同一入口未来可路由至 ShortRentAI 管线，
# 而不新增并列首页；当前仍以 RentAI 主流程为主。
@app.get("/assistant")
def web_assistant_entry():
    """Phase 4 Round7：聊天式统一入口骨架（静态 assistant.html）。"""
    page = _WEB_PUBLIC_DIR / "assistant.html"
    if not page.is_file():
        return JSONResponse(
            status_code=503,
            content={
                "error": "web_public_missing",
                "message": "Expected web_public/assistant.html beside api_server.py.",
            },
        )
    return FileResponse(page)


# --- 历史记录相关页面：统一入口 + 列表/详情（与 /api/analysis/history/*、/records/* 等配合）---
@app.get("/analysis-history")
def web_analysis_history_hub():
    """Phase 4 Round6：统一分析历史入口页（骨架：房源 / 合同分区，静态 analysis_history.html）。"""
    page = _WEB_PUBLIC_DIR / "analysis_history.html"
    if not page.is_file():
        return JSONResponse(
            status_code=503,
            content={
                "error": "web_public_missing",
                "message": "Expected web_public/analysis_history.html beside api_server.py.",
            },
        )
    return FileResponse(page)


@app.get("/history")
def web_phase3_history():
    """分析历史列表（localStorage analysis_history，静态 history.html）。"""
    page = _WEB_PUBLIC_DIR / "history.html"
    if not page.is_file():
        return JSONResponse(
            status_code=503,
            content={
                "error": "web_public_missing",
                "message": "Phase3 UI not found. Expected web_public/history.html beside api_server.py.",
            },
        )
    return FileResponse(page)


@app.get("/history-detail")
def web_history_detail():
    """分析历史单条详情（sessionStorage history_current，静态 history_detail.html）。"""
    page = _WEB_PUBLIC_DIR / "history_detail.html"
    if not page.is_file():
        return JSONResponse(
            status_code=503,
            content={
                "error": "web_public_missing",
                "message": "Expected web_public/history_detail.html beside api_server.py.",
            },
        )
    return FileResponse(page)


# 已登录用户账户概览 / 分桶入口
@app.get("/account")
def web_account_page():
    """Phase 5 Round2 Step4 — minimal account / history bucket (static HTML)."""
    page = _WEB_PUBLIC_DIR / "account.html"
    if not page.is_file():
        return JSONResponse(
            status_code=503,
            content={
                "error": "web_public_missing",
                "message": "Expected web_public/account.html beside api_server.py.",
            },
        )
    return FileResponse(page)


# --- 账户：登录 / 注册静态表单项（配合 /auth/login、/auth/register API）---
@app.get("/login")
def web_phase3_login():
    """P10 Phase3 Step4 — login form (static HTML)."""
    page = _WEB_PUBLIC_DIR / "login.html"
    if not page.is_file():
        return JSONResponse(
            status_code=503,
            content={"error": "web_public_missing", "message": "Expected web_public/login.html."},
        )
    return FileResponse(page)


@app.get("/register")
def web_phase3_register():
    """P10 Phase3 Step4 — registration form (static HTML)."""
    page = _WEB_PUBLIC_DIR / "register.html"
    if not page.is_file():
        return JSONResponse(
            status_code=503,
            content={"error": "web_public_missing", "message": "Expected web_public/register.html."},
        )
    return FileResponse(page)


# 全局 CSS/JS/图片等：挂载 web_public/assets → URL 前缀 /assets（所有页面静态资源由此加载）
_assets_dir = _WEB_PUBLIC_DIR / "assets"
if _assets_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="p10_phase3_assets")


_start_task_workers_once()


if __name__ == "__main__":
    # Direct `python api_server.py` — same bind/env as `python run.py` (uvicorn CLI 仍可用).
    import uvicorn

    from config import get_bind_host, get_bind_port, get_effective_debug, get_uvicorn_reload

    if get_effective_debug():
        logging.basicConfig(level=logging.DEBUG)
    _host = get_bind_host()
    _port = get_bind_port()
    _reload = get_uvicorn_reload()
    print(
        "RentalAI starting — http://%s:%s/  (reload=%s)" % (_host, _port, _reload),
        flush=True,
    )
    uvicorn.run(
        app,
        host=_host,
        port=_port,
        reload=_reload,
    )

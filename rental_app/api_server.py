# P2 Phase1–4: RentalAI HTTP API（FastAPI）
# 推荐本地一键启动（Phase4）: python run.py
# 等价: uvicorn api_server:app --reload --host 127.0.0.1 --port 8000
# 生产/PaaS: uvicorn api_server:app --host 0.0.0.0 --port $PORT
# 需在 rental_app 目录下执行（或设置 rootDir），以便正确 import web_bridge

import json
import logging
import os
import queue
import re
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import Body, FastAPI, File, Form, Request, UploadFile
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

import threading

from alert_utils import FailureTracker, send_alert
from api_analysis import analyze_batch_request_body, modular_analyze_response
from data.storage.records_db import (
    _DB_PATH as _RECORDS_DB_PATH,
    UI_HISTORY_ANALYSIS_TYPE,
    create_user,
    delete_favorite_record,
    email_exists,
    find_reusable_analysis_result,
    get_user_by_id,
    init_records_db,
    insert_analysis_record,
    insert_favorite_record,
    list_favorite_records,
    normalize_analysis_input_signature,
    verify_user,
)
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

logger = logging.getLogger("rentalai.api")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

_api_failures = FailureTracker(threshold=3, source="api-server")
init_records_db()
_task_store = TaskStore()

app = FastAPI(
    title="RentalAI API",
    description="P2 Phase5 — modular endpoints + /analyze-batch (standard recommendations)",
    version="0.6.0",
)

_WEB_PUBLIC_DIR = Path(__file__).resolve().parent / "web_public"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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


_AUTH_TOKENS: dict[str, str] = {}
_AUTH_LOCK = threading.Lock()


class AuthRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    email: str
    password: str


def _issue_token(user_id: str) -> str:
    token = uuid.uuid4().hex
    with _AUTH_LOCK:
        _AUTH_TOKENS[token] = user_id
    return token


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
    with _AUTH_LOCK:
        user_id = _AUTH_TOKENS.get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="invalid_or_expired_token")
    return user_id


def _get_task_identity(request: Request) -> str:
    """Bearer → real user id; otherwise stable guest id from X-Guest-Session (P10 Phase7)."""
    token = _extract_bearer_token(request)
    if token:
        with _AUTH_LOCK:
            uid = _AUTH_TOKENS.get(token)
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


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "rentalai-api",
        "api_version": "P2-Phase5",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/alerts")
def alerts_status():
    """Current consecutive-failure counts per endpoint (resets on success)."""
    return {
        "failure_counts": _api_failures.get_counts(),
        "threshold": _api_failures._threshold,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/auth/register")
def auth_register(body: AuthRequest):
    em = str(body.email or "").strip()
    pw = str(body.password or "")
    if not em or not pw:
        return JSONResponse(
            status_code=400,
            content={"error": "register_failed", "message": "Invalid email or password."},
        )
    if email_exists(em):
        return JSONResponse(
            status_code=400,
            content={"error": "register_failed", "message": "User already exists"},
        )
    user = create_user(body.email, body.password)
    if user is None:
        return JSONResponse(
            status_code=400,
            content={"error": "register_failed", "message": "Could not create account."},
        )
    token = _issue_token(user["id"])
    return {
        "user_id": user["id"],
        "email": user["email"],
        "created_at": user["created_at"],
        "token": token,
    }


@app.post("/auth/login")
def auth_login(body: AuthRequest):
    user = verify_user(body.email, body.password)
    if user is None:
        return JSONResponse(
            status_code=401,
            content={"error": "login_failed", "message": "Invalid email or password."},
        )
    token = _issue_token(user["id"])
    return {"user_id": user["id"], "email": user["email"], "token": token}


@app.post("/auth/logout")
def auth_logout(request: Request):
    """Invalidate the current bearer token (in-process store)."""
    token = _extract_bearer_token(request)
    if token:
        with _AUTH_LOCK:
            _AUTH_TOKENS.pop(token, None)
    return {"ok": True}


@app.get("/auth/me")
def auth_me(request: Request):
    """Resolve bearer token to a minimal public profile."""
    user_id = _get_user_id_from_request(request)
    user = get_user_by_id(user_id)
    if user is None:
        return JSONResponse(
            status_code=401,
            content={"error": "invalid_or_expired_token", "message": "Session expired. Please log in again."},
        )
    return {"user_id": user["id"], "email": user["email"], "created_at": user["created_at"]}


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


@app.post("/analyze-batch")
def analyze_batch(body: dict = Body(default_factory=dict)):
    """
    批量分析：`{ \"properties\": [ {...}, ... ] }`。
    逐项复用与 /analyze 相同的引擎；单项失败不拖垮整批。
    """
    return analyze_batch_request_body(body)


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


class ContractAnalyzeTextBody(BaseModel):
    """POST /api/contract/analyze-text — 纯文本合同风险扫描（rule-based）。"""

    model_config = ConfigDict(extra="ignore")
    contract_text: str = Field(default="", description="Full or partial tenancy contract text")


@app.post("/api/contract/analyze-text")
def api_contract_analyze_text(body: ContractAnalyzeTextBody = Body(...)):
    """
    合同文本分析入口（Phase B1）：返回 detected_risks / summary，后续可接 PDF 解析结果复用同一结构。
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
    user_id = _get_user_id_from_request(request)
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
    user_id = _get_user_id_from_request(request)
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
    user_id = _get_user_id_from_request(request)
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


_assets_dir = _WEB_PUBLIC_DIR / "assets"
if _assets_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="p10_phase3_assets")


_start_task_workers_once()

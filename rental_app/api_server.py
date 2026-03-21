# P2 Phase1–4: RentalAI HTTP API（FastAPI）
# 本地: uvicorn api_server:app --reload --host 127.0.0.1 --port 8000
# 生产/PaaS: uvicorn api_server:app --host 0.0.0.0 --port $PORT
# 需在 rental_app 目录下执行（或设置 rootDir），以便正确 import web_bridge

from typing import Any, Optional

from fastapi import Body, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from api_analysis import analyze_batch_request_body, modular_analyze_response

app = FastAPI(
    title="RentalAI API",
    description="P2 Phase5 — modular endpoints + /analyze-batch (standard recommendations)",
    version="0.6.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/health")
def health():
    return {"status": "ok", "service": "rentalai-api", "api_version": "P2-Phase5"}


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

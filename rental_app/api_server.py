# P2 Phase1: RentalAI HTTP API 入口（FastAPI）
# 启动: uvicorn api_server:app --reload --host 127.0.0.1 --port 8000
# 需在 rental_app 目录下执行，以便正确 import web_bridge

from fastapi import Body, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api_analysis import analyze_property_request_body

app = FastAPI(
    title="RentalAI API",
    description="P2 Phase1 — property analysis via web_bridge.run_web_demo_analysis",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """存活检查。"""
    return {"status": "ok", "service": "rentalai-api"}


@app.post("/analyze")
def analyze(body: dict = Body(default_factory=dict)):
    """
    接收房源相关字段 JSON，返回分析结果。
    字段示例: rent, bills_included, commute_minutes, bedrooms, budget,
    postcode, area, distance, target_postcode（均可选，缺失由桥接层默认）。
    """
    return analyze_property_request_body(body)

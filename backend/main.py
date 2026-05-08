from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.short_rent_api import get_short_rent_recommendations_api


app = FastAPI(title="Short Rent Backend API")

# Phase 5-A4：本地前后端联调允许跨域；生产环境应收紧 allow_origins。
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict:
    return {"message": "Backend API is running"}


@app.get("/api/short-rent/recommendations")
def short_rent_recommendations() -> dict:
    return get_short_rent_recommendations_api()

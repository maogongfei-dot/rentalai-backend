from fastapi import Body, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.short_rent_api import (
    create_short_rent_listing_api,
    get_short_rent_recommendations_api,
)


app = FastAPI(title="Short Rent Backend API")

# Phase 5-A4：本地前后端联调允许跨域；生产环境应收紧。
# Phase 6-C3：allow_origin_regex 覆盖 Vite 端口占用时自动切换的 localhost 端口（如 5174）。
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
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
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


@app.post("/api/short-rent/create")
def short_rent_create(data: dict = Body(...)) -> dict:
    return create_short_rent_listing_api(data)

import os

from fastapi import Body, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import Base, engine
from backend.db_models.short_rent_db_model import ShortRentDB  # noqa: F401
from backend.api.short_rent_api import (
    create_short_rent_listing_api,
    get_short_rent_recommendations_api,
)


app = FastAPI(title="Short Rent Backend API")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]

env_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

allowed_origins = default_origins + env_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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

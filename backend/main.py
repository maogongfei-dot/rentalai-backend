from fastapi import FastAPI

from backend.api.short_rent_api import get_short_rent_recommendations_api


app = FastAPI(title="Short Rent Backend API")


@app.get("/")
def root() -> dict:
    return {"message": "Backend API is running"}


@app.get("/api/short-rent/recommendations")
def short_rent_recommendations() -> dict:
    return get_short_rent_recommendations_api()

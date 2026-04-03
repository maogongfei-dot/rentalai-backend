"""Deployment shim: ``uvicorn app:app`` re-exports the FastAPI instance from ``api_server`` (no duplicate routes)."""
from api_server import app

__all__ = ["app"]

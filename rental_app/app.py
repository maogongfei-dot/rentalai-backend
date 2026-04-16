"""
Deployment entry / import shim for platform compatibility.

Role of this file:
- This file is a deployment shim (not the main development entry).
- Recommended local development entry is `run.py`.
- Main FastAPI backend app is defined in `api_server.py`.
- This shim keeps compatibility with import styles used by Render, gunicorn,
  and other platforms expecting an `app` object from `app.py`.
"""
# Keep this file intentionally minimal: re-export the single FastAPI app object
# so deployment platforms can import `app:app` without changing runtime behavior.
from api_server import app

__all__ = ["app"]

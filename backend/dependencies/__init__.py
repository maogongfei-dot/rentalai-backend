"""FastAPI dependencies for the ``backend`` package."""

from backend.dependencies.auth import get_current_user

__all__ = ["get_current_user"]

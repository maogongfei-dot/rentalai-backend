"""Auth HTTP routes (Phase 3 Step 2 — register only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.db_models.user_db_model import User
from backend.schemas.user_schema import UserCreate, UserRead
from backend.utils.security import hash_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register_user(body: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    """Create a new user; email is normalized to lowercase."""
    email = (body.email or "").strip().lower()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required.",
        )
    if not body.password or not str(body.password).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot be empty.",
        )

    stmt = select(User).where(User.email == email)
    if db.execute(stmt).scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    full_name = body.full_name
    if full_name is not None:
        full_name = full_name.strip() or None

    user = User(
        email=email,
        hashed_password=hash_password(body.password),
        full_name=full_name,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        ) from None
    db.refresh(user)
    return UserRead.model_validate(user)

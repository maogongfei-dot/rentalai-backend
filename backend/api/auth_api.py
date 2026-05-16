"""Auth HTTP routes (Phase 3 — register + login)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.db_models.user_db_model import User
from backend.schemas.user_schema import Token, UserCreate, UserLogin, UserRead
from backend.utils.security import create_access_token, hash_password, verify_password

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


@router.post("/login", response_model=Token)
def login_user(body: UserLogin, db: Session = Depends(get_db)) -> Token:
    """Authenticate with email + password; returns a JWT access token."""
    email = (body.email or "").strip().lower()
    if not email or not body.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    stmt = select(User).where(User.email == email)
    user = db.execute(stmt).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
    )
    return Token(access_token=access_token, token_type="bearer")

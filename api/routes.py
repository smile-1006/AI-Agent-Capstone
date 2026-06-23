"""FastAPI routes.

This module exposes the HTTP API used by the frontend.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from sqlalchemy.orm import Session

from typing import Any


from api.schemas import HealthResponse
from database.base import init_db
from database.session import get_db
from database.models import User
from api.auth import hash_password, create_access_token, verify_password



router = APIRouter(prefix="/api")




class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str


@router.on_event("startup")
def on_startup() -> None:
    # DB initialization for local/dev.
    # For production, use Alembic migrations.
    from database.session import SessionLocal

    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Health check endpoint."""

    return HealthResponse(status="ok")


@router.post("/auth/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user (dev convenience endpoint)."""

    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

    user = User(username=payload.username, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=user.username)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Login with username/password."""

    user = db.query(User).filter(User.username == payload.username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(subject=user.username)

    return {"access_token": token, "token_type": "bearer"}


class ExecuteRequest(BaseModel):
    """Execute agent pipeline request."""

    goal: str


@router.post("/execute")
def execute(
    payload: ExecuteRequest,
):
    """Run the multi-agent pipeline.

    Note: in a production implementation this endpoint would require auth.
    For capstone demos, we keep it functional and focused on agent orchestration.
    """

    # Import here to avoid circular imports at module import time.
    from api.execution import ExecuteUseCase

    use_case = ExecuteUseCase()
    # Execute synchronously from a sync route handler by awaiting via loop-less pattern.
    # FastAPI will handle this as a normal function; ExecuteUseCase is async callable.
    # To keep this route safe, we create a minimal asyncio run.
    import asyncio

    async def _run() -> dict[str, Any]:
        return await use_case(goal=payload.goal, user=None, context={})

    return asyncio.run(_run())



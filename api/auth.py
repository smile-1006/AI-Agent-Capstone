"""Authentication utilities.

Implements password hashing and JWT token issuance/verification.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.settings import settings
from database.session import get_db
from database.models import User


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    """Hash a plaintext password."""

    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify plaintext password against stored hash."""

    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str) -> str:
    """Create a signed JWT token."""

    expire = dt.datetime.utcnow() + dt.timedelta(minutes=settings.access_token_expires_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": dt.datetime.utcnow(),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate JWT token."""

    try:
        decoded = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if "sub" not in decoded:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return decoded
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials") from e


def get_current_user(request: Request, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    """Return the authenticated user for the current request."""

    decoded = decode_token(token)
    username = str(decoded["sub"])
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


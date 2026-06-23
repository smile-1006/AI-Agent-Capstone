"""Database initialization helpers.

This module provides idempotent DB schema creation for local/dev runs.
For production, Alembic migrations should be used.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from database.models import Base


def init_db(db: Session) -> None:
    """Create all tables if they don't exist."""

    Base.metadata.create_all(bind=db.get_bind())


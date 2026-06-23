"""FastAPI entrypoint.

This file wires together middleware, routes, and application lifecycle.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.logger import configure_logging
from database.base import init_db
from database.session import SessionLocal

from app.bootstrap import build_settings



def _init_db() -> None:
    """Initialize DB tables for local/dev.

    Production deployments should use Alembic migrations.
    """

    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()


from api.routes import router as api_router
from app.api_docs import router as docs_router




def create_app() -> FastAPI:
    """Create and configure the FastAPI app."""

    configure_logging()

    app = FastAPI(
        title="AI-Agent-Capstone",
        version="0.1.0",
    )

    @app.on_event("startup")
    def _startup() -> None:
        _init_db()

    app.include_router(api_router)
    app.include_router(docs_router)

    return app




app = create_app()


"""FastAPI routes.

This module exposes the HTTP API used by the frontend.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status, Request, WebSocket
from pydantic import BaseModel

from sqlalchemy.orm import Session

from typing import Any


from api.schemas import HealthResponse
from database.base import init_db
from database.session import get_db
from database.models import User
from api.auth import hash_password, create_access_token, verify_password, verify_tools_access



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
    context: dict[str, Any] = {}


@router.post("/execute")
async def execute(
    payload: ExecuteRequest,
):
    """Run the multi-agent pipeline.

    Note: in a production implementation this endpoint would require auth.
    For capstone demos, we keep it functional and focused on agent orchestration.
    """

    # Import here to avoid circular imports at module import time.
    from api.execution import ExecuteUseCase

    use_case = ExecuteUseCase()
    return await use_case(goal=payload.goal, user=None, context=payload.context or {})



@router.websocket('/ws/execute')
async def ws_execute(websocket: WebSocket):
    """WebSocket endpoint to run the agent pipeline and stream per-step progress."""
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        goal = data.get('goal')
        context = data.get('context') or {}

        # Instantiate components similar to ExecuteUseCase
        from api.execution import _LocalWebSearchTool
        from agents.router import RouterAgent as RouterImpl
        from agents.planner_agent import PlannerAgent as PlannerImpl
        from agents.research_agent import ResearchAgent as ResearchImpl
        from agents.executor_agent import ExecutorAgent as ExecutorImpl
        from agents.reviewer_agent import ReviewerAgent as ReviewerImpl

        router = RouterImpl()
        planner = PlannerImpl()
        researcher = ResearchImpl(web_search_tool=_LocalWebSearchTool())
        executor = ExecutorImpl()
        reviewer = ReviewerImpl()

        ctx = dict(context or {})

        # route
        route = await router.route(goal, context=ctx)
        ctx['route'] = route
        await websocket.send_json({'type': 'route', 'data': route})

        # plan
        plan = await planner.plan(goal, context=ctx)
        await websocket.send_json({'type': 'plan', 'data': plan})

        # research
        research = await researcher.research(plan=plan, context=ctx)
        await websocket.send_json({'type': 'research', 'data': research})

        # draft
        draft = await executor.execute(plan=plan, research=research, context=ctx)
        await websocket.send_json({'type': 'draft', 'data': draft})

        # final
        final = await reviewer.review(plan=plan, draft=draft, research=research, context=ctx)
        await websocket.send_json({'type': 'final', 'data': final})

    except Exception as e:
        await websocket.send_json({'type': 'error', 'data': str(e)})
    finally:
        await websocket.close()


# ---- Tool endpoints (web search, pdf read, image) ----


class WebSearchRequest(BaseModel):
    query: str
    max_results: int = 3


@router.post("/tools/web_search")
async def web_search(payload: WebSearchRequest, _auth: Any = Depends(verify_tools_access)):
    """Call the local web-search tool and return results."""
    from mcp.tools import tool_web_search

    return await tool_web_search(ctx={}, query=payload.query, max_results=payload.max_results)


@router.post("/tools/calculator")
async def calculator(payload: dict, _auth: Any = Depends(verify_tools_access)):
    """Evaluate a calculator expression using local tool handler.

    Expects JSON: { "expression": "2+2" }
    """
    expr = payload.get("expression")
    if not expr:
        raise HTTPException(status_code=400, detail="missing expression")
    from mcp.tools import tool_calculator

    try:
        res = await tool_calculator(ctx={}, expression=str(expr))
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PdfReadRequest(BaseModel):
    path: str
    max_pages: int = 3


@router.post("/tools/pdf_read")
async def pdf_read(payload: PdfReadRequest, _auth: Any = Depends(verify_tools_access)):
    """Read a local PDF using the PDF tool."""
    from mcp.tools import tool_pdf_read

    return await tool_pdf_read(ctx={}, path=payload.path, max_pages=payload.max_pages)


class DocumentReadRequest(BaseModel):
    path: str
    max_pages: int = 3


@router.post("/tools/document_read")
async def document_read(payload: DocumentReadRequest, _auth: Any = Depends(verify_tools_access)):
    """Read a local document file using the document read tool."""
    from mcp.tools import tool_document_read

    return await tool_document_read(ctx={}, path=payload.path, max_pages=payload.max_pages)


class ImageOcrRequest(BaseModel):
    path: str
    languages: list[str] | None = None


@router.post("/tools/image_ocr")
async def image_ocr(payload: ImageOcrRequest, _auth: Any = Depends(verify_tools_access)):
    """Extract text from a local image using OCR."""
    from mcp.tools import tool_image_ocr

    return await tool_image_ocr(ctx={}, path=payload.path, languages=payload.languages)


class ImageProcessRequest(BaseModel):
    path: str
    action: str = "info"


@router.post("/tools/image_process")
async def image_process(payload: ImageProcessRequest, _auth: Any = Depends(verify_tools_access)):
    """Process an image (info or thumbnail) via the image tool."""
    from mcp.tools import tool_image_process

    return await tool_image_process(ctx={}, path=payload.path, action=payload.action)




@router.get('/tools/image_thumbnail')
def image_thumbnail(path: str, request: Request, _auth: Any = Depends(verify_tools_access)):
    """Serve a previously-generated thumbnail file (restricted to project directory)."""
    # Prevent path traversal: only allow files under workspace
    import os
    from fastapi.responses import FileResponse

    base = os.path.abspath(os.getcwd())
    target = os.path.abspath(path)
    if not target.startswith(base):
        raise HTTPException(status_code=400, detail="invalid path")
    if not os.path.exists(target):
        raise HTTPException(status_code=404, detail="file not found")

    return FileResponse(target, filename=os.path.basename(target))



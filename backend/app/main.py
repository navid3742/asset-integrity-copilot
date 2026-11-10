"""HTTP API: chat, asset and document lookups, and the report review workflow."""

import hmac
import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from threading import Lock

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__, agent, db, retrieval
from .config import (
    API_KEY,
    DEMO_PASSWORD,
    LIVE_ENABLED,
    MAX_API_REQUESTS_PER_HOUR,
    MODEL,
    STATIC_DIR,
)

_REQUESTS = defaultdict(deque)
_RATE_LOCK = Lock()
_TAG_PATTERN = r"^(?:P|CV|PV)-\d{3}$"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.initialize()
    yield


app = FastAPI(
    title="Asset Integrity Copilot API",
    version=__version__,
    docs_url="/api/docs",
    lifespan=lifespan,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    # Hashed static bundles can be cached; API responses shouldn't be.
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


def auth(x_demo_key: str | None = Header(default=None)):
    if DEMO_PASSWORD and not hmac.compare_digest(x_demo_key or "", DEMO_PASSWORD):
        raise HTTPException(401, detail="Incorrect demo access password")
    return True


def limit_requests(request: Request):
    # X-Forwarded-For is ignored on purpose because a client can spoof it to dodge
    # the limit. Behind Render's proxy, client.host is usually the proxy address, so
    # in practice this works as a shared hourly cap rather than a per-visitor one.
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with _RATE_LOCK:
        q = _REQUESTS[ip]
        while q and now - q[0] > 3600:
            q.popleft()
        if len(q) >= MAX_API_REQUESTS_PER_HOUR:
            raise HTTPException(429, detail="Demo hourly request limit reached")
        q.append(now)


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    history: list[dict] = Field(default_factory=list, max_length=6)


class DraftRequest(BaseModel):
    asset_id: str = Field(pattern=_TAG_PATTERN)


class ApprovalRequest(BaseModel):
    confirmation: str = Field(min_length=1, max_length=80)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "Asset Integrity Copilot", "version": __version__}


@app.get("/api/status", dependencies=[Depends(auth)])
def status():
    return {
        "mode": "live" if LIVE_ENABLED else "offline",
        "live_available": LIVE_ENABLED,
        "configured_but_password_missing": bool(API_KEY and not DEMO_PASSWORD),
        "model": MODEL if LIVE_ENABLED else None,
        "agent_framework": "OpenAI Agents SDK",
        "usage": agent.usage(),
        "counts": db.counts(),
    }


@app.post("/api/chat", dependencies=[Depends(auth), Depends(limit_requests)])
def chat(payload: ChatRequest):
    try:
        return agent.live_chat(payload.question, payload.history)
    except Exception as exc:
        logging.exception("Agent request failed: %s", type(exc).__name__)
        if "limit" in str(exc).lower():
            raise HTTPException(429, detail="API budget limit reached. Use offline mode.") from None
        raise HTTPException(
            502, detail="AI provider request failed. Check API key, model access, quota and logs."
        ) from None


@app.get("/api/documents", dependencies=[Depends(auth)])
def documents():
    return retrieval.documents()


@app.get("/api/documents/{doc_id}", dependencies=[Depends(auth)])
def document(doc_id: str):
    found = retrieval.get_document(doc_id)
    if not found:
        raise HTTPException(404, detail="Document not found")
    return found


@app.get("/api/assets", dependencies=[Depends(auth)])
def assets(q: str = ""):
    return db.list_assets(q)


@app.get("/api/assets/{asset_id}", dependencies=[Depends(auth)])
def asset(asset_id: str):
    found = db.get_asset(asset_id)
    if not found:
        raise HTTPException(404, detail="Asset not found")
    return found


@app.get("/api/assets/{asset_id}/history", dependencies=[Depends(auth)])
def asset_history(asset_id: str):
    if not db.get_asset(asset_id):
        raise HTTPException(404, detail="Asset not found")
    return {
        "inspections": db.get_inspections(asset_id),
        "maintenance": db.get_maintenance(asset_id),
        "incidents": db.get_incidents(asset_id),
    }


@app.get("/api/reports", dependencies=[Depends(auth)])
def reports():
    return db.list_reports()


@app.post("/api/reports/draft", dependencies=[Depends(auth), Depends(limit_requests)])
def draft(payload: DraftRequest):
    result = db.create_draft(payload.asset_id)
    if result is None:
        raise HTTPException(404, detail="Asset not found")
    return result


@app.post("/api/reports/{report_id}/approve", dependencies=[Depends(auth), Depends(limit_requests)])
def approve(report_id: str, payload: ApprovalRequest):
    if payload.confirmation != "I_REVIEWED_THIS_DEMO_REPORT":
        raise HTTPException(422, detail="Explicit review confirmation required")
    previous = db.get_report(report_id)
    if not previous:
        raise HTTPException(404, detail="Report not found")
    if previous["status"] == "approved":
        raise HTTPException(409, detail="Already approved")
    return db.approve_report(report_id)


if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/{path:path}", include_in_schema=False)
    def client_side_router(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, detail="API route not found")
        target = (STATIC_DIR / path).resolve()
        if target.is_file() and STATIC_DIR.resolve() in target.parents:
            return FileResponse(target)
        return FileResponse(STATIC_DIR / "index.html")

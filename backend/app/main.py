"""Owner: M1. FastAPI bootstrap. Registers EVERY member's router up front so no
one has to edit this file when they implement their endpoints (scaffold contract)."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, auth, cases, documents, forms, run, voice
from app.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Knowledge-base ingestion runs as a BackgroundTask, which dies with the
    process. A restart mid-ingestion would otherwise strand rows in 'processing'
    forever, with no way for an admin to retry them."""
    try:
        from app.db.session import SessionLocal
        from app.repositories import knowledge as knowledge_repo

        with SessionLocal() as db:
            reset = knowledge_repo.fail_stale_processing(db)
        if reset:
            logger.warning("Reset %d knowledge document(s) stranded in 'processing'.", reset)
    except Exception:  # noqa: BLE001 — never block startup on housekeeping
        logger.warning("Could not sweep stranded ingestions.", exc_info=True)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def vary_on_language(request, call_next):
    """Advertise that responses differ by X-Language.

    Case bodies are translated per request. Without this, any shared cache —
    a CDN, a proxy, the browser's own HTTP cache — is entitled to serve a
    Sinhala body to a subsequent English request for the same URL.
    """
    response = await call_next(request)
    existing = response.headers.get("Vary")
    response.headers["Vary"] = f"{existing}, X-Language" if existing else "X-Language"
    return response

# Pre-registered routers (one per domain owner)
app.include_router(auth.router)       # Auth
app.include_router(cases.router)      # M1
app.include_router(run.router)        # M2
app.include_router(documents.router)  # M5
app.include_router(forms.router)      # M5
app.include_router(admin.router)      # M6 — knowledge base (admin only)
app.include_router(voice.router)      # Voice input (speech-to-text fallback)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "app": settings.app_name}

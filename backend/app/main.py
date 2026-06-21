"""Owner: M1. FastAPI bootstrap. Registers EVERY member's router up front so no
one has to edit this file when they implement their endpoints (scaffold contract)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, cases, documents, forms, run
from app.config import settings

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pre-registered routers (one per domain owner)
app.include_router(auth.router)       # Auth
app.include_router(cases.router)      # M1
app.include_router(run.router)        # M2
app.include_router(documents.router)  # M5
app.include_router(forms.router)      # M5


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "app": settings.app_name}

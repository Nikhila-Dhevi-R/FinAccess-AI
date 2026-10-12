"""
FinAccess AI — FastAPI Backend
Main application entry point with /api/v1 versioning and backward-compatible routing.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import get_settings
from database import engine, Base, ensure_schema
from routers import sessions, forms, confirmations, schemes, guidance, fraud, auth

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all database tables on startup."""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    ensure_schema(engine)
    print(f"[OK] FinAccess AI backend started - DB: {settings.DATABASE_URL}")
    yield
    print("[INFO] FinAccess AI backend shutting down")


app = FastAPI(
    title="FinAccess AI",
    version=settings.APP_VERSION,
    description="Multilingual voice-first financial inclusion platform for elderly, illiterate, and low-literacy users in India",
    lifespan=lifespan,
)

# ─── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── API v1 Router ───────────────────────────────────────────────────────────
v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(sessions.router)
v1_router.include_router(forms.router)
v1_router.include_router(confirmations.router)
v1_router.include_router(schemes.router)
v1_router.include_router(guidance.router)
v1_router.include_router(fraud.router)
v1_router.include_router(auth.router)
app.include_router(v1_router)

# ─── Root backward-compatibility routers ─────────────────────────────────────
app.include_router(sessions.router)
app.include_router(forms.router)
app.include_router(confirmations.router)
app.include_router(schemes.router)
app.include_router(guidance.router)
app.include_router(fraud.router)
app.include_router(auth.router)

# ─── Static files (uploads) ──────────────────────────────────────────────────
if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


@app.get("/")
def root():
    return {
        "app": "FinAccess AI",
        "version": settings.APP_VERSION,
        "api_v1": "/api/v1",
        "status": "running",
        "tagline": "Speak. Understand. Complete.",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

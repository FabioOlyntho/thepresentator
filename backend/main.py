"""
The Presentator — FastAPI Backend

Professional presentation generation from documents via Gemini AI.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import init_db
from backend.routes import health, jobs, download, brands, ws

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("Starting The Presentator backend...")
    settings.ensure_dirs()
    await init_db()
    logger.info("Database initialized")
    logger.info("API key: %s", "configured" if settings.GEMINI_API_KEY else "NOT SET")
    yield
    logger.info("Shutting down The Presentator backend")


app = FastAPI(
    title="The Presentator",
    description="Professional presentation generation from documents",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
app.include_router(download.router, prefix="/api/v1", tags=["download"])
app.include_router(brands.router, prefix="/api/v1", tags=["brands"])
app.include_router(ws.router, prefix="/api/v1", tags=["websocket"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )

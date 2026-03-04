"""
Health — API health check endpoint.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "The Presentator",
        "version": "1.0.0",
    }

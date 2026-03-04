"""
Job Manager — Background task orchestration and state machine.
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import async_session
from backend.models import Job, JobSlide

logger = logging.getLogger(__name__)

# In-memory progress tracking (job_id → list of ProgressEvent dicts)
_progress: dict[str, list[dict]] = defaultdict(list)

# Active WebSocket connections (job_id → set of WebSocket)
_ws_connections: dict[str, set] = defaultdict(set)


def report_progress(job_id: str, step: str, progress: int, message: str):
    """Report progress for a job (called from pipeline thread)."""
    event = {"step": step, "progress": progress, "message": message}
    _progress[job_id].append(event)

    # Broadcast to connected WebSockets (non-blocking)
    for ws in list(_ws_connections.get(job_id, set())):
        try:
            asyncio.get_event_loop().call_soon_threadsafe(
                asyncio.ensure_future,
                ws.send_json(event),
            )
        except Exception:
            pass  # WebSocket may be closed


def get_progress(job_id: str) -> list[dict]:
    """Get all progress events for a job."""
    return list(_progress.get(job_id, []))


def register_ws(job_id: str, ws):
    """Register a WebSocket connection for progress updates."""
    _ws_connections[job_id].add(ws)


def unregister_ws(job_id: str, ws):
    """Unregister a WebSocket connection."""
    _ws_connections[job_id].discard(ws)
    if not _ws_connections[job_id]:
        del _ws_connections[job_id]


async def update_job_status(
    job_id: str,
    status: str,
    error_message: str | None = None,
    output_pptx_path: str | None = None,
    output_specs_path: str | None = None,
    title: str | None = None,
    time_total: float | None = None,
):
    """Update job status in the database."""
    async with async_session() as session:
        values = {
            "status": status,
            "updated_at": datetime.now(timezone.utc),
        }
        if error_message is not None:
            values["error_message"] = error_message
        if output_pptx_path is not None:
            values["output_pptx_path"] = output_pptx_path
        if output_specs_path is not None:
            values["output_specs_path"] = output_specs_path
        if title is not None:
            values["title"] = title
        if time_total is not None:
            values["time_total"] = time_total

        await session.execute(
            update(Job).where(Job.id == job_id).values(**values)
        )
        await session.commit()


async def save_job_slides(job_id: str, slides_info: list[dict]):
    """Save slide metadata for a completed job."""
    async with async_session() as session:
        for info in slides_info:
            slide = JobSlide(
                job_id=job_id,
                slide_number=info.get("number", 0),
                slide_type=info.get("type", "content"),
                title=info.get("title", ""),
            )
            session.add(slide)
        await session.commit()


def clear_progress(job_id: str):
    """Clear in-memory progress data for a completed job."""
    _progress.pop(job_id, None)

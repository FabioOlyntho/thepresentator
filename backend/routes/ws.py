"""
WebSocket — Real-time progress updates for jobs.
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from backend.database import async_session
from backend.models import Job
from backend.services.job_manager import register_ws, unregister_ws, get_progress

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/jobs/{job_id}")
async def job_progress_ws(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time job progress updates."""
    await websocket.accept()

    # Verify job exists
    async with async_session() as session:
        result = await session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            await websocket.send_json({"error": "Job not found"})
            await websocket.close()
            return

        # Send existing progress events (replay)
        events = get_progress(job_id)
        for event in events:
            await websocket.send_json(event)

        # If job is already completed/failed, send final status and close
        if job.status in ("completed", "failed"):
            await websocket.send_json({
                "step": job.status,
                "progress": 100 if job.status == "completed" else 0,
                "message": job.error_message or "Complete",
            })
            await websocket.close()
            return

    # Register for live updates
    register_ws(job_id, websocket)

    try:
        # Keep connection alive until client disconnects or job completes
        while True:
            # Wait for client messages (ping/pong or close)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        logger.debug("WebSocket disconnected for job %s", job_id)
    finally:
        unregister_ws(job_id, websocket)

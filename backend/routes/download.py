"""
Download — File download endpoints for generated presentations.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Job

router = APIRouter()


@router.get("/jobs/{job_id}/download")
async def download_pptx(job_id: str, db: AsyncSession = Depends(get_db)):
    """Download the generated PPTX file."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "completed":
        raise HTTPException(status_code=409, detail=f"Job is {job.status}, not completed")

    if not job.output_pptx_path or not Path(job.output_pptx_path).exists():
        raise HTTPException(status_code=404, detail="Output file not found")

    filename = f"{job.title or 'presentation'}.pptx"
    # Sanitize filename
    filename = "".join(c if c.isalnum() or c in (" ", "-", "_", ".") else "_" for c in filename)

    return FileResponse(
        path=job.output_pptx_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=filename,
    )


@router.get("/jobs/{job_id}/specs")
async def download_specs(job_id: str, db: AsyncSession = Depends(get_db)):
    """Download the slide specs JSON file."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.output_specs_path or not Path(job.output_specs_path).exists():
        raise HTTPException(status_code=404, detail="Specs file not found")

    return FileResponse(
        path=job.output_specs_path,
        media_type="application/json",
        filename=f"{job.title or 'specs'}.json",
    )

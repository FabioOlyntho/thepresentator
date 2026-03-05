"""
Jobs — CRUD endpoints for presentation generation jobs.
"""

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.config import settings
from backend.database import get_db
from backend.models import Job, JobSlide
from backend.schemas import JobOptions, JobResponse, JobListResponse
from backend.services.job_manager import get_progress, clear_progress
from backend.services.pipeline_service import run_generation
from backend.services.storage_service import save_upload, cleanup_job_files

logger = logging.getLogger(__name__)

router = APIRouter()

VALID_MODES = {"editable", "full_slide", "notebooklm", "ocr_editable", "pdnob", "translate"}


@router.post("/jobs", response_model=JobResponse, status_code=201)
async def create_job(
    file: UploadFile = File(...),
    options: str = Form(default="{}"),
    db: AsyncSession = Depends(get_db),
):
    """Create a new presentation generation job."""
    # Parse options JSON
    try:
        opts = JobOptions(**json.loads(options))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid options JSON: {e}")

    if opts.mode not in VALID_MODES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid mode: {opts.mode}. Valid: {', '.join(sorted(VALID_MODES))}",
        )

    if not settings.GEMINI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY not configured. Set it in .env file.",
        )

    # Create job record
    job = Job(
        status="pending",
        mode=opts.mode,
        title=opts.title,
        language=opts.language,
        target_language=opts.target_language,
        slide_count=opts.slide_count,
        prompt=opts.prompt,
        brand_kit_id=opts.brand_kit_id,
        input_filename=file.filename or "upload",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Save uploaded file
    try:
        input_path = await save_upload(file, job.id)
        job.input_path = input_path
        await db.commit()
    except ValueError as e:
        job.status = "failed"
        job.error_message = str(e)
        await db.commit()
        raise HTTPException(status_code=422, detail=str(e))

    # Resolve brand config path
    brand_path = None
    if opts.brand_kit_id:
        brand_file = settings.BRANDS_DIR / f"{opts.brand_kit_id}.json"
        if brand_file.exists():
            brand_path = str(brand_file)

    # Launch pipeline in background
    asyncio.create_task(
        run_generation(
            job_id=job.id,
            input_path=input_path,
            mode=opts.mode,
            title=opts.title,
            language=opts.language,
            target_language=opts.target_language,
            slide_count=opts.slide_count,
            prompt=opts.prompt,
            model=opts.model,
            brand_path=brand_path or settings.DEFAULT_BRAND_PATH,
            pdnob_level=opts.pdnob_level,
        )
    )

    # Re-fetch with eager loading for response serialization
    result = await db.execute(
        select(Job).options(selectinload(Job.slides)).where(Job.id == job.id)
    )
    return result.scalar_one()


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    status: str | None = None,
    mode: str | None = None,
    search: str | None = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List jobs with optional filtering."""
    query = select(Job).options(selectinload(Job.slides))

    if status:
        query = query.where(Job.status == status)
    if mode:
        query = query.where(Job.mode == mode)
    if search:
        query = query.where(Job.title.ilike(f"%{search}%"))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = query.order_by(desc(Job.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    jobs = result.scalars().all()

    return JobListResponse(jobs=jobs, total=total)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get job details including slides."""
    result = await db.execute(
        select(Job).options(selectinload(Job.slides)).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/progress")
async def get_job_progress(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get progress events for a job (polling fallback for WebSocket)."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    events = get_progress(job_id)
    return {
        "job_id": job_id,
        "status": job.status,
        "events": events,
    }


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a job and its files."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Clean up files
    cleanup_job_files(job_id)
    clear_progress(job_id)

    await db.delete(job)
    await db.commit()

    return {"detail": "Job deleted"}


@router.patch("/jobs/{job_id}/pin")
async def toggle_pin(job_id: str, db: AsyncSession = Depends(get_db)):
    """Toggle pinned status for a job."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.pinned = not job.pinned
    await db.commit()

    return {"pinned": job.pinned}

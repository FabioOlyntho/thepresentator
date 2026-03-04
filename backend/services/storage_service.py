"""
Storage Service — File upload, download, and cleanup.
"""

import logging
import shutil
from pathlib import Path

from fastapi import UploadFile

from backend.config import settings

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md", ".pptx"}


async def save_upload(file: UploadFile, job_id: str) -> str:
    """
    Save an uploaded file to the upload directory.

    Returns the absolute path to the saved file.
    """
    settings.ensure_dirs()

    ext = Path(file.filename or "upload").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {ext}. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    job_dir = settings.UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(file.filename or "upload").name
    dest = job_dir / safe_name

    with open(dest, "wb") as f:
        content = await file.read()
        if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise ValueError(
                f"File too large ({len(content) / 1024 / 1024:.1f} MB). "
                f"Maximum: {settings.MAX_UPLOAD_SIZE_MB} MB"
            )
        f.write(content)

    logger.info("Saved upload: %s (%d bytes)", dest, len(content))
    return str(dest)


def get_output_path(job_id: str, filename: str) -> str:
    """Get the output path for a job's generated file."""
    settings.ensure_dirs()
    job_dir = settings.OUTPUT_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    return str(job_dir / filename)


def cleanup_job_files(job_id: str):
    """Remove all files for a job (uploads + outputs)."""
    for base_dir in [settings.UPLOAD_DIR, settings.OUTPUT_DIR]:
        job_dir = base_dir / job_id
        if job_dir.exists():
            shutil.rmtree(job_dir)
            logger.info("Cleaned up: %s", job_dir)

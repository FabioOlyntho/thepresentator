"""
Pipeline Service — Async wrapper for presentation generation pipelines.

Runs blocking CLI pipelines in a thread pool and reports progress via callbacks.
"""

import asyncio
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from backend.config import settings
from backend.services.job_manager import (
    report_progress,
    update_job_status,
    save_job_slides,
)

logger = logging.getLogger(__name__)

# Thread pool for blocking pipeline operations
_executor = ThreadPoolExecutor(max_workers=settings.MAX_CONCURRENT_JOBS)

# Ensure scripts/ is importable
_scripts_dir = str(Path(__file__).parent.parent.parent / "scripts")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)


def _run_pipeline_sync(
    job_id: str,
    input_path: str,
    mode: str,
    title: str | None,
    language: str | None,
    target_language: str | None,
    slide_count: int,
    prompt: str | None,
    model: str,
    brand_path: str | None,
    output_dir: str,
    ocr_engine: str = "gemini",
) -> dict:
    """Run the presentation generation pipeline synchronously (called in thread pool)."""
    from presentation_factory import run_pipeline

    report_progress(job_id, "extracting", 10, "Extracting content...")

    # Determine mode flags
    editable_mode = mode == "editable"
    full_slide_mode = mode == "full_slide"
    notebooklm_mode = mode == "notebooklm"
    ocr_editable_mode = mode == "ocr_editable"
    pdnob_mode = mode == "pdnob"
    translate_to = target_language if mode != "translate" else None

    # For translate-only mode, we still run editable pipeline first
    if mode == "translate":
        editable_mode = True

    report_progress(job_id, "generating", 25, "Generating slide specifications...")

    result = run_pipeline(
        input_file=input_path,
        title=title,
        language=language,
        slide_count=slide_count,
        objective=prompt or "Create an insightful executive presentation",
        output_dir=output_dir,
        brand_path=brand_path,
        model=model,
        gemini_api_key=settings.GEMINI_API_KEY,
        generate_images=not editable_mode,
        full_slide_mode=full_slide_mode,
        editable_mode=editable_mode,
        notebooklm_mode=notebooklm_mode,
        ocr_editable_mode=ocr_editable_mode,
        translate_to=translate_to,
        ocr_engine=ocr_engine,
    )

    return result


async def run_generation(
    job_id: str,
    input_path: str,
    mode: str,
    title: str | None = None,
    language: str | None = None,
    target_language: str | None = None,
    slide_count: int = 8,
    prompt: str | None = None,
    model: str = "gemini-2.5-flash",
    brand_path: str | None = None,
    ocr_engine: str = "gemini",
):
    """
    Run the generation pipeline asynchronously.

    Updates job status and reports progress throughout execution.
    """
    output_dir = str(settings.OUTPUT_DIR / job_id)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    try:
        await update_job_status(job_id, "processing")
        report_progress(job_id, "uploading", 5, "File received, starting pipeline...")

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor,
            _run_pipeline_sync,
            job_id,
            input_path,
            mode,
            title,
            language,
            target_language,
            slide_count,
            prompt,
            model,
            brand_path,
            output_dir,
            ocr_engine,
        )

        if result.get("success"):
            report_progress(job_id, "completed", 100,
                            f"Done! {result['metadata'].get('total_slides', '?')} slides in {result['timing'].get('total', 0):.1f}s")

            await update_job_status(
                job_id,
                status="completed",
                output_pptx_path=result["files"].get("pptx") or result["files"].get("pptx_translated"),
                output_specs_path=result["files"].get("specs_json"),
                title=result["metadata"].get("title"),
                time_total=result["timing"].get("total"),
            )

            # Save slide metadata if specs JSON exists
            specs_path = result["files"].get("specs_json")
            if specs_path and Path(specs_path).exists():
                try:
                    specs_data = json.loads(Path(specs_path).read_text(encoding="utf-8"))
                    slides_info = [
                        {"number": s.get("number", i + 1), "type": s.get("type", "content"), "title": s.get("title", "")}
                        for i, s in enumerate(specs_data.get("slides", []))
                    ]
                    await save_job_slides(job_id, slides_info)
                except Exception as e:
                    logger.warning("Could not save slide metadata: %s", e)

        else:
            error = result.get("error", "Unknown pipeline error")
            report_progress(job_id, "failed", 0, f"Error: {error}")
            await update_job_status(job_id, status="failed", error_message=error)

    except Exception as e:
        logger.exception("Pipeline failed for job %s", job_id)
        report_progress(job_id, "failed", 0, f"Error: {str(e)}")
        await update_job_status(job_id, status="failed", error_message=str(e))

"""
Presentation Factory — Main orchestrator for professional presentation generation.

Pipeline: PDF/DOCX/TXT/MD/PPTX → Content Extraction → Gemini Analysis → Slide Specs → AI Images → PPTX

Six modes:
  (default):       Editable — Programmatic Recodme layouts (no AI images, instant)
  --full-slide:    Each slide is a COMPLETE AI-rendered image (non-editable)
  --composite:     AI illustrations + python-pptx text layout (legacy approach)
  --notebooklm:    Delegate to NotebookLM for best visual quality (requires auth)
  --ocr-editable:  NotebookLM → OCR → editable Recodme (best quality + editable)
  --translate-to:  Translate output PPTX to another language (post-processing)

Usage:
    python presentation_factory.py <input_file> [options]

Options:
    --title TEXT         Presentation title override
    --language ES|EN     Force language (auto-detected by default)
    --slides N           Target slide count (default: 8)
    --objective TEXT      Presentation objective
    --output PATH        Output directory (default: ./output)
    --brand PATH         Brand config JSON (default: config/brand.json)
    --model TEXT          Gemini model (default: gemini-2.5-flash)
    --no-images          Skip AI image generation (gradient-only backgrounds)
    --image-model TEXT   Image generation model (default: gemini-3-pro-image-preview)
    --full-slide         Use full-slide mode (non-editable AI images)
    --composite          Use composite mode (AI illustrations + pptx text layout)
    --notebooklm         Use NotebookLM for generation (best quality, requires auth)
    --ocr-editable       NotebookLM quality + OCR conversion to editable Recodme PPTX
    --translate-to CODE  Translate output to target language (ES, EN, FR, DE, PT, IT)
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Load .env from project root
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    load_dotenv(str(_env_path))

from content_extractor import extract_content, ExtractedContent
from gemini_client import GeminiClient, PresentationSpec
from image_generator import generate_slide_images
from slide_builder import SlideBuilder, BrandConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent


def sanitize_filename(name: str) -> str:
    """Create a safe filename from a title."""
    safe = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in name)
    return safe.strip()[:80]


def _apply_translation(
    result: dict,
    translate_to: str,
    source_lang: str,
    api_key: str | None,
    model: str,
    start_time: float,
) -> dict:
    """Apply translation post-processing to a successful pipeline result."""
    logger.info("=" * 60)
    logger.info("POST-PROCESSING: Translation → %s", translate_to)
    logger.info("=" * 60)

    from translator import translate_pptx

    source_pptx = result["files"]["pptx"]
    translated_path = source_pptx.replace(".pptx", f"_{translate_to.lower()}.pptx")

    t0 = time.time()
    trans_result = translate_pptx(
        input_pptx=source_pptx,
        output_pptx=translated_path,
        source_lang=source_lang,
        target_lang=translate_to,
        api_key=api_key,
        model=model,
    )
    result["timing"]["translation"] = round(time.time() - t0, 2)
    result["timing"]["total"] = round(time.time() - start_time, 2)

    if trans_result["success"]:
        result["files"]["pptx_translated"] = trans_result["files"]["pptx"]
        result["files"]["pptx_original"] = source_pptx
        result["metadata"]["translated_to"] = translate_to
        result["metadata"]["translation_changed"] = trans_result["metadata"]["changed_runs"]
        logger.info("Translation complete: %s", translated_path)
    else:
        logger.warning("Translation failed: %s", trans_result.get("error"))
        result["metadata"]["translation_error"] = trans_result.get("error", "Unknown")

    return result


def run_pipeline(
    input_file: str,
    title: str | None = None,
    language: str | None = None,
    slide_count: int = 8,
    objective: str = "Create an insightful executive presentation from this document",
    output_dir: str | None = None,
    brand_path: str | None = None,
    model: str = "gemini-2.5-flash",
    gemini_api_key: str | None = None,
    generate_images: bool = True,
    image_model: str = "gemini-3-pro-image-preview",
    full_slide_mode: bool = True,
    editable_mode: bool = True,
    notebooklm_mode: bool = False,
    ocr_editable_mode: bool = False,
    translate_to: str | None = None,
    ocr_engine: str = "gemini",
) -> dict:
    """
    Run the complete presentation generation pipeline.

    Args:
        input_file: Path to PDF, DOCX, TXT, MD, or PPTX file
        title: Optional title override
        language: Force "ES" or "EN" (auto-detected if None)
        slide_count: Target number of slides (4-15)
        objective: Presentation objective description
        output_dir: Output directory path
        brand_path: Path to brand config JSON
        model: Gemini model name
        gemini_api_key: Gemini API key (or set GEMINI_API_KEY env var)
        generate_images: Whether to generate AI images for slides
        image_model: Gemini model for image generation
        full_slide_mode: True = full-slide images (default), False = composite
        editable_mode: True = editable slides (default), overrides full_slide_mode
        notebooklm_mode: True = delegate to NotebookLM (best quality, requires auth)
        ocr_editable_mode: True = NotebookLM + OCR → editable Recodme (best of both)
        translate_to: Target language code for post-generation translation (e.g., "EN")

    Returns:
        dict with paths to generated files and metadata
    """
    start_time = time.time()
    output_dir = Path(output_dir or PROJECT_ROOT / "output")
    output_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "input_file": input_file,
        "success": False,
        "files": {},
        "metadata": {},
        "timing": {},
    }

    # ─── Step 1: Extract Content ───────────────────────────────
    logger.info("=" * 60)
    logger.info("STEP 1: Content Extraction")
    logger.info("=" * 60)

    t0 = time.time()
    try:
        content = extract_content(input_file, gemini_api_key=gemini_api_key)
    except RuntimeError as e:
        if "Image-based PDF" in str(e):
            logger.warning("Image-based PDF detected. Attempting with Gemini OCR...")
            if not gemini_api_key:
                gemini_api_key = os.environ.get("GEMINI_API_KEY")
            if not gemini_api_key:
                logger.error(
                    "Cannot process image-based PDF without GEMINI_API_KEY. "
                    "Set the environment variable and try again."
                )
                result["error"] = str(e)
                return result
            content = extract_content(input_file, gemini_api_key=gemini_api_key)
        else:
            raise

    result["timing"]["extraction"] = round(time.time() - t0, 2)

    logger.info("Extracted: %s", content.summary().replace("\n", " | "))

    if content.word_count < 50:
        logger.error("Extracted content too short (%d words). Check the input file.", content.word_count)
        result["error"] = f"Content too short: {content.word_count} words"
        return result

    # Use auto-detected language if not specified
    lang = language or content.language
    result["metadata"]["language"] = lang
    result["metadata"]["word_count"] = content.word_count
    result["metadata"]["page_count"] = content.page_count

    # ─── NotebookLM Mode: Delegate entirely ────────────────────
    if notebooklm_mode or ocr_editable_mode:
        if not input_file.lower().endswith(".pdf"):
            logger.error("NotebookLM mode requires PDF input. Got: %s", input_file)
            result["error"] = "NotebookLM mode only supports PDF files"
            return result

        mode_label = "OCR+EDITABLE" if ocr_editable_mode else "NOTEBOOKLM"
        logger.info("=" * 60)
        logger.info("%s MODE: Delegating to NotebookLM engine", mode_label)
        logger.info("=" * 60)

        from notebooklm_client import NotebookLMPipeline

        if not NotebookLMPipeline.is_authenticated():
            logger.error(
                "NotebookLM not authenticated. Run: "
                "venv/Scripts/python.exe -m notebooklm_tools.cli.main login"
            )
            result["error"] = "NotebookLM auth not found. Run 'nlm login' first."
            return result

        pipeline = NotebookLMPipeline()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = sanitize_filename(title or content.filename)
        pptx_path = output_dir / f"{safe_name}_{timestamp}.pptx"

        downloaded = pipeline.generate_from_pdf(
            pdf_path=input_file,
            output_path=str(pptx_path),
            prompt=objective,
            slide_count=slide_count,
            language=lang,
        )

        if not downloaded or not Path(downloaded).exists():
            total_time = round(time.time() - start_time, 2)
            result["timing"]["total"] = total_time
            result["error"] = "NotebookLM generation failed"
            logger.error("NotebookLM generation failed after %.1fs", total_time)
            return result

        # ── OCR+Editable: Convert NotebookLM image PPTX to editable ──
        if ocr_editable_mode:
            logger.info("=" * 60)
            logger.info("OCR CONVERSION: Image PPTX → Editable Recodme")
            logger.info("=" * 60)

            from ocr_converter import convert_notebooklm_to_editable

            editable_path = str(pptx_path).replace(".pptx", "_editable.pptx")
            ocr_result = convert_notebooklm_to_editable(
                input_pptx=downloaded,
                output_pptx=editable_path,
                api_key=gemini_api_key,
                brand_path=brand_path,
                model=model,
                ocr_engine=ocr_engine,
            )

            total_time = round(time.time() - start_time, 2)
            result["timing"]["total"] = total_time

            if ocr_result["success"]:
                result["success"] = True
                result["files"]["pptx"] = ocr_result["files"]["pptx"]
                result["files"]["pptx_notebooklm"] = downloaded  # Keep original
                result["files"]["specs_json"] = ocr_result["files"].get("specs_json", "")
                result["metadata"]["title"] = ocr_result["metadata"].get("title", title or content.filename)
                result["metadata"]["mode"] = "ocr_editable"
                result["metadata"]["total_slides"] = ocr_result["metadata"].get("total_slides", "N/A")
                result["timing"].update(ocr_result["timing"])

                logger.info("=" * 60)
                logger.info("COMPLETE (OCR+Editable)")
                logger.info("=" * 60)
                logger.info("Title: %s", result["metadata"]["title"])
                logger.info("Slides: %s", result["metadata"]["total_slides"])
                logger.info("Time: %.1fs", total_time)
                logger.info("PPTX (editable): %s", editable_path)
                logger.info("PPTX (original): %s", downloaded)
            else:
                result["error"] = f"OCR conversion failed: {ocr_result.get('error', 'Unknown')}"
                logger.error("OCR conversion failed: %s", ocr_result.get("error"))

            if translate_to and result["success"]:
                result = _apply_translation(result, translate_to, lang, gemini_api_key, model, start_time)

            return result

        # Plain NotebookLM mode (no OCR)
        total_time = round(time.time() - start_time, 2)
        result["timing"]["total"] = total_time
        result["success"] = True
        result["files"]["pptx"] = downloaded
        result["metadata"]["title"] = title or content.filename
        result["metadata"]["mode"] = "notebooklm"
        result["metadata"]["total_slides"] = "N/A (NotebookLM)"

        logger.info("=" * 60)
        logger.info("COMPLETE (NotebookLM)")
        logger.info("=" * 60)
        logger.info("Title: %s", result["metadata"]["title"])
        logger.info("Language: %s", lang)
        logger.info("Time: %.1fs", total_time)
        logger.info("PPTX: %s", downloaded)

        if translate_to and result["success"]:
            result = _apply_translation(result, translate_to, lang, gemini_api_key, model, start_time)

        return result

    # ─── Step 2: Generate Slide Specs ──────────────────────────
    logger.info("=" * 60)
    logger.info("STEP 2: Slide Spec Generation (Gemini)")
    logger.info("=" * 60)

    t0 = time.time()
    client = GeminiClient(api_key=gemini_api_key, model=model)
    mode = "LIVE API" if not client.is_mock else "MOCK"
    logger.info("Mode: %s | Model: %s", mode, model)

    spec = client.generate_slide_specs(
        content=content.text,
        filename=content.filename,
        language=lang,
        objective=objective,
        slide_count=slide_count,
    )

    if title:
        spec.title = title
        spec.slides[0].title = title

    result["timing"]["generation"] = round(time.time() - t0, 2)
    result["metadata"]["title"] = spec.title
    result["metadata"]["total_slides"] = spec.total_slides
    result["metadata"]["mode"] = mode

    logger.info("Generated %d slides: '%s'", spec.total_slides, spec.title)

    # Save specs JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = sanitize_filename(spec.title or content.filename)
    specs_path = output_dir / f"{safe_name}_{timestamp}_specs.json"
    specs_path.write_text(client.specs_to_json(spec), encoding="utf-8")
    result["files"]["specs_json"] = str(specs_path)
    logger.info("Specs saved: %s", specs_path.name)

    # ─── Load Brand Config (used by image gen + PPTX build) ──
    if brand_path:
        brand = BrandConfig.from_json(brand_path)
    else:
        default_brand = PROJECT_ROOT / "config" / "brand.json"
        if default_brand.exists():
            brand = BrandConfig.from_json(str(default_brand))
        else:
            brand = BrandConfig.default()

    # ─── Step 2.5: Generate AI Images ─────────────────────────
    image_paths = {}
    if generate_images:
        if editable_mode:
            # Programmatic Recodme layouts — no AI images needed
            logger.info("=" * 60)
            logger.info("STEP 2.5: Skipping AI images (programmatic Recodme layouts)")
            logger.info("=" * 60)
            result["timing"]["image_generation"] = 0
            result["metadata"]["images_generated"] = 0
            result["metadata"]["image_mode"] = "recodme_programmatic"
        else:
            if full_slide_mode:
                mode_label = "Full-Slide"
            else:
                mode_label = "Illustration (Composite)"
            logger.info("=" * 60)
            logger.info("STEP 2.5: AI Image Generation — %s", mode_label)
            logger.info("=" * 60)

            t0 = time.time()
            images_dir = output_dir / "images" / timestamp
            api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY")

            if api_key:
                est_per_slide = 25 if full_slide_mode else 8
                est_total = est_per_slide * len(spec.slides)
                logger.info(
                    "Model: %s | Estimated: ~%ds/slide, ~%ds total",
                    image_model, est_per_slide, est_total,
                )

                image_paths = generate_slide_images(
                    slides=spec.slides,
                    output_dir=str(images_dir),
                    api_key=api_key,
                    model=image_model,
                    brand_config=brand,
                    full_slide_mode=full_slide_mode,
                    editable_mode=False,
                )
                generated_count = sum(1 for v in image_paths.values() if v is not None)
                result["timing"]["image_generation"] = round(time.time() - t0, 2)
                result["metadata"]["images_generated"] = generated_count
                result["metadata"]["images_total"] = len(spec.slides)
                result["metadata"]["image_mode"] = "full_slide" if full_slide_mode else "composite"
                logger.info(
                    "Images: %d/%d generated in %.1fs",
                    generated_count, len(spec.slides), result["timing"]["image_generation"],
                )
            else:
                logger.warning("No API key — skipping image generation (gradient-only mode)")
                result["timing"]["image_generation"] = 0
                result["metadata"]["images_generated"] = 0
    else:
        logger.info("Image generation disabled (--no-images)")
        result["timing"]["image_generation"] = 0
        result["metadata"]["images_generated"] = 0

    # ─── Step 3: Build PPTX ────────────────────────────────────
    logger.info("=" * 60)
    logger.info("STEP 3: PPTX Generation")
    logger.info("=" * 60)

    t0 = time.time()

    builder = SlideBuilder(brand, image_paths=image_paths, full_slide_mode=full_slide_mode, editable_mode=editable_mode)
    builder.build_presentation(spec)

    pptx_path = output_dir / f"{safe_name}_{timestamp}.pptx"
    builder.save(str(pptx_path))

    result["timing"]["building"] = round(time.time() - t0, 2)
    result["files"]["pptx"] = str(pptx_path)

    # ─── Summary ───────────────────────────────────────────────
    total_time = round(time.time() - start_time, 2)
    result["timing"]["total"] = total_time
    result["success"] = True

    logger.info("=" * 60)
    logger.info("COMPLETE")
    logger.info("=" * 60)
    logger.info("Title: %s", spec.title)
    logger.info("Slides: %d", spec.total_slides)
    logger.info("Language: %s", lang)
    logger.info("Mode: %s", mode)
    img_time = result["timing"].get("image_generation", 0)
    logger.info(
        "Time: %.1fs (extract=%.1fs, generate=%.1fs, images=%.1fs, build=%.1fs)",
        total_time, result["timing"]["extraction"],
        result["timing"]["generation"], img_time,
        result["timing"]["building"],
    )
    logger.info("PPTX: %s", pptx_path)
    logger.info("Specs: %s", specs_path)

    # Quality check
    logger.info("-" * 40)
    mode_str = "editable" if editable_mode else ("full-slide" if full_slide_mode else "composite")
    logger.info("Quality Check (mode=%s):", mode_str)
    for slide in spec.slides:
        words = len(slide.body.split()) if slide.body else 0
        has_image = bool(image_paths.get(slide.number))
        if editable_mode:
            status = "EDIT"
        elif full_slide_mode and has_image:
            status = "FULL"
        elif has_image:
            status = "IMG"
        elif slide.visual_concept:
            status = "GRAD"
        else:
            status = "WARN"
        img_label = "BG" if editable_mode and has_image else ("FULL" if full_slide_mode and has_image else ("YES" if has_image else "gradient"))
        logger.info(
            "  [%s] Slide %d (%s): %d words, image=%s",
            status, slide.number, slide.type, words, img_label,
        )

    # ─── Optional: Translation ───────────────────────────────
    if translate_to and result["success"]:
        result = _apply_translation(result, translate_to, lang, gemini_api_key, model, start_time)

    return result


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Presentation Factory — Recodme-branded presentation generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes (mutually exclusive):
  (default)      Editable — Programmatic Recodme layouts (no AI images, instant)
  --full-slide   Full-slide — each slide is a single AI image (non-editable)
  --composite    Composite — AI illustrations + pptx text layout (legacy)
  --notebooklm   NotebookLM — best visual quality (requires auth setup)
  --ocr-editable OCR+Editable — NotebookLM quality + editable Recodme output

Post-processing:
  --translate-to CODE  Translate output PPTX (ES, EN, FR, DE, PT, IT)

Examples:
  python presentation_factory.py document.pdf
  python presentation_factory.py document.pdf --slides 10 --language ES
  python presentation_factory.py document.pdf --full-slide     # non-editable AI images
  python presentation_factory.py document.pdf --notebooklm     # NotebookLM quality
  python presentation_factory.py document.pdf --ocr-editable   # best of both worlds
  python presentation_factory.py document.pdf --no-images      # gradient-only mode
  python presentation_factory.py document.pdf --translate-to EN # generate + translate
        """,
    )
    parser.add_argument("input_file", help="Path to PDF or DOCX file")
    parser.add_argument("--title", help="Presentation title override")
    parser.add_argument("--language", choices=["ES", "EN"], help="Force language")
    parser.add_argument("--slides", type=int, default=8, help="Target slide count (default: 8)")
    parser.add_argument("--objective", default="Create an insightful executive presentation",
                        help="Presentation objective")
    parser.add_argument("--output", help="Output directory")
    parser.add_argument("--brand", help="Brand config JSON path")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Gemini model")
    parser.add_argument("--no-images", action="store_true", help="Skip AI image generation")
    parser.add_argument("--image-model", default="gemini-3-pro-image-preview",
                        help="Model for image generation (default: gemini-3-pro-image-preview)")

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--full-slide", action="store_true",
                            help="Use full-slide mode (non-editable AI images)")
    mode_group.add_argument("--composite", action="store_true",
                            help="Use composite mode (AI illustrations + pptx text)")
    mode_group.add_argument("--notebooklm", action="store_true",
                            help="Use NotebookLM for generation (best quality, requires auth)")
    mode_group.add_argument("--ocr-editable", action="store_true",
                            help="NotebookLM quality + OCR → editable Recodme (best of both)")

    parser.add_argument("--ocr-engine", choices=["gemini", "docling"], default="gemini",
                        help="OCR engine for --ocr-editable mode: 'gemini' (API) or 'docling' (offline)")
    parser.add_argument("--translate-to",
                        help="Translate output PPTX to target language (ES, EN, FR, DE, PT, IT)")

    args = parser.parse_args()

    if not Path(args.input_file).exists():
        print(f"Error: File not found: {args.input_file}")
        sys.exit(1)

    # Determine mode: ocr-editable > notebooklm > editable (default) > full-slide > composite
    ocr_editable_mode = args.ocr_editable
    notebooklm_mode = args.notebooklm
    editable_mode = not args.full_slide and not args.composite and not args.notebooklm and not args.ocr_editable
    full_slide_mode = args.full_slide

    # Composite mode uses the old illustration model by default
    image_model = args.image_model
    if args.composite and image_model == "gemini-3-pro-image-preview":
        image_model = "gemini-2.5-flash-image"

    result = run_pipeline(
        input_file=args.input_file,
        title=args.title,
        language=args.language,
        slide_count=args.slides,
        objective=args.objective,
        output_dir=args.output,
        brand_path=args.brand,
        model=args.model,
        generate_images=not args.no_images,
        image_model=image_model,
        full_slide_mode=full_slide_mode,
        editable_mode=editable_mode,
        notebooklm_mode=notebooklm_mode,
        ocr_editable_mode=ocr_editable_mode,
        translate_to=args.translate_to,
        ocr_engine=args.ocr_engine,
    )

    if not result["success"]:
        print(f"\nError: {result.get('error', 'Unknown error')}")
        sys.exit(1)

    print(f"\nOutput: {result['files'].get('pptx', 'N/A')}")
    return result


if __name__ == "__main__":
    main()

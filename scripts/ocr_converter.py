"""
OCR Converter — Converts NotebookLM image-based PPTX to editable Recodme PPTX.

Pipeline:
  Image PPTX → Extract slide images (python-pptx)
  → Gemini Vision API (structured JSON extraction per slide)
  → SlideSpec objects (type, title, bullets, columns, etc.)
  → slide_builder.py with brand config → Editable PPTX

Usage:
    python scripts/ocr_converter.py input_notebooklm.pptx [--output output.pptx] [--brand config/brand.json]
"""

import argparse
import base64
import io
import json
import logging
import os
import sys
import time
from pathlib import Path

import requests
from pptx import Presentation

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# Ensure sibling modules are importable
_scripts_dir = str(Path(__file__).parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# Valid slide types (must match slide_builder.py's dispatcher)
VALID_SLIDE_TYPES = {"title", "section", "content", "comparison", "data", "quote", "conclusion"}


def load_ocr_prompt() -> str:
    """Load the OCR extraction prompt template."""
    path = PROMPTS_DIR / "ocr_extraction_prompt.txt"
    if not path.exists():
        raise FileNotFoundError(f"OCR prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def extract_slide_images(pptx_path: str) -> list[tuple[int, bytes]]:
    """
    Extract the primary image from each slide in a NotebookLM PPTX.

    NotebookLM slides are single full-bleed images (17.8" x 10.0").
    Each slide contains one picture shape covering the entire canvas.

    Args:
        pptx_path: Path to NotebookLM-generated PPTX file.

    Returns:
        List of (slide_number, image_bytes) tuples, 1-indexed.
    """
    prs = Presentation(pptx_path)
    results = []

    for idx, slide in enumerate(prs.slides, start=1):
        image_bytes = None
        largest_area = 0

        for shape in slide.shapes:
            if shape.shape_type == 13:  # MSO_SHAPE_TYPE.PICTURE
                # Pick the largest image on the slide (should be the full-bleed one)
                area = shape.width * shape.height
                if area > largest_area:
                    largest_area = area
                    image_bytes = shape.image.blob

        if image_bytes:
            results.append((idx, image_bytes))
            logger.info("Extracted image from slide %d (%d bytes)", idx, len(image_bytes))
        else:
            logger.warning("No image found on slide %d", idx)

    return results


def classify_slide_type(slide_number: int, total_slides: int, raw_type: str) -> str:
    """
    Validate and apply heuristic fallbacks for slide type classification.

    Args:
        slide_number: 1-indexed slide number.
        total_slides: Total number of slides.
        raw_type: The type returned by Gemini Vision.

    Returns:
        A valid slide type string.
    """
    if raw_type in VALID_SLIDE_TYPES:
        return raw_type

    # Heuristic fallbacks
    if slide_number == 1:
        return "title"
    if slide_number == total_slides:
        return "conclusion"
    return "content"


def extract_slide_content(
    image_bytes: bytes,
    slide_number: int,
    total_slides: int,
    api_key: str,
    model: str = "gemini-2.5-flash",
) -> dict:
    """
    Send a slide image to Gemini Vision and extract structured content.

    Args:
        image_bytes: Raw image bytes (PNG/JPEG).
        slide_number: 1-indexed slide number.
        total_slides: Total number of slides.
        api_key: Gemini API key.
        model: Gemini model for vision extraction.

    Returns:
        Dict with slide content fields matching SlideSpec.
    """
    prompt_template = load_ocr_prompt()
    prompt = prompt_template.replace("{slide_number}", str(slide_number))
    prompt = prompt.replace("{total_slides}", str(total_slides))

    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    # Detect MIME type from image header
    if image_bytes[:4] == b"\x89PNG":
        mime_type = "image/png"
    elif image_bytes[:2] == b"\xff\xd8":
        mime_type = "image/jpeg"
    else:
        mime_type = "image/png"  # Default

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": b64_image,
                    }
                },
            ]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 4096,
            "responseMimeType": "application/json",
        },
    }

    logger.info("OCR slide %d/%d via Gemini Vision...", slide_number, total_slides)
    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    if "candidates" not in data or not data["candidates"]:
        raise RuntimeError(f"Gemini returned no candidates for slide {slide_number}")

    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]

    # Parse JSON response
    try:
        content = json.loads(raw_text)
    except json.JSONDecodeError:
        # Try stripping markdown fences
        import re
        cleaned = raw_text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        content = json.loads(cleaned)

    # Validate and fix slide type
    raw_type = content.get("type", "content")
    content["type"] = classify_slide_type(slide_number, total_slides, raw_type)

    return content


def content_to_slidespec(content: dict, slide_number: int):
    """
    Convert extracted content dict to a SlideSpec object.

    Args:
        content: Dict from Gemini Vision extraction.
        slide_number: 1-indexed slide number.

    Returns:
        SlideSpec instance.
    """
    from gemini_client import SlideSpec

    return SlideSpec(
        number=slide_number,
        type=content.get("type", "content"),
        title=content.get("title", ""),
        subtitle=content.get("subtitle", ""),
        body=content.get("body", ""),
        bullet_points=content.get("bullet_points", []),
        visual_concept="",  # Not needed for editable mode
        speaker_notes=content.get("speaker_notes", ""),
        source_reference="",
        left_column=content.get("left_column", []),
        right_column=content.get("right_column", []),
        left_header=content.get("left_header", ""),
        right_header=content.get("right_header", ""),
        checkbox_items=content.get("checkbox_items", []),
    )


def convert_notebooklm_to_editable(
    input_pptx: str,
    output_pptx: str | None = None,
    api_key: str | None = None,
    brand_path: str | None = None,
    model: str = "gemini-2.5-flash",
) -> dict:
    """
    Full pipeline: NotebookLM image PPTX → OCR → editable Recodme PPTX.

    Args:
        input_pptx: Path to NotebookLM-generated PPTX.
        output_pptx: Output path for editable PPTX (auto-generated if None).
        api_key: Gemini API key (falls back to GEMINI_API_KEY env var).
        brand_path: Path to brand config JSON (uses default Recodme if None).
        model: Gemini model for vision extraction.

    Returns:
        Dict with success status, file paths, and metadata.
    """
    start_time = time.time()

    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {
            "success": False,
            "error": "No API key. Set GEMINI_API_KEY or pass api_key parameter.",
        }

    result = {
        "success": False,
        "files": {},
        "metadata": {},
        "timing": {},
    }

    # Step 1: Extract images from PPTX
    logger.info("Step 1: Extracting slide images from %s", input_pptx)
    t0 = time.time()
    slide_images = extract_slide_images(input_pptx)

    if not slide_images:
        return {
            "success": False,
            "error": "No images found in PPTX. Is this a NotebookLM presentation?",
        }

    result["timing"]["extraction"] = round(time.time() - t0, 2)
    total_slides = len(slide_images)
    logger.info("Found %d slide images", total_slides)

    # Step 2: OCR each slide via Gemini Vision
    logger.info("Step 2: OCR extraction via Gemini Vision")
    t0 = time.time()

    from gemini_client import PresentationSpec

    slide_specs = []
    for i, (slide_num, img_bytes) in enumerate(slide_images):
        # Rate limiting: pause between API calls (skip first)
        if i > 0:
            time.sleep(1.0)

        try:
            content = extract_slide_content(
                image_bytes=img_bytes,
                slide_number=slide_num,
                total_slides=total_slides,
                api_key=api_key,
                model=model,
            )
            spec = content_to_slidespec(content, slide_num)
            slide_specs.append(spec)
            logger.info(
                "  Slide %d [%s]: %s",
                slide_num, spec.type, spec.title[:60],
            )
        except Exception as e:
            logger.error("  Slide %d OCR failed: %s", slide_num, e)
            # Create a fallback content slide
            from gemini_client import SlideSpec
            fallback = SlideSpec(
                number=slide_num,
                type=classify_slide_type(slide_num, total_slides, ""),
                title=f"Slide {slide_num}",
                body="(OCR extraction failed for this slide)",
                speaker_notes="",
            )
            slide_specs.append(fallback)

    result["timing"]["ocr"] = round(time.time() - t0, 2)

    # Build PresentationSpec
    title = slide_specs[0].title if slide_specs else "Untitled"
    subtitle = slide_specs[0].subtitle if slide_specs else ""
    presentation_spec = PresentationSpec(
        title=title,
        subtitle=subtitle,
        language="auto",  # Preserved from original
        source_document=Path(input_pptx).name,
        themes=[],
        slides=slide_specs,
    )

    # Step 3: Build editable PPTX
    logger.info("Step 3: Building editable Recodme PPTX")
    t0 = time.time()

    from slide_builder import SlideBuilder, BrandConfig

    if brand_path:
        brand = BrandConfig.from_json(brand_path)
    else:
        default_brand = Path(__file__).parent.parent / "config" / "brand.json"
        if default_brand.exists():
            brand = BrandConfig.from_json(str(default_brand))
        else:
            brand = BrandConfig.default()

    builder = SlideBuilder(brand=brand, editable_mode=True)
    builder.build_presentation(presentation_spec)

    # Determine output path
    if not output_pptx:
        input_stem = Path(input_pptx).stem
        output_dir = Path(input_pptx).parent
        output_pptx = str(output_dir / f"{input_stem}_editable.pptx")

    builder.save(output_pptx)
    result["timing"]["building"] = round(time.time() - t0, 2)

    # Save specs JSON alongside
    specs_path = Path(output_pptx).with_suffix(".json")
    from gemini_client import GeminiClient
    client = GeminiClient()
    specs_path.write_text(client.specs_to_json(presentation_spec), encoding="utf-8")

    # Results
    total_time = round(time.time() - start_time, 2)
    result["success"] = True
    result["files"] = {
        "pptx": output_pptx,
        "specs_json": str(specs_path),
    }
    result["metadata"] = {
        "title": title,
        "total_slides": total_slides,
        "slide_types": [s.type for s in slide_specs],
    }
    result["timing"]["total"] = total_time

    logger.info("=" * 50)
    logger.info("OCR Conversion Complete")
    logger.info("  Title: %s", title)
    logger.info("  Slides: %d", total_slides)
    logger.info("  Time: %.1fs (extract=%.1fs, ocr=%.1fs, build=%.1fs)",
                total_time, result["timing"]["extraction"],
                result["timing"]["ocr"], result["timing"]["building"])
    logger.info("  Output: %s", output_pptx)
    logger.info("=" * 50)

    return result


def main():
    """CLI entry point for OCR conversion."""
    parser = argparse.ArgumentParser(
        description="Convert NotebookLM image PPTX to editable Recodme PPTX",
    )
    parser.add_argument("input_pptx", help="Path to NotebookLM-generated PPTX file")
    parser.add_argument("--output", "-o", help="Output path for editable PPTX")
    parser.add_argument("--brand", help="Brand config JSON path")
    parser.add_argument("--model", default="gemini-2.5-flash",
                        help="Gemini model for Vision OCR (default: gemini-2.5-flash)")

    args = parser.parse_args()

    if not Path(args.input_pptx).exists():
        print(f"Error: File not found: {args.input_pptx}")
        sys.exit(1)

    result = convert_notebooklm_to_editable(
        input_pptx=args.input_pptx,
        output_pptx=args.output,
        brand_path=args.brand,
        model=args.model,
    )

    if not result["success"]:
        print(f"\nError: {result.get('error', 'Unknown error')}")
        sys.exit(1)

    print(f"\nOutput: {result['files']['pptx']}")


if __name__ == "__main__":
    main()

"""
Image Generator — Creates full-slide images using Gemini Nano Banana Pro.

Each slide is generated as a COMPLETE image (text + design + visuals baked in),
matching the Recodme approach where every slide is a single rasterized image.

Falls back to illustration-only mode (old composite approach) or None on failure.
"""

import base64
import json
import logging
import os
import time
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# Full-slide generation — Nano Banana 2 (Gemini 3.1 Flash Image Preview)
FULL_SLIDE_MODEL = "gemini-3.1-flash-image-preview"
# Illustration-only fallback (composite mode)
COMPOSITE_MODEL = "gemini-2.5-flash-image"

GENERATE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

# Layout instructions per slide type — Recodme aesthetic
LAYOUT_TEMPLATES = {
    "title": (
        "Warm cream background (#F5F0E8). "
        "Institution/source name at top in small dark text. "
        "Large bold dark navy title centered in upper half (40pt+). "
        "Subtitle below in regular weight, slightly smaller. "
        "ONE contained editorial line-art illustration centered in middle (not full-bleed) — "
        "a simple conceptual sketch that represents the topic's essence, drawn in navy/gold line-art. "
        "Small source attribution box in bottom-right corner with muted text. "
        "Small 'Recodme' watermark text in bottom-right. "
        "Generous whitespace. Clean and structured."
    ),
    "content": (
        "Warm cream background (#F5F0E8). "
        "Bold dark navy title at top spanning full width (32-36pt). "
        "Below the title: a 2x2 GRID layout with thin hairline dividers. "
        "Each grid cell contains: a small flat line-art icon (navy or teal, hand-drawn style), "
        "a bold subtitle, and 2-3 lines of body text. "
        "If there are fewer than 4 items, use a 2-column or single-column layout instead. "
        "Icons are simple and conceptual — like editorial sketches, NOT 3D or photorealistic. "
        "All text is dark navy on cream background. "
        "Small 'Recodme' watermark in bottom-right."
    ),
    "section": (
        "Warm cream background (#F5F0E8). "
        "Very large bold dark navy title centered vertically and horizontally (44pt+). "
        "Subtitle or context line below in smaller text. "
        "ONE small centered line-art illustration below the text — simple, contained, editorial. "
        "Very generous whitespace (50%+ of slide is empty). "
        "Clean and minimal — this is a transition/divider slide. "
        "Small 'Recodme' watermark in bottom-right."
    ),
    "data": (
        "Light warm gray background (#F0EDEA) with very faint grid lines. "
        "Bold dark navy title at top with subtitle/context below (32-36pt). "
        "Main content area: clean FLAT bar chart, horizontal bars, or simple data visualization. "
        "Use navy (#313131) and gold (#C5960C) for chart colors, with key numbers in bold accent. "
        "Data labels are large and clear. Axes are simple thin lines. "
        "Bold conclusion/insight text at the bottom of the slide. "
        "NO 3D charts, no gradients in bars — flat, clean, minimal. "
        "Small 'Recodme' watermark in bottom-right."
    ),
    "quote": (
        "Warm cream background (#F5F0E8). "
        "Large bold title at top in dark navy. "
        "A simple line-art clipboard or document icon on the left side. "
        "Checklist-style layout with teal checkmarks and bold labels. "
        "Each item has: a checkmark icon, bold title, and 1-2 lines of explanation. "
        "Clean vertical stacking with generous spacing between items. "
        "All text dark navy on cream. "
        "Small 'Recodme' watermark in bottom-right."
    ),
    "comparison": (
        "Warm cream background (#F5F0E8). "
        "Bold dark navy title spanning full width at top (32-36pt). "
        "Subtitle/context line below the title. "
        "TWO-COLUMN layout with a thin vertical hairline divider in the center. "
        "Left column and right column may have slightly different background tints (one cream, one very light gray). "
        "Each column has: a small flat line-art icon at top, a bold label, and body text below. "
        "Icons are simple editorial sketches (clock, factory, scale, etc.) in navy or brown line-art. "
        "Bottom of slide: bold italic insight or conclusion text. "
        "Small 'Recodme' watermark in bottom-right."
    ),
    "conclusion": (
        "Warm cream background (#F5F0E8). "
        "Large bold dark navy title at top (36-40pt). "
        "THREE-COLUMN layout below with THREE key pillars/takeaways. "
        "Each column has: a small flat line-art icon inside a colored circle (red or navy), "
        "a bold label, and 2-3 lines of supporting text. "
        "OR: a numbered list with bold key points and explanatory text. "
        "Final bold statement or quote at the bottom. "
        "All text dark navy on cream. Clean and structured. "
        "Small 'Recodme' watermark in bottom-right."
    ),
}


def load_full_slide_template() -> str:
    """Load the full-slide prompt template."""
    path = PROMPTS_DIR / "full_slide_prompt_template.txt"
    if not path.exists():
        return (
            "Design a COMPLETE presentation slide as a single image.\n"
            "SLIDE TYPE: {slide_type}\n"
            "LAYOUT INSTRUCTIONS: {layout_instructions}\n"
            "TEXT CONTENT:\n{text_content}\n"
            "VISUAL DIRECTION: {visual_concept}\n"
            "Canvas: 16:9 widescreen, 2752x1536 pixels.\n"
            "Professional quality. ALL text must be crisp and correctly spelled.\n"
            "No borders, no UI elements."
        )
    return path.read_text(encoding="utf-8")


def load_image_prompt_template() -> str:
    """Load the illustration-only prompt template (composite fallback)."""
    path = PROMPTS_DIR / "image_prompt_template.txt"
    if not path.exists():
        return (
            "Create a professional presentation slide illustration.\n"
            "Concept: {visual_concept}\n"
            "Style: Modern corporate, clean, minimalist. Use deep navy blue, warm gold, and white color palette.\n"
            "Aspect ratio: 16:9 widescreen.\n"
            "IMPORTANT: Do NOT include any text, words, letters, or numbers in the image.\n"
            "The image should be a visual metaphor or illustration, not a diagram with labels."
        )
    return path.read_text(encoding="utf-8")


def _format_text_content(slide_spec) -> str:
    """Format all text content from a slide spec for the prompt."""
    parts = []
    if slide_spec.title:
        parts.append(f'- Title: "{slide_spec.title}"')
    if slide_spec.subtitle:
        parts.append(f'- Subtitle: "{slide_spec.subtitle}"')
    if slide_spec.body:
        parts.append(f'- Body: "{slide_spec.body}"')
    if slide_spec.bullet_points:
        formatted = ", ".join(f'"{bp}"' for bp in slide_spec.bullet_points)
        parts.append(f"- Key points: [{formatted}]")
    if slide_spec.source_reference:
        parts.append(f'- Source: "{slide_spec.source_reference}"')
    return "\n".join(parts) if parts else '- Title: "Untitled Slide"'


def build_full_slide_prompt(slide_spec, brand_config=None) -> str:
    """
    Build a comprehensive prompt for full-slide image generation.

    The prompt instructs Gemini to render the ENTIRE slide as one image,
    including all text, typography, layout, and visual elements.
    """
    template = load_full_slide_template()
    slide_type = slide_spec.type or "content"
    layout_instructions = LAYOUT_TEMPLATES.get(slide_type, LAYOUT_TEMPLATES["content"])
    text_content = _format_text_content(slide_spec)
    visual_concept = slide_spec.visual_concept or "Professional corporate atmosphere"

    return template.format(
        slide_type=slide_type,
        layout_instructions=layout_instructions,
        text_content=text_content,
        visual_concept=visual_concept,
    )


def build_image_prompt(visual_concept: str, slide_title: str = "", slide_type: str = "content") -> str:
    """Build illustration-only prompt (composite/fallback mode)."""
    template = load_image_prompt_template()
    return template.format(
        visual_concept=visual_concept,
        slide_title=slide_title,
        slide_type=slide_type,
    )



def _call_gemini_image(prompt: str, api_key: str, model: str, timeout: int = 90) -> bytes | None:
    """
    Call Gemini image generation API and return image bytes.

    Returns PNG/JPEG bytes on success, None on failure.
    """
    url = GENERATE_URL.format(model=model, key=api_key)

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE", "TEXT"],
        },
    }

    # Pro-class models support explicit image config
    if "pro" in model.lower() or model.startswith("gemini-3"):
        payload["generationConfig"]["imageConfig"] = {
            "aspectRatio": "16:9",
            "imageSize": "2K",
        }

    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        if "candidates" not in data or not data["candidates"]:
            logger.warning("Gemini returned no candidates")
            return None

        parts = data["candidates"][0]["content"]["parts"]
        for part in parts:
            if "inlineData" in part:
                image_data = base64.b64decode(part["inlineData"]["data"])
                return image_data

        logger.warning("No image data in Gemini response")
        return None

    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else "?"
        logger.warning("Gemini HTTP error (%s) with model %s", status, model)
        return None
    except requests.exceptions.Timeout:
        logger.warning("Gemini timeout with model %s", model)
        return None
    except Exception as e:
        logger.warning("Gemini call failed (%s): %s", type(e).__name__, e)
        return None


def generate_full_slide_image(
    slide_spec,
    brand_config=None,
    api_key: str | None = None,
    model: str = FULL_SLIDE_MODEL,
) -> bytes | None:
    """
    Generate a COMPLETE slide as a single image (text + design + visuals).

    This is the primary generation mode matching Recodme's approach.
    Returns JPEG/PNG bytes on success, None on failure.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        logger.warning("No GEMINI_API_KEY — skipping full-slide generation")
        return None

    prompt = build_full_slide_prompt(slide_spec, brand_config)
    logger.info("Generating full slide %d [%s]: %s", slide_spec.number, slide_spec.type, slide_spec.title[:50])
    return _call_gemini_image(prompt, key, model, timeout=90)


def generate_illustration(
    visual_concept: str,
    slide_title: str = "",
    slide_type: str = "content",
    api_key: str | None = None,
    model: str = COMPOSITE_MODEL,
) -> bytes | None:
    """
    Generate an illustration-only image (composite/fallback mode).

    Returns PNG bytes on success, None on failure.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        logger.warning("No GEMINI_API_KEY — skipping illustration generation")
        return None

    prompt = build_image_prompt(visual_concept, slide_title, slide_type)
    return _call_gemini_image(prompt, key, model, timeout=60)


def generate_slide_images(
    slides: list,
    output_dir: str | None = None,
    api_key: str | None = None,
    model: str = FULL_SLIDE_MODEL,
    brand_config=None,
    full_slide_mode: bool = True,
    editable_mode: bool = False,
) -> dict[int, str | None]:
    """
    Generate images for all slides in a presentation.

    Args:
        slides: List of SlideSpec objects
        output_dir: Directory to save images
        api_key: Gemini API key
        model: Gemini model name
        brand_config: BrandConfig for prompt construction
        full_slide_mode: True = full-slide images (default), False = illustration-only
        editable_mode: True = text-free backgrounds for editable slides

    Returns:
        Dict mapping slide number -> image file path (or None if generation failed)
    """
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        logger.warning("No API key — all slides will use gradient-only backgrounds")
        return {s.number: None for s in slides}

    images_dir = Path(output_dir or Path(__file__).parent.parent / "output" / "images")
    images_dir.mkdir(parents=True, exist_ok=True)

    image_paths: dict[int, str | None] = {}
    total = len(slides)

    if full_slide_mode:
        mode_label = "FULL-SLIDE"
    else:
        mode_label = "ILLUSTRATION"
    rate_delay = 2.0 if full_slide_mode else 0.5

    logger.info("Image generation mode: %s | Model: %s | Slides: %d", mode_label, model, total)

    for i, slide in enumerate(slides):
        concept = slide.visual_concept
        if not concept and not full_slide_mode:
            logger.info("Slide %d: no visual_concept — skipping", slide.number)
            image_paths[slide.number] = None
            continue

        logger.info("Generating image %d/%d for slide %d: %s", i + 1, total, slide.number, slide.title[:50])

        if full_slide_mode:
            image_bytes = generate_full_slide_image(
                slide_spec=slide,
                brand_config=brand_config,
                api_key=key,
                model=model,
            )
        else:
            image_bytes = generate_illustration(
                visual_concept=concept,
                slide_title=slide.title,
                slide_type=slide.type,
                api_key=key,
                model=model,
            )

        if image_bytes:
            ext = "jpg" if full_slide_mode else "png"
            filename = f"slide_{slide.number:02d}.{ext}"
            filepath = images_dir / filename
            filepath.write_bytes(image_bytes)
            image_paths[slide.number] = str(filepath)
            logger.info("Saved: %s (%d KB)", filename, len(image_bytes) // 1024)
        else:
            image_paths[slide.number] = None
            logger.warning("Slide %d: image generation failed — will use fallback", slide.number)

        # Pause between API calls for rate limits
        if i < total - 1:
            time.sleep(rate_delay)

    generated = sum(1 for v in image_paths.values() if v is not None)
    logger.info("Image generation complete: %d/%d slides have images", generated, total)
    return image_paths


def generate_mock_images(slides: list) -> dict[int, str | None]:
    """Generate placeholder image paths for testing (no actual API calls)."""
    return {s.number: None for s in slides}

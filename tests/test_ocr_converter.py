"""
Test Suite — OCR Converter: NotebookLM image PPTX → editable Recodme PPTX.

Run: python -m pytest tests/test_ocr_converter.py -v
"""

import io
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from pptx import Presentation
from pptx.util import Inches
from PIL import Image

from gemini_client import SlideSpec, PresentationSpec
from ocr_converter import (
    extract_slide_images,
    classify_slide_type,
    content_to_slidespec,
    convert_notebooklm_to_editable,
    convert_pdnob_style,
    extract_text_with_positions,
    erase_text_from_image,
    _sample_text_color,
    OCRTextBlock,
    load_ocr_prompt,
    normalize_text,
    _parse_raw_text_to_slide,
    VALID_SLIDE_TYPES,
)


# ─── Helper: Create a mock NotebookLM PPTX with image slides ────

def _create_mock_notebooklm_pptx(num_slides: int = 3) -> str:
    """Create a PPTX file with one full-bleed image per slide (mimics NotebookLM output)."""
    prs = Presentation()
    prs.slide_width = Inches(17.78)  # NotebookLM: 17.8" wide
    prs.slide_height = Inches(10.0)

    for i in range(num_slides):
        slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout

        # Create a simple PNG image in memory
        img = Image.new("RGB", (1280, 720), color=(245, 240, 232))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        # Add image as full-bleed picture shape
        slide.shapes.add_picture(
            buf,
            Inches(0), Inches(0),
            Inches(17.78), Inches(10.0),
        )

    tmp = tempfile.NamedTemporaryFile(suffix=".pptx", delete=False)
    prs.save(tmp.name)
    tmp.close()
    return tmp.name


def _create_mock_empty_pptx() -> str:
    """Create a PPTX file with slides but no images (text-only)."""
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    # Only add a text box, no picture
    txBox = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(5), Inches(2))
    txBox.text_frame.text = "Text-only slide"

    tmp = tempfile.NamedTemporaryFile(suffix=".pptx", delete=False)
    prs.save(tmp.name)
    tmp.close()
    return tmp.name


# ─── OCR Prompt Tests ────────────────────────────────────────────

def test_ocr_prompt_loads():
    """OCR extraction prompt file exists and loads."""
    prompt = load_ocr_prompt()
    assert len(prompt) > 100, "OCR prompt should be substantial"
    assert "{slide_number}" in prompt
    assert "{total_slides}" in prompt
    assert "JSON" in prompt
    print("  [PASS] OCR prompt loads with placeholders")


def test_ocr_prompt_has_slide_types():
    """Prompt instructs Gemini about valid slide types."""
    prompt = load_ocr_prompt()
    for stype in ["title", "section", "content", "comparison", "data", "quote", "conclusion"]:
        assert stype in prompt, f"Prompt missing slide type: {stype}"
    print("  [PASS] OCR prompt includes all 7 slide types")


# ─── Image Extraction Tests ──────────────────────────────────────

def test_extract_slide_images():
    """Extract images from a mock NotebookLM PPTX."""
    pptx_path = _create_mock_notebooklm_pptx(num_slides=3)
    try:
        images = extract_slide_images(pptx_path)
        assert len(images) == 3, f"Expected 3 slide images, got {len(images)}"
        for slide_num, img_bytes in images:
            assert isinstance(slide_num, int)
            assert isinstance(img_bytes, bytes)
            assert len(img_bytes) > 100, "Image bytes should be non-trivial"
        # Slide numbers should be 1, 2, 3
        nums = [n for n, _ in images]
        assert nums == [1, 2, 3], f"Expected slide numbers [1,2,3], got {nums}"
    finally:
        Path(pptx_path).unlink()
    print("  [PASS] Extract slide images from mock PPTX (3 slides)")


def test_extract_slide_images_empty():
    """No images found in text-only PPTX."""
    pptx_path = _create_mock_empty_pptx()
    try:
        images = extract_slide_images(pptx_path)
        assert len(images) == 0, f"Expected 0 images from text-only PPTX, got {len(images)}"
    finally:
        Path(pptx_path).unlink()
    print("  [PASS] No images extracted from text-only PPTX")


def test_extract_slide_images_single():
    """Extract from PPTX with just 1 slide."""
    pptx_path = _create_mock_notebooklm_pptx(num_slides=1)
    try:
        images = extract_slide_images(pptx_path)
        assert len(images) == 1
        assert images[0][0] == 1
    finally:
        Path(pptx_path).unlink()
    print("  [PASS] Single-slide PPTX extraction")


# ─── Slide Type Classification Tests ─────────────────────────────

def test_classify_valid_types():
    """Valid slide types pass through unchanged."""
    for stype in VALID_SLIDE_TYPES:
        assert classify_slide_type(3, 8, stype) == stype
    print("  [PASS] Valid slide types pass through")


def test_classify_first_slide_fallback():
    """First slide falls back to 'title' for invalid types."""
    assert classify_slide_type(1, 8, "unknown") == "title"
    assert classify_slide_type(1, 8, "intro") == "title"
    assert classify_slide_type(1, 8, "") == "title"
    print("  [PASS] First slide → title fallback")


def test_classify_last_slide_fallback():
    """Last slide falls back to 'conclusion' for invalid types."""
    assert classify_slide_type(8, 8, "unknown") == "conclusion"
    assert classify_slide_type(10, 10, "outro") == "conclusion"
    print("  [PASS] Last slide → conclusion fallback")


def test_classify_middle_slide_fallback():
    """Middle slides fall back to 'content' for invalid types."""
    assert classify_slide_type(3, 8, "unknown") == "content"
    assert classify_slide_type(5, 10, "freeform") == "content"
    assert classify_slide_type(2, 5, "") == "content"
    print("  [PASS] Middle slides → content fallback")


# ─── SlideSpec Mapping Tests ─────────────────────────────────────

def test_content_to_slidespec_full():
    """Full content dict maps to SlideSpec with all fields."""
    content = {
        "type": "comparison",
        "title": "Before vs After",
        "subtitle": "Key Changes",
        "body": "Significant improvements observed",
        "bullet_points": ["Speed — 3x faster", "Cost — 50% lower"],
        "left_column": ["Old method", "Manual process"],
        "right_column": ["New method", "Automated pipeline"],
        "left_header": "Before",
        "right_header": "After",
        "checkbox_items": [],
        "speaker_notes": "This slide shows the transformation.",
    }
    spec = content_to_slidespec(content, slide_number=4)
    assert spec.number == 4
    assert spec.type == "comparison"
    assert spec.title == "Before vs After"
    assert spec.subtitle == "Key Changes"
    assert spec.body == "Significant improvements observed"
    assert len(spec.bullet_points) == 2
    assert spec.left_column == ["Old method", "Manual process"]
    assert spec.right_column == ["New method", "Automated pipeline"]
    assert spec.left_header == "Before"
    assert spec.right_header == "After"
    assert spec.speaker_notes == "This slide shows the transformation."
    assert spec.visual_concept == ""  # Not needed for editable mode
    print("  [PASS] Full content dict → SlideSpec mapping")


def test_content_to_slidespec_minimal():
    """Minimal content dict produces valid SlideSpec with defaults."""
    content = {
        "type": "content",
        "title": "Simple Slide",
    }
    spec = content_to_slidespec(content, slide_number=2)
    assert spec.number == 2
    assert spec.type == "content"
    assert spec.title == "Simple Slide"
    assert spec.body == ""
    assert spec.bullet_points == []
    assert spec.left_column == []
    assert spec.right_column == []
    print("  [PASS] Minimal content → SlideSpec with defaults")


def test_content_to_slidespec_empty():
    """Empty content dict produces valid SlideSpec."""
    spec = content_to_slidespec({}, slide_number=1)
    assert spec.number == 1
    assert spec.type == "content"
    assert spec.title == ""
    print("  [PASS] Empty content → valid SlideSpec")


# ─── Full Pipeline Tests (Mocked Gemini) ─────────────────────────

def _mock_gemini_response(slide_number, total_slides):
    """Create a mock Gemini Vision API response for a slide."""
    if slide_number == 1:
        content = {
            "type": "title",
            "title": "Seven Tactics Shape Influence",
            "subtitle": "A Manager's Framework",
            "body": "",
            "bullet_points": [],
            "speaker_notes": "Welcome to the presentation.",
        }
    elif slide_number == total_slides:
        content = {
            "type": "conclusion",
            "title": "Master the Full Repertoire",
            "body": "Adapt your tactics to context.",
            "bullet_points": [
                "Diagnose \u2014 then act",
                "Adapt \u2014 direction matters",
                "Invest \u2014 relationships first",
            ],
            "speaker_notes": "Close by emphasizing adaptability.",
        }
    else:
        content = {
            "type": "content",
            "title": f"Key Insight {slide_number}",
            "body": "Evidence supports this claim.",
            "bullet_points": [
                "Reason \u2014 data and logic",
                "Coalition \u2014 allies multiply",
            ],
            "speaker_notes": f"Slide {slide_number} explains the key insight.",
        }
    return json.dumps(content)


@patch("ocr_converter.requests.post")
def test_convert_pipeline_mock(mock_post):
    """Full conversion pipeline with mocked Gemini Vision API."""
    pptx_path = _create_mock_notebooklm_pptx(num_slides=3)

    # Mock Gemini responses for each slide
    def side_effect(*args, **kwargs):
        # Determine which slide by counting calls
        call_count = mock_post.call_count
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": _mock_gemini_response(call_count, 3)
                    }]
                }
            }]
        }
        return mock_resp

    mock_post.side_effect = side_effect

    try:
        output_pptx = tempfile.mktemp(suffix="_editable.pptx")
        result = convert_notebooklm_to_editable(
            input_pptx=pptx_path,
            output_pptx=output_pptx,
            api_key="test-key-12345",
        )

        assert result["success"], f"Pipeline failed: {result.get('error')}"
        assert result["files"]["pptx"] == output_pptx
        assert result["metadata"]["total_slides"] == 3
        assert result["metadata"]["title"] == "Seven Tactics Shape Influence"
        assert "extraction" in result["timing"]
        assert "ocr" in result["timing"]
        assert "building" in result["timing"]

        # Verify output PPTX is valid and has correct number of slides
        prs = Presentation(output_pptx)
        assert len(prs.slides) == 3, f"Expected 3 slides, got {len(prs.slides)}"

        # Verify NO picture shapes (editable mode = solid fills)
        for slide in prs.slides:
            has_picture = any(s.shape_type == 13 for s in slide.shapes)
            assert not has_picture, "Editable output should not have picture shapes"

        # Verify specs JSON was saved
        assert Path(result["files"]["specs_json"]).exists()

        # Cleanup
        Path(output_pptx).unlink(missing_ok=True)
        Path(result["files"]["specs_json"]).unlink(missing_ok=True)
    finally:
        Path(pptx_path).unlink()

    print("  [PASS] Full mock conversion pipeline (3 slides)")


@patch("ocr_converter.requests.post")
def test_convert_pipeline_ocr_failure_fallback(mock_post):
    """Pipeline creates fallback slides when OCR fails for individual slides."""
    pptx_path = _create_mock_notebooklm_pptx(num_slides=2)

    call_count = [0]

    def side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            # First slide succeeds
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "candidates": [{
                    "content": {
                        "parts": [{
                            "text": json.dumps({
                                "type": "title",
                                "title": "Working Slide",
                                "speaker_notes": "Notes here.",
                            })
                        }]
                    }
                }]
            }
            return mock_resp
        else:
            # Second slide fails
            raise RuntimeError("Gemini API error")

    mock_post.side_effect = side_effect

    try:
        output_pptx = tempfile.mktemp(suffix="_editable.pptx")
        result = convert_notebooklm_to_editable(
            input_pptx=pptx_path,
            output_pptx=output_pptx,
            api_key="test-key-12345",
        )

        assert result["success"], "Pipeline should succeed even with partial OCR failure"
        assert result["metadata"]["total_slides"] == 2

        # Verify output still has 2 slides
        prs = Presentation(output_pptx)
        assert len(prs.slides) == 2

        Path(output_pptx).unlink(missing_ok=True)
        Path(result["files"]["specs_json"]).unlink(missing_ok=True)
    finally:
        Path(pptx_path).unlink()

    print("  [PASS] Pipeline handles partial OCR failure with fallback slides")


def test_convert_no_api_key():
    """Pipeline returns error when no API key is provided."""
    old_key = os.environ.pop("GEMINI_API_KEY", None)
    try:
        result = convert_notebooklm_to_editable(
            input_pptx="fake.pptx",
            api_key=None,
        )
        assert not result["success"]
        assert "API key" in result["error"]
    finally:
        if old_key:
            os.environ["GEMINI_API_KEY"] = old_key
    print("  [PASS] Pipeline requires API key")


def test_convert_empty_pptx():
    """Pipeline returns error for PPTX with no images."""
    pptx_path = _create_mock_empty_pptx()
    try:
        result = convert_notebooklm_to_editable(
            input_pptx=pptx_path,
            api_key="test-key-12345",
        )
        assert not result["success"]
        assert "No images" in result["error"]
    finally:
        Path(pptx_path).unlink()
    print("  [PASS] Pipeline rejects empty PPTX (no images)")


# ─── UTF-8 Normalization Tests ───────────────────────────────────

def test_normalize_text_nfc():
    """NFC normalization composes decomposed accents."""
    # "é" as decomposed (e + combining acute accent)
    decomposed = "e\u0301"
    result = normalize_text(decomposed)
    assert result == "é", f"Expected 'é', got {repr(result)}"
    # "ñ" decomposed
    assert normalize_text("n\u0303") == "ñ"
    print("  [PASS] NFC normalization composes decomposed accents")


def test_normalize_text_zero_width():
    """Removes zero-width characters and BOM."""
    text = "Hello\u200bWorld\ufeff"
    result = normalize_text(text)
    assert result == "HelloWorld", f"Expected 'HelloWorld', got {repr(result)}"
    print("  [PASS] Removes zero-width characters and BOM")


def test_normalize_text_nbsp():
    """Replaces non-breaking spaces with regular spaces."""
    text = "Hello\u00a0World"
    result = normalize_text(text)
    assert result == "Hello World"
    print("  [PASS] Replaces non-breaking spaces")


def test_normalize_text_empty():
    """Empty string returns empty."""
    assert normalize_text("") == ""
    assert normalize_text(None) is None
    print("  [PASS] Empty/None handling")


def test_content_to_slidespec_normalizes_text():
    """SlideSpec creation normalizes all text fields."""
    content = {
        "type": "content",
        "title": "Tácticas de Influencia",  # normal
        "body": "e\u0301xito",  # decomposed é
        "bullet_points": ["Razo\u0301n \u2014 lo\u0301gica", "Coalicio\u0301n \u2014 aliados"],
        "speaker_notes": "Nota\u00a0con\u200bcaracteres",
    }
    spec = content_to_slidespec(content, slide_number=3)
    assert spec.body == "éxito"
    assert spec.bullet_points[0] == "Razón — lógica"
    assert spec.bullet_points[1] == "Coalición — aliados"
    assert spec.speaker_notes == "Nota concaracteres"
    print("  [PASS] SlideSpec normalizes all text fields")


# ─── Docling OCR Engine Tests ───────────────────────────────────

def test_parse_raw_text_to_slide_basic():
    """Parse raw OCR text with title and bullets."""
    raw = "# Key Insight 2\n- Speed — 3x faster\n- Cost — 50% lower\nSome body text here."
    result = _parse_raw_text_to_slide(raw, slide_number=2, total_slides=5)
    assert result["title"] == "Key Insight 2"
    assert len(result["bullet_points"]) == 2
    assert "Speed — 3x faster" in result["bullet_points"]
    assert result["type"] == "content"
    print("  [PASS] Parse raw OCR text with title and bullets")


def test_parse_raw_text_to_slide_title_slide():
    """First slide always becomes title type."""
    raw = "# My Presentation\n**A Great Topic**\nSome intro text."
    result = _parse_raw_text_to_slide(raw, slide_number=1, total_slides=8)
    assert result["type"] == "title"
    assert result["title"] == "My Presentation"
    assert result["subtitle"] == "A Great Topic"
    print("  [PASS] First slide parsed as title type")


def test_parse_raw_text_to_slide_conclusion():
    """Last slide always becomes conclusion type."""
    raw = "# Final Thoughts\n- Point 1\n- Point 2"
    result = _parse_raw_text_to_slide(raw, slide_number=8, total_slides=8)
    assert result["type"] == "conclusion"
    print("  [PASS] Last slide parsed as conclusion type")


def test_parse_raw_text_to_slide_empty():
    """Empty raw text produces valid fallback."""
    result = _parse_raw_text_to_slide("", slide_number=3, total_slides=5)
    assert result["title"] == "Slide 3"
    assert result["type"] == "content"
    print("  [PASS] Empty raw text produces valid fallback")


def test_parse_raw_text_numbered_bullets():
    """Numbered list items are parsed as bullet points."""
    raw = "# Topic\n1. First point\n2. Second point\n3. Third point"
    result = _parse_raw_text_to_slide(raw, slide_number=3, total_slides=5)
    assert len(result["bullet_points"]) == 3
    assert "First point" in result["bullet_points"][0]
    print("  [PASS] Numbered bullets parsed correctly")


def test_parse_raw_text_colon_to_em_dash():
    """Bullet items with colons get reformatted to em dash style."""
    raw = "# Topic\n- Speed: very fast\n- Cost: very low"
    result = _parse_raw_text_to_slide(raw, slide_number=2, total_slides=5)
    assert "Speed — very fast" in result["bullet_points"]
    assert "Cost — very low" in result["bullet_points"]
    print("  [PASS] Colon bullet format → em dash")


def test_convert_invalid_ocr_engine():
    """Pipeline returns error for unknown OCR engine."""
    result = convert_notebooklm_to_editable(
        input_pptx="fake.pptx",
        api_key="test-key",
        ocr_engine="unknown_engine",
    )
    assert not result["success"]
    assert "Unknown OCR engine" in result["error"]
    print("  [PASS] Invalid OCR engine returns error")


def test_convert_docling_no_api_key():
    """Docling engine doesn't need API key — should not error on missing key."""
    pptx_path = _create_mock_empty_pptx()
    try:
        old_key = os.environ.pop("GEMINI_API_KEY", None)
        result = convert_notebooklm_to_editable(
            input_pptx=pptx_path,
            api_key=None,
            ocr_engine="docling",
        )
        # Should fail because no images, not because of API key
        assert not result["success"]
        assert "No images" in result["error"]
    finally:
        if old_key:
            os.environ["GEMINI_API_KEY"] = old_key
        Path(pptx_path).unlink()
    print("  [PASS] Docling engine doesn't need API key")


@patch("ocr_converter.extract_slide_content_docling")
def test_convert_pipeline_docling_mock(mock_docling):
    """Full conversion pipeline with mocked Docling OCR engine."""
    pptx_path = _create_mock_notebooklm_pptx(num_slides=3)

    call_count = [0]

    def side_effect(image_bytes, slide_number, total_slides):
        call_count[0] += 1
        if slide_number == 1:
            return {
                "type": "title",
                "title": "Docling Extracted Title",
                "subtitle": "Via OCR",
                "body": "",
                "bullet_points": [],
                "speaker_notes": "",
            }
        elif slide_number == 3:
            return {
                "type": "conclusion",
                "title": "Final Summary",
                "body": "End of presentation.",
                "bullet_points": ["Key — takeaway"],
                "speaker_notes": "",
            }
        else:
            return {
                "type": "content",
                "title": f"Slide {slide_number} Content",
                "body": "Some body text.",
                "bullet_points": ["Point — one", "Point — two"],
                "speaker_notes": "",
            }

    mock_docling.side_effect = side_effect

    try:
        output_pptx = tempfile.mktemp(suffix="_editable.pptx")
        result = convert_notebooklm_to_editable(
            input_pptx=pptx_path,
            output_pptx=output_pptx,
            ocr_engine="docling",
        )

        assert result["success"], f"Docling pipeline failed: {result.get('error')}"
        assert result["metadata"]["total_slides"] == 3
        assert result["metadata"]["ocr_engine"] == "docling"
        assert result["metadata"]["title"] == "Docling Extracted Title"

        # Verify output PPTX is valid
        prs = Presentation(output_pptx)
        assert len(prs.slides) == 3

        # Verify NO picture shapes (editable mode)
        for slide in prs.slides:
            has_picture = any(s.shape_type == 13 for s in slide.shapes)
            assert not has_picture, "Editable output should not have picture shapes"

        Path(output_pptx).unlink(missing_ok=True)
        Path(result["files"]["specs_json"]).unlink(missing_ok=True)
    finally:
        Path(pptx_path).unlink()

    print("  [PASS] Full Docling mock conversion pipeline (3 slides)")


# ─── PDNob OCR Tests ──────────────────────────────────────────────


def _create_image_with_text() -> bytes:
    """Create a test image with black text on white background."""
    img = Image.new("RGB", (800, 600), color=(255, 255, 255))
    # Draw a dark rectangle to simulate text area
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    # Simulate text blocks as dark rectangles
    draw.rectangle([50, 50, 300, 80], fill=(20, 20, 20))   # "Title" area
    draw.rectangle([50, 120, 400, 145], fill=(30, 30, 30))  # "Body" area
    draw.rectangle([50, 180, 350, 205], fill=(25, 25, 25))  # "Bullet" area
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@patch("ocr_converter._get_rapid_ocr")
def test_extract_text_with_positions(mock_ocr_factory):
    """Extract text blocks with positions from image via mocked RapidOCR."""
    mock_engine = MagicMock()
    mock_ocr_factory.return_value = mock_engine

    # RapidOCR v3.x returns (results_list, elapsed_times)
    # Each item: [box, text, score]
    mock_engine.return_value = (
        [
            [[[50, 50], [300, 50], [300, 80], [50, 80]], "Title Text", "0.95"],
            [[[50, 120], [400, 120], [400, 145], [50, 145]], "Body content here", "0.88"],
        ],
        [0.1, 0.2, 0.3],
    )

    image_bytes = _create_image_with_text()
    blocks = extract_text_with_positions(image_bytes)

    assert len(blocks) == 2, f"Expected 2 text blocks, got {len(blocks)}"
    assert blocks[0].text == "Title Text"
    assert blocks[1].text == "Body content here"
    # Verify percentage coordinates are reasonable (0-100 range)
    for b in blocks:
        assert 0 <= b.x_pct <= 100
        assert 0 <= b.y_pct <= 100
        assert b.width_pct > 0
        assert b.height_pct > 0
        assert b.font_size_pt >= 8.0
        assert len(b.color) == 3
    # First block should be above second (sorted top-to-bottom)
    assert blocks[0].y_pct < blocks[1].y_pct
    print("  [PASS] Extract text with positions (mocked RapidOCR)")


@patch("ocr_converter._get_rapid_ocr")
def test_extract_text_with_positions_empty(mock_ocr_factory):
    """No text detected returns empty list."""
    mock_engine = MagicMock()
    mock_ocr_factory.return_value = mock_engine
    mock_engine.return_value = (None, [0.0])

    image_bytes = _create_image_with_text()
    blocks = extract_text_with_positions(image_bytes)
    assert blocks == []
    print("  [PASS] Empty OCR result returns empty list")


@patch("ocr_converter._get_rapid_ocr")
def test_extract_text_filters_low_confidence(mock_ocr_factory):
    """Text blocks below 0.5 confidence are filtered out."""
    mock_engine = MagicMock()
    mock_ocr_factory.return_value = mock_engine

    mock_engine.return_value = (
        [
            [[[10, 10], [200, 10], [200, 40], [10, 40]], "High confidence", "0.92"],
            [[[10, 60], [200, 60], [200, 90], [10, 90]], "Low confidence", "0.30"],
        ],
        [0.1, 0.2, 0.3],
    )

    image_bytes = _create_image_with_text()
    blocks = extract_text_with_positions(image_bytes)
    assert len(blocks) == 1
    assert blocks[0].text == "High confidence"
    print("  [PASS] Low confidence text blocks filtered out")


def test_erase_text_from_image():
    """Erased image has same dimensions and text regions are modified."""
    image_bytes = _create_image_with_text()
    original_img = Image.open(io.BytesIO(image_bytes))
    orig_w, orig_h = original_img.size

    text_blocks = [
        OCRTextBlock(
            text="Title", x_pct=6.25, y_pct=8.33,
            width_pct=31.25, height_pct=5.0,
            font_size_pt=24.0, color=(20, 20, 20),
        ),
    ]

    erased_bytes = erase_text_from_image(image_bytes, text_blocks)
    assert len(erased_bytes) > 0
    erased_img = Image.open(io.BytesIO(erased_bytes))
    assert erased_img.size == (orig_w, orig_h), "Erased image dimensions should match original"
    print("  [PASS] Erase text from image (dimensions preserved)")


def test_erase_text_no_blocks():
    """Erasing with no text blocks returns image unchanged in dimensions."""
    image_bytes = _create_image_with_text()
    erased_bytes = erase_text_from_image(image_bytes, [])
    erased_img = Image.open(io.BytesIO(erased_bytes))
    original_img = Image.open(io.BytesIO(image_bytes))
    assert erased_img.size == original_img.size
    print("  [PASS] Erase text with no blocks preserves image")


def test_sample_text_color():
    """Color sampling detects dark text on light background."""
    import numpy as np
    # Create a white image with a dark text region
    img = np.full((100, 200, 3), 240, dtype=np.uint8)  # Light gray bg
    # Draw dark "text" in the middle
    img[30:60, 40:160] = [30, 30, 80]  # Dark blue-ish text

    color = _sample_text_color(img, 40, 30, 160, 60)
    # Should detect the dark text color, not the background
    assert color[0] < 100, f"Expected dark R, got {color[0]}"
    assert color[2] < 150, f"Expected dark-ish B, got {color[2]}"
    print("  [PASS] Sample text color detects dark text on light bg")


def test_sample_text_color_fallback():
    """Color sampling falls back to white for tiny bbox."""
    import numpy as np
    img = np.full((100, 200, 3), 128, dtype=np.uint8)
    # Very small bbox (< 4px)
    color = _sample_text_color(img, 10, 10, 12, 12)
    assert color == (255, 255, 255), "Tiny bbox should fallback to white"
    print("  [PASS] Sample text color fallback for tiny bbox")


def test_build_pdnob_slide():
    """PDNob slide has background image + text boxes."""
    from slide_builder import SlideBuilder

    # Create a temp image
    img = Image.new("RGB", (1280, 720), color=(200, 200, 220))
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img.save(tmp.name)
    tmp.close()

    try:
        builder = SlideBuilder()
        text_blocks = [
            OCRTextBlock(
                text="Test Title", x_pct=5.0, y_pct=10.0,
                width_pct=80.0, height_pct=8.0,
                font_size_pt=32.0, color=(255, 255, 255),
            ),
            OCRTextBlock(
                text="Body text here", x_pct=5.0, y_pct=25.0,
                width_pct=60.0, height_pct=5.0,
                font_size_pt=18.0, color=(200, 200, 200),
            ),
        ]
        builder.build_pdnob_slide(tmp.name, text_blocks)

        # Verify slide was created
        assert len(builder.prs.slides) == 1
        slide = builder.prs.slides[0]

        # Should have picture shape (background) + 2 text boxes
        shapes = list(slide.shapes)
        has_picture = any(s.shape_type == 13 for s in shapes)
        assert has_picture, "PDNob slide should have a background picture"

        text_shapes = [s for s in shapes if hasattr(s, "text_frame")]
        assert len(text_shapes) >= 2, f"Expected >= 2 text shapes, got {len(text_shapes)}"
    finally:
        Path(tmp.name).unlink(missing_ok=True)

    print("  [PASS] PDNob slide has background image + text boxes")


def test_build_pdnob_slide_no_text():
    """PDNob slide with no text blocks just has the background image."""
    from slide_builder import SlideBuilder

    img = Image.new("RGB", (1280, 720), color=(100, 100, 100))
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img.save(tmp.name)
    tmp.close()

    try:
        builder = SlideBuilder()
        builder.build_pdnob_slide(tmp.name, [])

        assert len(builder.prs.slides) == 1
        slide = builder.prs.slides[0]
        has_picture = any(s.shape_type == 13 for s in slide.shapes)
        assert has_picture, "Fallback PDNob slide should still have background image"
    finally:
        Path(tmp.name).unlink(missing_ok=True)

    print("  [PASS] PDNob slide with no text has background image only")


@patch("ocr_converter.extract_text_with_positions")
@patch("ocr_converter.erase_text_from_image")
def test_convert_pdnob_style(mock_erase, mock_extract):
    """Full PDNob conversion pipeline with mocked OCR + inpainting."""
    pptx_path = _create_mock_notebooklm_pptx(num_slides=2)

    # Mock OCR returning text blocks
    mock_extract.return_value = [
        OCRTextBlock(
            text="Slide Title", x_pct=5.0, y_pct=5.0,
            width_pct=80.0, height_pct=8.0,
            font_size_pt=28.0, color=(255, 255, 255),
        ),
    ]

    # Mock inpainting returning a valid PNG
    clean_img = Image.new("RGB", (1280, 720), color=(50, 50, 80))
    buf = io.BytesIO()
    clean_img.save(buf, format="PNG")
    mock_erase.return_value = buf.getvalue()

    try:
        output_pptx = tempfile.mktemp(suffix="_pdnob.pptx")
        result = convert_pdnob_style(
            input_pptx=pptx_path,
            output_pptx=output_pptx,
        )

        assert result["success"], f"PDNob pipeline failed: {result.get('error')}"
        assert result["metadata"]["total_slides"] == 2
        assert result["metadata"]["mode"] == "pdnob"
        assert "ocr_inpaint" in result["timing"]
        assert Path(output_pptx).exists()

        # Verify output PPTX has correct number of slides
        prs = Presentation(output_pptx)
        assert len(prs.slides) == 2

        # Each slide should have a picture shape (background)
        for slide in prs.slides:
            has_picture = any(s.shape_type == 13 for s in slide.shapes)
            assert has_picture, "PDNob slides should have background pictures"

        Path(output_pptx).unlink(missing_ok=True)
    finally:
        Path(pptx_path).unlink()

    print("  [PASS] Full PDNob mock conversion pipeline (2 slides)")


def test_convert_pdnob_empty_pptx():
    """PDNob pipeline returns error for PPTX with no images."""
    pptx_path = _create_mock_empty_pptx()
    try:
        result = convert_pdnob_style(input_pptx=pptx_path)
        assert not result["success"]
        assert "No images" in result["error"]
    finally:
        Path(pptx_path).unlink()
    print("  [PASS] PDNob pipeline rejects empty PPTX")


# ─── Run All Tests ────────────────────────────────────────────────

def run_all():
    print("\n=== OCR Converter Test Suite ===\n")
    tests = [
        ("OCR Prompt Loads", test_ocr_prompt_loads),
        ("OCR Prompt Slide Types", test_ocr_prompt_has_slide_types),
        ("Extract Slide Images", test_extract_slide_images),
        ("Extract No Images", test_extract_slide_images_empty),
        ("Extract Single Slide", test_extract_slide_images_single),
        ("Classify Valid Types", test_classify_valid_types),
        ("Classify First → Title", test_classify_first_slide_fallback),
        ("Classify Last → Conclusion", test_classify_last_slide_fallback),
        ("Classify Middle → Content", test_classify_middle_slide_fallback),
        ("SlideSpec Full Mapping", test_content_to_slidespec_full),
        ("SlideSpec Minimal", test_content_to_slidespec_minimal),
        ("SlideSpec Empty", test_content_to_slidespec_empty),
        ("Mock Pipeline (3 slides)", test_convert_pipeline_mock),
        ("OCR Failure Fallback", test_convert_pipeline_ocr_failure_fallback),
        ("No API Key Error", test_convert_no_api_key),
        ("Empty PPTX Error", test_convert_empty_pptx),
        # New: UTF-8 normalization
        ("Normalize NFC", test_normalize_text_nfc),
        ("Normalize Zero-Width", test_normalize_text_zero_width),
        ("Normalize NBSP", test_normalize_text_nbsp),
        ("Normalize Empty", test_normalize_text_empty),
        ("SlideSpec Normalizes Text", test_content_to_slidespec_normalizes_text),
        # New: Docling OCR engine
        ("Parse Raw Text Basic", test_parse_raw_text_to_slide_basic),
        ("Parse Raw Text Title", test_parse_raw_text_to_slide_title_slide),
        ("Parse Raw Text Conclusion", test_parse_raw_text_to_slide_conclusion),
        ("Parse Raw Text Empty", test_parse_raw_text_to_slide_empty),
        ("Parse Numbered Bullets", test_parse_raw_text_numbered_bullets),
        ("Parse Colon → Em Dash", test_parse_raw_text_colon_to_em_dash),
        ("Invalid OCR Engine", test_convert_invalid_ocr_engine),
        ("Docling No API Key", test_convert_docling_no_api_key),
        ("Docling Mock Pipeline", test_convert_pipeline_docling_mock),
        # New: PDNob OCR
        ("PDNob Extract Text Positions", test_extract_text_with_positions),
        ("PDNob Extract Empty Result", test_extract_text_with_positions_empty),
        ("PDNob Filter Low Confidence", test_extract_text_filters_low_confidence),
        ("PDNob Erase Text", test_erase_text_from_image),
        ("PDNob Erase No Blocks", test_erase_text_no_blocks),
        ("PDNob Sample Text Color", test_sample_text_color),
        ("PDNob Sample Color Fallback", test_sample_text_color_fallback),
        ("PDNob Build Slide", test_build_pdnob_slide),
        ("PDNob Build Slide No Text", test_build_pdnob_slide_no_text),
        ("PDNob Full Pipeline", test_convert_pdnob_style),
        ("PDNob Empty PPTX", test_convert_pdnob_empty_pptx),
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 40}")
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
    print(f"{'=' * 40}\n")
    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)

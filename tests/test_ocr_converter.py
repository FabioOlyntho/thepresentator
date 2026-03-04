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
    load_ocr_prompt,
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

# CLAUDE.md — The Presentator (presentation-factory)

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**The Presentator** — PDF-to-PPTX presentation factory powered by Gemini AI. Converts PDF documents into professional PowerPoint presentations with multiple generation modes. Includes a FastAPI backend + React frontend for web-based usage, and a CLI for direct pipeline execution.

## Architecture

### Generation Modes

| Mode | Flag | Description |
|------|------|-------------|
| **Editable** (default) | — | Gemini AI → JSON specs → programmatic python-pptx layouts. Modern dark design (cyan/purple accents, Outfit+DM Sans). No image generation. |
| **PDNob** | `--mode pdnob` | OCR → text extraction + inpainting → visual segmentation → background removal (rembg) → editable text boxes + transparent image regions. Preserves original visual layout. |
| **Full-slide** | `--full-slide` | Single AI image per slide (Nano Banana 2). Non-editable. |
| **Composite** | `--composite` | AI illustrations + python-pptx text layout (legacy). |
| **Hybrid** | — | NotebookLM images as backgrounds + editable text overlays. |
| **NotebookLM** | `--notebooklm` | Delegate to NotebookLM for best visual quality. Image-based slides (17.8" x 10.0"). |

### Pipeline Flows

**Editable mode**: `PDF → content_extractor → gemini_client (JSON specs) → slide_builder (programmatic PPTX)`

**PDNob mode**: `PPTX → extract_slide_images → extract_text_with_positions → erase_text_from_image → group_text_blocks → segment_slide_image → remove_background (rembg) → build_pdnob_slide`

**Full-slide mode**: `PDF → gemini_client (specs) → image_generator (Nano Banana 2) → slide_builder (full-bleed images)`

**NotebookLM mode**: `PDF → notebooklm_client (create/revise slide deck) → PPTX (image-based)`

## Project Structure

```
presentation-factory/
├── scripts/              # Core pipeline modules
│   ├── content_extractor.py   # PDF → text extraction (PyPDF2, Docling)
│   ├── gemini_client.py       # Gemini AI → SlideSpec JSON generation
│   ├── image_generator.py     # Full-slide image gen (Nano Banana 2)
│   ├── notebooklm_client.py   # NotebookLM MCP integration
│   ├── ocr_converter.py       # OCR + inpainting + segmentation pipeline
│   ├── presentation_factory.py # CLI orchestrator (all modes)
│   ├── slide_builder.py       # PPTX generation (all layout modes)
│   └── translator.py          # Gemini-powered slide translation
├── backend/              # FastAPI web service
│   ├── main.py           # App setup, CORS, lifespan
│   ├── config.py         # Settings (env vars, paths)
│   ├── models.py         # SQLAlchemy (jobs, brand_kits, slides)
│   ├── schemas.py        # Pydantic request/response models
│   ├── routes/           # API endpoints (jobs, brands, downloads, health, ws)
│   └── services/         # Business logic (job_service, pipeline, storage)
├── frontend/             # React 19 + Vite + TypeScript
│   ├── src/              # Components, pages, API layer
│   └── dist/             # Built frontend (served by backend)
├── tests/                # pytest test suite
│   ├── test_ocr_converter.py  # 65 tests (OCR, positioning, segmentation, bg removal)
│   ├── test_system.py         # Integration tests
│   └── test_translator.py     # Translation tests
├── config/
│   ├── brand.json        # Default brand config (Recodme palette)
│   └── template.pptx     # Base PPTX template
├── prompts/              # AI prompt templates
├── output/               # Generated presentations
└── requirements.txt      # Python dependencies
```

## Key Data Models

| Model | Location | Fields |
|-------|----------|--------|
| `SlideSpec` | `gemini_client.py` | number, type, title, subtitle, body, bullet_points, visual_concept, speaker_notes |
| `OCRTextBlock` | `ocr_converter.py` | text, x_pct, y_pct, width_pct, height_pct, font_size_pt, color |
| `ImageRegion` | `ocr_converter.py` | x_pct, y_pct, width_pct, height_pct |
| `BrandConfig` | `slide_builder.py` | primary, secondary, accent, bg, text, font_heading, font_body |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key for AI services |
| `GOOGLE_APPLICATION_CREDENTIALS` | No | For Google Cloud services (Drive, Stitch) |

## Design System (v5 Editable)

- Background: Dark (#1A1A2E)
- Primary accent: Cyan (#00D4FF)
- Secondary accent: Purple (#7C3AED)
- Fonts: Outfit (headings), DM Sans (body)
- Micro-copy: max 10-word titles, max 30-word body

## Verification Commands

```bash
# Run all tests (140 expected)
./venv/Scripts/python.exe -m pytest tests/ -v

# Run OCR-specific tests (65 expected)
./venv/Scripts/python.exe -m pytest tests/test_ocr_converter.py -v

# PDNob conversion (real file)
./venv/Scripts/python.exe scripts/ocr_converter.py output/notebooklm_revised.pptx --mode pdnob -o output/test.pptx

# Frontend build
cd frontend && npm run build

# Backend dev server
./venv/Scripts/python.exe -m uvicorn backend.main:app --port 8001 --reload
```

## Common Pitfalls

- **RapidOCR v3.x** returns `(results_list, elapsed_times)` where each item is `[box, text, score]` — NOT separate lists
- **NotebookLM slides are 17.8" x 10.0"**, not standard 13.333" x 7.5" — always read source dims with `get_source_slide_dims()`
- **Font size formula**: `bbox_h / img_h * (slide_height_inches * 72)` — calibrate to actual source height
- **Text box positioning**: Use percentage-based coords from OCR, NO artificial padding or oversized minimums
- **Image segmentation** uses pixel-based contour detection (NOT text-gap). Samples background from corners → Euclidean distance threshold → morphological close/open → findContours → merge nearby boxes. Falls back to single full-bleed if < 2 regions detected.
- **Background removal** uses rembg (U2-Net AI model) on each cropped region. Applied only when multi-region segmentation is active (2+ regions). Produces transparent RGBA PNGs.
- **ALWAYS test end-to-end on real data** — mocked tests can pass while actual pipeline is broken

## TDD Protocol

1. Write tests FIRST (RED) in `tests/test_ocr_converter.py`
2. Implement feature to pass tests (GREEN)
3. Refactor while keeping tests green
4. Run full suite: `./venv/Scripts/python.exe -m pytest tests/ -v`
5. Visual verification in PowerPoint for positioning changes

## Post-Commit Checklist

- [ ] All 140+ tests passing
- [ ] Update CLAUDE.md if architecture changed
- [ ] Update MEMORY.md with session notes
- [ ] Visual check in PowerPoint for any slide generation changes

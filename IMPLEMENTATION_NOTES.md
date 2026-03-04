# Implementation Notes

## What Works

### Content Extraction
- **Text-based PDFs**: pdfplumber extracts with full fidelity (tested: 3,332 words from 8-page Spanish PDF, 14,207 words from 20-page Porter PDF)
- **Scanned/image PDFs**: Gemini Vision API OCR works (tested: 12-page scanned PDF, 716 words extracted in 94.7s)
- **Fallback chain**: pdfplumber → PyPDF2 → Gemini Vision OCR (automatic)
- **Language detection**: Heuristic Spanish/English detection works correctly
- **DOCX support**: Implemented but not tested with sample files

### Gemini AI Integration
- **Model**: `gemini-2.5-flash` (free tier, Google AI Studio)
- **Slide spec generation**: NotebookLM-quality output with:
  - Conclusion-style titles ("So what?" answers, not topic labels)
  - 30-60 words per slide body
  - Visual concepts for every slide
  - Source references with page numbers and direct quotes
  - Speaker notes for every slide
  - Logical flow from introduction to conclusion
- **JSON structured output**: Uses `responseMimeType: "application/json"` for reliable parsing
- **Mock mode**: Full mock specs in both ES/EN for testing without API key

### PPTX Generation
- **7 slide types**: title, section, content, comparison, data, quote, conclusion
- **Branded design**: Configurable colors, fonts via brand.json
- **16:9 widescreen**: Professional dimensions (13.333" x 7.5")
- **Speaker notes**: Populated from Gemini output
- **Visual concept hints**: Shown as small text for manual design follow-up

### Pipeline
- **End-to-end time**: ~25s for text PDFs, ~120s for scanned PDFs
- **Quality validation**: Automatic word count and visual concept checks
- **Dual output**: PPTX + JSON specs for every run

## Performance

| Test Case | Extract | Generate | Build | Total |
|-----------|---------|----------|-------|-------|
| Tácticas (8 pages, text) | 0.7s | 23.9s | 0.1s | 24.7s |
| Strategic (12 pages, OCR) | 94.7s | 24.5s | 0.1s | 119.3s |

## Known Issues

1. **Windows console encoding**: Spanish characters display as `T\xe1cticas` in cmd.exe but render correctly in PPTX and JSON files (UTF-8 is correct)
2. **OCR word count**: Gemini Vision OCR returns formatted text that may have lower word counts than native text extraction due to OCR interpretation
3. **Visual concepts**: Currently stored as text hints only — no automatic image generation (planned for future with DALL-E/Imagen)
4. **Bullet formatting**: python-pptx bullet XML customization is limited — bullets render but may not match PowerPoint's native bullet style exactly
5. **Language override**: `--language EN` is overridden by auto-detection when the source document is in a different language (by design)

## Architecture Decisions

1. **python-pptx over Google Slides API**: Generates PPTX locally without requiring Google Cloud credentials. Google Slides API can be added as an optional export path.
2. **gemini-2.5-flash over gemini-pro**: Better availability, faster response, sufficient quality for slide spec generation.
3. **Gemini Vision for OCR**: No local Tesseract/Poppler dependency required. Uses the same API key as content generation.
4. **Mock mode**: Allows development and testing without API keys. Mock specs are realistic and match the expected JSON schema.
5. **Modular pipeline**: Each component (extract → generate → build) is independently testable and replaceable.

## Next Steps

### Immediate
- [ ] Add Google Slides API export (optional, requires service account)
- [ ] Add DALL-E/Imagen integration for visual concept auto-generation
- [ ] Support for PowerPoint template files (.potx) as design base
- [ ] Batch processing for multiple documents

### Medium Term
- [ ] Web UI (Streamlit or FastAPI)
- [ ] Template library (different brands/styles)
- [ ] Multi-language support beyond ES/EN
- [ ] Slide animations and transitions
- [ ] Table and chart generation from data slides

### Long Term
- [ ] Audio narration generation (TTS from speaker notes)
- [ ] Video export with narration
- [ ] Collaborative editing workflow
- [ ] Integration with LMS platforms

## File Inventory

| File | Lines | Purpose |
|------|-------|---------|
| content_extractor.py | 240 | PDF/DOCX extraction + OCR |
| gemini_client.py | 420 | Gemini API + mock + specs |
| slide_builder.py | 430 | PPTX generation engine |
| presentation_factory.py | 280 | CLI orchestrator |
| test_system.py | 250 | 12 unit/integration tests |
| brand.json | 20 | Brand configuration |
| system_prompt.txt | 60 | NotebookLM design rules |
| user_prompt_template.txt | 30 | Document analysis prompt |

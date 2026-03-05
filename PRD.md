# The Presentator — Product Requirements Document (PRD)

## 1. Product Overview

**The Presentator** is an AI-powered presentation generation platform that converts PDF documents, Word files, and other text sources into professional PowerPoint (.pptx) presentations. It uses Google Gemini AI to analyze content, extract key points, generate slide specifications, and build polished decks — all in under 2 minutes.

The product serves the internal team at HumanAIe as a productivity tool for rapidly creating client-facing presentations, training materials, executive summaries, and proposal decks from existing documents.

**Live URL:** https://presentator.humanaie.com
**Repository:** FabioOlyntho/thepresentator

---

## 2. Problem Statement

Creating presentations from existing documents (reports, proposals, technical specs) is a time-consuming manual process that typically takes 1-4 hours. The work involves:
- Reading and summarizing document content
- Designing slide layouts and visual hierarchy
- Writing micro-copy (titles, bullet points, speaker notes)
- Applying consistent branding (colors, fonts, logos)
- Translating presentations for multi-language audiences

**The Presentator** automates this entire workflow end-to-end, reducing presentation creation from hours to minutes while maintaining professional visual quality.

---

## 3. Target Users

| User Type | Use Case |
|-----------|----------|
| Business managers | Convert reports/proposals into executive presentations |
| Consultants | Rapidly produce client-facing decks from analysis documents |
| Recruiters (HumanAIe) | Generate candidate brief presentations, role summaries |
| Sales team | Create proposal decks from technical specifications |
| Training leads | Convert documentation into training slide decks |

---

## 4. Generation Modes

The Presentator offers **5 generation modes** plus a **translation mode**, each optimized for different output quality and editability requirements:

### 4.1 Just Text (Editable Mode) — `editable`

**Pipeline:** `PDF → Gemini AI → JSON slide specs → python-pptx programmatic layout`

- Fully editable PowerPoint with text boxes, bullet points, and formatted content
- Modern dark design system: #1A1A2E background, cyan (#00D4FF) and purple (#7C3AED) accents
- Typography: Outfit (headings) + DM Sans (body)
- No images — pure text-based slides
- Fastest mode (~15-30 seconds)
- Best for: Internal presentations, quick drafts, content that will be heavily edited

### 4.2 NotebookLM — `notebooklm`

**Pipeline:** `PDF → NotebookLM API (create/revise slide deck) → PPTX download`

- Delegates entirely to Google's NotebookLM for maximum visual quality
- Image-based slides (17.8" x 10.0" custom dimensions)
- Each slide is a single high-quality rendered image — not editable
- Best for: Final presentations where visual quality matters most
- Limitation: NotebookLM `create_slide_deck` can fail with server-side error [3]; `revise_slide_deck` is more reliable

### 4.3 NotebookLM Text Editable — `ocr_editable` (Recommended)

**Pipeline:** `PDF → NotebookLM → PPTX → OCR text extraction → inpainting (text removal) → editable text boxes over clean background images`

- Combines NotebookLM visual quality with text editability
- OCR extracts text positions from NotebookLM slides
- AI inpainting removes original text from background images
- Reconstructed slides: clean background image + editable text boxes at exact original positions
- Best for: Presentations that need both visual quality and text editing

### 4.4 NotebookLM Text and Image Editable — `full_slide`

**Pipeline:** `PDF → NotebookLM → PPTX → OCR → inpainting → visual segmentation → separate text boxes + image regions`

- Everything from ocr_editable PLUS visual segmentation of image content
- Pixel-based contour detection separates distinct illustrations from backgrounds
- Each image region becomes an independently movable/resizable element
- Text and images are fully editable in PowerPoint
- Best for: Presentations where layout rearrangement is needed

### 4.5 NLM Text and Image Editable without Background — `pdnob`

**Pipeline:** `PDF → NotebookLM → PPTX → OCR → inpainting → segmentation → background removal (rembg/U2-Net) → transparent PNG regions + editable text`

- Everything from full_slide PLUS AI background removal on image regions
- rembg (U2-Net AI model) produces transparent RGBA PNGs
- Image elements have no background — can be placed on any slide design
- Three sub-levels: `ocr_only`, `remove_bg`, `full`
- Best for: Maximum flexibility, custom slide designs, brand-specific backgrounds

### 4.6 Translate — `translate`

**Pipeline:** `PDF → Gemini AI → slide specs → Gemini translation → translated PPTX`

- Generates presentation in source language, then translates all text to target language
- Supports: Spanish, English, Portuguese, French, German, Italian
- Auto-detect source language
- Preserves slide structure and formatting

---

## 5. Technical Architecture

### 5.1 System Overview

```
                     ┌─────────────────────────┐
                     │    React 19 Frontend     │
                     │  (Vite + TypeScript)     │
                     │  6 pages, 14 components  │
                     └────────────┬────────────┘
                                  │ HTTP/WebSocket
                     ┌────────────▼────────────┐
                     │   FastAPI Backend        │
                     │   (Python 3.12/3.13)     │
                     │   Port 8001, SQLite DB   │
                     └────────────┬────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
    ┌─────────▼──────┐  ┌────────▼────────┐  ┌──────▼────────┐
    │ Gemini AI API  │  │ NotebookLM API  │  │ OCR Pipeline  │
    │ (content gen)  │  │ (visual slides) │  │ (RapidOCR +   │
    │ gemini-2.5-    │  │ create/revise   │  │  OpenCV +     │
    │ flash          │  │ slide deck      │  │  rembg)       │
    └────────────────┘  └─────────────────┘  └───────────────┘
```

### 5.2 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite, TypeScript, CSS Variables |
| Backend | Python 3.13 (dev) / 3.12 (prod), FastAPI 0.129, uvicorn |
| Database | SQLite + aiosqlite + SQLAlchemy 2.0 (async) |
| AI | Google Gemini API (gemini-2.5-flash), NotebookLM MCP CLI |
| PDF Processing | PyPDF2, pdfplumber, python-docx |
| Presentation | python-pptx 1.0 |
| OCR | RapidOCR (ONNX Runtime), OpenCV 4.8 |
| Image Processing | Pillow, rembg (U2-Net), OpenCV |
| Real-time | WebSocket (native FastAPI) |
| Hosting | VPS (Ubuntu 24.04), PM2, Traefik, Let's Encrypt |

### 5.3 Database Schema

| Table | Fields | Purpose |
|-------|--------|---------|
| `jobs` | id, status, mode, title, language, target_language, slide_count, prompt, brand_kit_id, input_filename, input_path, output_pptx_path, output_specs_path, time_total, error_message, pinned, created_at, updated_at | Presentation generation jobs |
| `job_slides` | id, job_id (FK), slide_number, slide_type, title, thumbnail_path | Individual slide metadata |
| `brand_kits` | id, name, logo_path, colors_json, fonts_json, logo_position, is_default, created_at | Custom brand configurations |

---

## 6. API Endpoints

### 6.1 Jobs (Presentation Generation)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/jobs` | Create a new generation job (multipart: file + JSON options) |
| GET | `/api/v1/jobs` | List jobs with filters (status, mode, search, pagination) |
| GET | `/api/v1/jobs/{id}` | Get job details + slide metadata |
| GET | `/api/v1/jobs/{id}/progress` | Get progress events (polling fallback) |
| DELETE | `/api/v1/jobs/{id}` | Delete job and all associated files |
| PATCH | `/api/v1/jobs/{id}/pin` | Toggle pinned status |

### 6.2 Downloads

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/jobs/{id}/download` | Download generated .pptx file |
| GET | `/api/v1/jobs/{id}/specs` | Download slide specs JSON |

### 6.3 Brand Kits

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/brands` | Create a new brand kit |
| GET | `/api/v1/brands` | List all brand kits |
| GET | `/api/v1/brands/{id}` | Get specific brand kit |
| PUT | `/api/v1/brands/{id}` | Update a brand kit |
| DELETE | `/api/v1/brands/{id}` | Delete a brand kit (non-default only) |

### 6.4 Real-time

| Method | Path | Description |
|--------|------|-------------|
| WS | `/api/v1/ws/jobs/{id}` | WebSocket for live progress updates |

### 6.5 Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check (status, service name, version) |

---

## 7. Frontend Pages & Components

### 7.1 Pages (6)

| Page | Route | Description |
|------|-------|-------------|
| **Dashboard** | `/` | Overview with recent jobs, stats bar (total/completed/failed/processing), quick actions |
| **Generate** | `/generate` | Main creation interface: file dropzone, mode selector, language picker, prompt input, brand selector, slide count |
| **Translate** | `/translate` | Translation-specific interface: upload + source/target language selection |
| **Job Detail** | `/jobs/:id` | Full job view: slide carousel with thumbnails, progress tracker, download buttons, specs viewer |
| **History** | `/history` | Searchable/filterable job list with JobCard grid, pin/delete actions |
| **Brand Kits** | `/brands` | Brand kit management: create/edit/delete with color pickers, font selectors, logo upload |

### 7.2 Components (14)

| Component | Purpose |
|-----------|---------|
| `Layout` | App shell with sidebar navigation |
| `Sidebar` | Navigation menu with page links |
| `FileDropzone` | Drag-and-drop file upload (PDF, DOCX, PPTX) |
| `ModeSelector` | Generation mode picker (5 modes with descriptions) |
| `PdnobLevelSelector` | PDNob processing level picker (3 sub-levels) |
| `LanguagePicker` | Source/target language dropdown (7 languages) |
| `PromptInput` | Custom design prompt text area |
| `BrandSelector` | Brand kit dropdown for job creation |
| `JobCard` | Job summary card with status badge, mode label, time, actions |
| `StatsBar` | Dashboard statistics (total, completed, failed, processing counts) |
| `SlideCarousel` | Slide thumbnail viewer with navigation |
| `ProgressTracker` | Real-time progress bar with step labels (WebSocket) |
| `BrandKitCard` | Brand kit display card with color swatches |
| `BrandKitForm` | Brand kit create/edit form with color pickers and font inputs |

---

## 8. Job Options & Configuration

### 8.1 Job Creation Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `mode` | string | `editable` | Generation mode (editable, full_slide, notebooklm, ocr_editable, pdnob, translate) |
| `title` | string | null | Title override (auto-detected from content if null) |
| `language` | string | null | Source language (ES/EN/PT/FR/DE/IT/auto) |
| `target_language` | string | null | Translation target language |
| `slide_count` | int | 8 | Target number of slides (4-20) |
| `prompt` | string | null | Custom design/content prompt |
| `model` | string | gemini-2.5-flash | Gemini model to use |
| `brand_kit_id` | string | null | Custom brand kit ID |
| `pdnob_level` | string | full | PDNob processing level (ocr_only, remove_bg, full) |

### 8.2 Brand Kit Configuration

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| **Colors** | | | |
| primary | hex | #01262D | Main brand color |
| secondary | hex | #313131 | Secondary color |
| accent | hex | #E84422 | Accent/highlight color |
| background | hex | #F5F0E8 | Slide background |
| text_dark | hex | #313131 | Dark text color |
| text_light | hex | #FFFFFF | Light text color |
| highlight | hex | #E84422 | Emphasis color |
| **Fonts** | | | |
| title | string | Poppins | Heading font family |
| body | string | Poppins | Body text font family |
| accent | string | Poppins Light | Accent text font family |
| **Layout** | | | |
| logo_position | string | title_and_footer | Logo placement on slides |

---

## 9. Processing Pipeline Detail

### 9.1 Content Extraction

- **PDF files**: PyPDF2 for text extraction, pdfplumber for table data
- **Word files**: python-docx for structured content extraction
- **PPTX files** (for PDNob mode): Slide images extracted as PNG at source resolution

### 9.2 AI Content Generation (Gemini)

The Gemini AI receives extracted text and produces structured JSON slide specifications:

```json
{
  "slides": [
    {
      "number": 1,
      "type": "title",
      "title": "Max 10 words",
      "subtitle": "Brief context line",
      "body": "Max 30 words of key message",
      "bullet_points": ["Point 1", "Point 2"],
      "visual_concept": "Description for image generation",
      "speaker_notes": "Detailed notes for presenter"
    }
  ]
}
```

**Slide types**: title, section, content, two_column, chart, comparison, quote, closing

**Micro-copy rules**: Max 10-word titles, max 30-word body text, no source citations

### 9.3 OCR Pipeline (PDNob modes)

1. **Extract slide images** — Each slide rendered as PNG at source resolution
2. **OCR text extraction** — RapidOCR with position data (x%, y%, width%, height%, font size, color)
3. **Text inpainting** — OpenCV removes detected text regions, fills with surrounding background
4. **Text block grouping** — Adjacent text blocks merged into logical groups
5. **Visual segmentation** — Pixel-based contour detection separates image regions from background
6. **Background removal** — rembg (U2-Net AI) produces transparent RGBA PNGs per region
7. **Slide reconstruction** — Clean background + positioned text boxes + transparent image regions

### 9.4 Translation Pipeline

1. Generate presentation in source language (full editable pipeline)
2. Extract all text from generated slide specs
3. Send to Gemini with translation prompt (preserve formatting tokens)
4. Rebuild PPTX with translated text in same layouts

---

## 10. Job Lifecycle & Real-time Progress

### 10.1 Status Machine

```
pending → processing → completed
                     → failed
```

### 10.2 Progress Events (WebSocket)

| Step | Progress | Description |
|------|----------|-------------|
| uploading | 5% | File received, starting pipeline |
| extracting | 10% | Extracting content from document |
| generating | 25% | Generating slide specifications via Gemini |
| building | 50-90% | Building PPTX (varies by mode) |
| completed | 100% | Done! X slides in Y.Zs |
| failed | 0% | Error: [message] |

Progress is delivered via WebSocket (`/api/v1/ws/jobs/{id}`) with HTTP polling fallback (`/api/v1/jobs/{id}/progress`).

---

## 11. Supported Input Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| PDF | .pdf | Primary input — text extraction via PyPDF2/pdfplumber |
| Word | .docx | Structured content extraction via python-docx |
| PowerPoint | .pptx | Required for PDNob mode (slide image extraction) |
| Text | .txt | Direct text input |
| Markdown | .md | Markdown content extraction |

**Max upload size:** 50 MB

---

## 12. Supported Output Languages

| Code | Language |
|------|----------|
| ES | Spanish |
| EN | English |
| PT | Portuguese |
| FR | French |
| DE | German |
| IT | Italian |
| auto | Auto-detect source |

---

## 13. Infrastructure & Deployment

### 13.1 Production Environment

| Component | Configuration |
|-----------|--------------|
| Server | VPS 82.25.117.157 (Hostinger, Ubuntu 24.04, 4 vCPU, 8GB RAM) |
| URL | https://presentator.humanaie.com |
| Process manager | PM2 (fork mode, name: `presentator`) |
| Reverse proxy | Traefik v3.4.0 (Docker Swarm, file provider) |
| SSL | Let's Encrypt (auto-renewal via Traefik ACME) |
| Application | uvicorn with 2 workers on port 8001 |
| Database | SQLite at `/var/www/presentator/data/presentator.db` |
| Frontend | Served by FastAPI SPA fallback (no separate web server) |
| Backups | Code + SQLite DB, 7-day retention at `/var/backups/presentator/` |

### 13.2 Deployment Pipeline (7 steps)

1. **Build tarball** — backend/, scripts/, frontend/dist/, config/, prompts/, requirements
2. **SCP upload** — Tarball to VPS `/tmp/`
3. **Pre-deploy backup** — Current code + SQLite database
4. **Extract + install** — Stop PM2 → extract → pip install dependencies
5. **PM2 restart** — Start/restart uvicorn workers
6. **Health check** — Validate `/api/v1/health` returns `{"status":"ok"}`
7. **Auto-rollback** — On health check failure: restore backup + restart PM2

### 13.3 Shared VPS Services

The Presentator shares the VPS with other HumanAIe products:

| Service | Port | URL |
|---------|------|-----|
| SmartOutreachIQ API | 3002 | api-outreach.humanaie.com |
| SmartOutreachIQ Frontend | 8080 | outreach.humanaie.com |
| Enrichment Outbound Engine | 8000 | api-copy.humanaie.com |
| Investment Monitor | 8501 | investment.humanaie.com |
| **The Presentator** | **8001** | **presentator.humanaie.com** |
| n8n (workflows) | 5678 | prod.haie.es |
| Evolution API (WhatsApp) | 8088 | evolution.haie.es |

---

## 14. Design System

### 14.1 Default Design (v5 Editable Mode)

| Property | Value |
|----------|-------|
| Background | Dark #1A1A2E |
| Primary accent | Cyan #00D4FF |
| Secondary accent | Purple #7C3AED |
| Heading font | Outfit |
| Body font | DM Sans |
| Title max length | 10 words |
| Body max length | 30 words |
| Speaker notes | Full detail (not shown on slides) |

### 14.2 Brand Kit System

Users can create custom brand kits that override the default design:
- 7 configurable colors (primary, secondary, accent, background, text dark, text light, highlight)
- 3 configurable fonts (title, body, accent)
- Logo upload with configurable position (title_and_footer, title_only, footer_only)
- Brand kits persist in SQLite and are saved as JSON configs for the pipeline

---

## 15. CLI Interface

In addition to the web interface, The Presentator offers a full CLI for batch processing:

```bash
# Basic editable presentation
python scripts/presentation_factory.py input.pdf --output output/

# NotebookLM mode
python scripts/presentation_factory.py input.pdf --notebooklm

# PDNob mode with background removal
python scripts/ocr_converter.py input.pptx --mode pdnob -o output/result.pptx

# Translation
python scripts/translator.py input.pptx --target EN -o output/translated.pptx

# Custom options
python scripts/presentation_factory.py input.pdf \
  --title "Q4 Report" \
  --language ES \
  --slides 12 \
  --brand config/brand.json \
  --model gemini-2.5-flash
```

---

## 16. Quality & Testing

| Metric | Value |
|--------|-------|
| Test suite | 143 pytest tests |
| Test files | 3 (test_ocr_converter.py: 65, test_system.py: ~50, test_translator.py: ~28) |
| OCR coverage | Positioning, segmentation, background removal, font calibration |
| Smoke tests | 9 production tests (health, frontend, SSL, API, infrastructure) |
| Build verification | Vite frontend build + pytest suite on every change |

---

## 17. Dependencies & External Services

| Service | Purpose | Required |
|---------|---------|----------|
| Google Gemini API | Content analysis, slide spec generation, translation | Yes |
| NotebookLM | Visual slide generation (notebooklm/ocr_editable/full_slide/pdnob modes) | For NLM modes |
| RapidOCR (ONNX) | Offline text position extraction from slide images | For PDNob modes |
| rembg (U2-Net) | AI background removal from image regions | For PDNob full mode |
| OpenCV | Image processing, inpainting, contour detection | For PDNob modes |

---

## 18. Known Limitations

1. **NotebookLM availability** — `create_slide_deck` can fail with server-side error [3]; `revise_slide_deck` is the reliable fallback
2. **NotebookLM slide dimensions** — 17.8" x 10.0" (non-standard), not 13.333" x 7.5"
3. **OCR accuracy** — RapidOCR may miss small or stylized text; font size calibration is approximate
4. **Concurrent jobs** — Limited to 2 simultaneous generation jobs (thread pool constraint)
5. **Max upload size** — 50 MB per file
6. **No authentication** — Currently open access (internal tool assumption)
7. **SQLite** — Single-writer limitation; adequate for internal tool usage

---

## 19. Future Roadmap Considerations

| Feature | Priority | Description |
|---------|----------|-------------|
| Template library | Medium | Pre-built slide templates for common use cases |
| Batch processing | Medium | Upload multiple documents, generate presentations in queue |
| Slide editing UI | Low | In-browser slide editor for quick tweaks before download |
| Authentication | Low | API key or SSO for multi-user access control |
| Analytics | Low | Track generation stats, popular modes, error rates |
| Google Slides export | Low | Direct export to Google Slides in addition to PPTX |

---

## 20. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | Mar 2026 | Initial production deployment with 5 generation modes, brand kits, translation, real-time progress, deployment automation |

---

*This PRD documents The Presentator as deployed at https://presentator.humanaie.com on March 5, 2026.*

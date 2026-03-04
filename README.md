# Presentation Factory

NotebookLM-quality presentation generation from PDF/DOCX documents.

## Pipeline

```
PDF/DOCX → Content Extraction → Gemini AI Analysis → Slide Specs (JSON) → PPTX
```

## Quick Start

```bash
# 1. Set up
cd presentation-factory
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# 2. Add your Gemini API key
cp .env.template .env
# Edit .env with your key from https://aistudio.google.com/apikey

# 3. Generate a presentation
python scripts/presentation_factory.py document.pdf --slides 8
```

## Usage

```bash
python scripts/presentation_factory.py <input_file> [options]

Options:
  --title TEXT       Override presentation title
  --language ES|EN   Force language (auto-detected by default)
  --slides N         Target slide count (default: 8, range: 4-15)
  --objective TEXT    Presentation objective
  --output PATH      Output directory (default: ./output)
  --brand PATH       Brand config JSON (default: config/brand.json)
  --model TEXT        Gemini model (default: gemini-2.5-flash)
```

## Examples

```bash
# Spanish PDF
python scripts/presentation_factory.py "Tácticas_de_influencia.pdf" --slides 8

# English PDF with custom title
python scripts/presentation_factory.py "Strategic_Influence.pdf" --title "Leadership Tactics" --language EN

# Image-based/scanned PDF (automatic OCR via Gemini Vision)
python scripts/presentation_factory.py "scanned_document.pdf" --slides 10
```

## Features

- **Text-based PDFs**: Extracted via pdfplumber/PyPDF2
- **Scanned/image PDFs**: OCR via Gemini Vision API (automatic fallback)
- **DOCX files**: Full support via python-docx
- **Language detection**: Automatic ES/EN detection
- **NotebookLM quality**: Conclusion-style titles, 30-60 words/slide, visual concepts
- **Mock mode**: Works without API key for testing

## Output

Each run generates:
- `{title}_{timestamp}.pptx` — Ready-to-present PowerPoint
- `{title}_{timestamp}_specs.json` — Full slide specifications (editable)

## Project Structure

```
presentation-factory/
├── scripts/
│   ├── content_extractor.py    # PDF/DOCX text extraction + OCR
│   ├── gemini_client.py        # Gemini API for slide spec generation
│   ├── slide_builder.py        # PPTX creation with branded design
│   └── presentation_factory.py # Main orchestrator (CLI)
├── config/
│   └── brand.json              # Brand colors, fonts, dimensions
├── prompts/
│   ├── system_prompt.txt       # NotebookLM-quality design rules
│   └── user_prompt_template.txt # Document analysis prompt
├── tests/
│   └── test_system.py          # 12 tests covering all components
├── output/                     # Generated presentations
├── requirements.txt
├── .env.template
└── README.md
```

## Tests

```bash
python tests/test_system.py
# 12 passed, 0 failed
```

## API Keys

| Service | Required | Get From |
|---------|----------|----------|
| Gemini API | Yes (or use mock mode) | [Google AI Studio](https://aistudio.google.com/apikey) |
| Google Slides API | No (uses python-pptx locally) | N/A |

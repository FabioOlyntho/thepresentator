"""
Gemini Client — Generates NotebookLM-quality slide specifications using Gemini API.

Supports:
- Google AI Studio endpoint (free tier)
- Structured JSON output for slide specs
- Mock mode for testing without API key
- Content chunking for large documents
"""

import json
import os
import re
import sys
import logging
from pathlib import Path
from dataclasses import dataclass, field

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


@dataclass
class SlideSpec:
    """Specification for a single slide."""
    number: int
    type: str  # title, section, content, comparison, data, quote, conclusion
    title: str
    subtitle: str = ""
    body: str = ""
    bullet_points: list[str] = field(default_factory=list)
    visual_concept: str = ""
    speaker_notes: str = ""
    source_reference: str = ""
    left_column: list[str] = field(default_factory=list)
    right_column: list[str] = field(default_factory=list)
    left_header: str = ""
    right_header: str = ""
    checkbox_items: list[str] = field(default_factory=list)


@dataclass
class PresentationSpec:
    """Complete presentation specification."""
    title: str
    subtitle: str
    language: str
    source_document: str
    themes: list[str]
    slides: list[SlideSpec]

    @property
    def total_slides(self) -> int:
        return len(self.slides)


def load_prompt(name: str) -> str:
    """Load a prompt template from the prompts directory."""
    path = PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


def build_user_prompt(
    content: str,
    filename: str,
    language: str,
    objective: str,
    slide_count: int,
) -> str:
    """Build the user prompt from template and parameters."""
    template = load_prompt("user_prompt_template.txt")
    return template.format(
        content=content[:60000],  # Truncate to fit context window
        filename=filename,
        language=language,
        objective=objective,
        slide_count=slide_count,
        penultimate=slide_count - 1,
    )


def parse_slide_specs(raw_json: str) -> PresentationSpec:
    """Parse Gemini's JSON response into structured PresentationSpec."""
    # Strip markdown code fences if present
    cleaned = raw_json.strip()
    if cleaned.startswith("```"):
        # Remove ```json or ``` prefix and ``` suffix
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)

    data = json.loads(cleaned)

    metadata = data.get("metadata", {})
    slides_data = data.get("slides", [])

    slides = []
    for s in slides_data:
        slides.append(SlideSpec(
            number=s.get("number", len(slides) + 1),
            type=s.get("type", "content"),
            title=s.get("title", ""),
            subtitle=s.get("subtitle", ""),
            body=s.get("body", ""),
            bullet_points=s.get("bullet_points", []),
            visual_concept=s.get("visual_concept", ""),
            speaker_notes=s.get("speaker_notes", ""),
            source_reference=s.get("source_reference", ""),
            left_column=s.get("left_column", []),
            right_column=s.get("right_column", []),
            left_header=s.get("left_header", ""),
            right_header=s.get("right_header", ""),
            checkbox_items=s.get("checkbox_items", []),
        ))

    return PresentationSpec(
        title=metadata.get("title", "Untitled"),
        subtitle=metadata.get("subtitle", ""),
        language=metadata.get("language", "ES"),
        source_document=metadata.get("source_document", ""),
        themes=metadata.get("themes", []),
        slides=slides,
    )


def call_gemini(
    system_prompt: str,
    user_prompt: str,
    api_key: str,
    model: str = "gemini-2.5-flash",
    temperature: float = 0.4,
    max_tokens: int = 8192,
) -> str:
    """Call Gemini API and return the text response."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [
            {
                "parts": [{"text": user_prompt}]
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "responseMimeType": "application/json",
        }
    }

    logger.info("Calling Gemini API (model=%s, temp=%.1f)...", model, temperature)
    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    if "candidates" not in data or not data["candidates"]:
        raise RuntimeError(f"Gemini returned no candidates: {json.dumps(data, indent=2)}")

    text = data["candidates"][0]["content"]["parts"][0]["text"]
    logger.info("Gemini response received (%d chars)", len(text))
    return text


def generate_mock_specs(
    content: str,
    filename: str,
    language: str,
    slide_count: int,
) -> PresentationSpec:
    """Generate mock slide specs for testing without API key.

    Uses micro-copy style: short titles, punchy bullets, no source citations.
    """
    logger.info("Using MOCK mode (no GEMINI_API_KEY)")

    is_spanish = language == "ES"
    slides = []

    # Title slide
    slides.append(SlideSpec(
        number=1,
        type="title",
        title="Siete Tácticas Dirigen Toda Influencia" if is_spanish else "Seven Tactics Drive All Influence",
        subtitle="Marco práctico para directivos" if is_spanish else "A practical framework for managers",
        body="",
        visual_concept="Warm cream background with subtle geometric grid in beige, red accent bar at top, flat compass icon in dark teal centered — leave lower half clear for text",
        speaker_notes="Bienvenidos. Hoy veremos cómo toda influencia directiva se reduce a siete tácticas fundamentales." if is_spanish else "Welcome. Today we explore how all managerial influence reduces to seven fundamental tactics.",
    ))

    # Content slides — micro-copy style
    content_slides_es = [
        SlideSpec(
            number=2, type="content",
            title="1.400 tácticas, siete categorías",
            body="Toda influencia directiva cabe en siete grupos. Sin excepción.",
            bullet_points=[
                "Razón — datos y lógica",
                "Coalición — aliados multiplican",
                "Cordialidad — rapport primero",
                "Negociación — intercambio justo",
            ],
            visual_concept="Warm cream background with seven flat circle icons in a row across top third, alternating red and teal fills, thin beige grid lines — leave center and bottom clear for text",
            speaker_notes="La investigación analizó cientos de directivos y encontró más de 1.400 técnicas distintas, que se agrupan en siete categorías fundamentales.",
        ),
        SlideSpec(
            number=3, type="content",
            title="Razón: la táctica universal",
            body="Datos + lógica = mínima resistencia.",
            bullet_points=[
                "Versatilidad — funciona arriba y abajo",
                "Resistencia — baja fricción emocional",
                "Preparación — requiere datos previos",
            ],
            visual_concept="Warm cream background with flat line-art balance scale icon in dark teal at top-right corner, subtle beige diagonal stripe across bottom-left — leave center clear for text",
            speaker_notes="La razón es la primera opción de todo directivo. Presentar datos y argumentos lógicos genera la menor resistencia.",
        ),
        SlideSpec(
            number=4, type="comparison",
            title="Dirección determina táctica",
            body="",
            left_header="Hacia arriba",
            right_header="Hacia abajo",
            left_column=["Razón + coalición", "Sin autoridad formal", "Persuadir con datos"],
            right_column=["Imposición + sanciones", "Autoridad directa", "Dirigir con poder"],
            visual_concept="Split layout — left third solid dark teal, right two-thirds warm cream, thin red vertical divider line in center — flat arrow icons pointing up on left, down on right",
            speaker_notes="La dirección de la influencia determina qué tácticas funcionan mejor. Hacia arriba usamos razón; hacia abajo podemos imponer.",
        ),
        SlideSpec(
            number=5, type="content",
            title="Cordialidad: terreno fértil",
            body="Rapport no es manipulación. Es inversión.",
            bullet_points=[
                "Confianza — activo a largo plazo",
                "Resistencia — reduce fricción futura",
                "Base — plataforma para otras tácticas",
            ],
            visual_concept="Warm cream background with flat handshake icon in dark teal centered in upper third, subtle concentric circles in beige radiating outward — leave lower two-thirds clear for text",
            speaker_notes="La cordialidad construye la base relacional que hace posible la influencia sostenible.",
        ),
        SlideSpec(
            number=6, type="quote",
            title="Reglas del Influenciador Eficaz",
            body="",
            checkbox_items=[
                "Diagnostica antes de actuar",
                "Adapta la táctica a la dirección",
                "Construye relaciones primero",
                "Nunca uses solo una táctica",
            ],
            visual_concept="Warm cream background with flat clipboard icon in red at top-left, subtle checkmark pattern in light beige as background texture — leave right side and center clear for text",
            speaker_notes="Estas cuatro reglas resumen la esencia del directivo influyente.",
        ),
    ]

    content_slides_en = [
        SlideSpec(
            number=2, type="content",
            title="1,400 tactics, seven categories",
            body="All managerial influence fits seven groups. No exceptions.",
            bullet_points=[
                "Reason — data and logic",
                "Coalition — allies multiply",
                "Friendliness — rapport first",
                "Bargaining — fair exchange",
            ],
            visual_concept="Warm cream background with seven flat circle icons in a row across top third, alternating red and teal fills, thin beige grid lines — leave center and bottom clear for text",
            speaker_notes="Research analyzed hundreds of managers and found over 1,400 distinct techniques, grouped into seven fundamental categories.",
        ),
        SlideSpec(
            number=3, type="content",
            title="Reason: the universal tactic",
            body="Data + logic = minimal resistance.",
            bullet_points=[
                "Versatility — works upward and downward",
                "Resistance — low emotional friction",
                "Preparation — requires prior data",
            ],
            visual_concept="Warm cream background with flat line-art balance scale icon in dark teal at top-right corner, subtle beige diagonal stripe across bottom-left — leave center clear for text",
            speaker_notes="Reason is every manager's first choice. Presenting data and logical arguments generates the least resistance.",
        ),
        SlideSpec(
            number=4, type="comparison",
            title="Direction determines tactic",
            body="",
            left_header="Upward",
            right_header="Downward",
            left_column=["Reason + coalition", "No formal authority", "Persuade with data"],
            right_column=["Assertiveness + sanctions", "Direct authority", "Direct with power"],
            visual_concept="Split layout — left third solid dark teal, right two-thirds warm cream, thin red vertical divider line in center — flat arrow icons pointing up on left, down on right",
            speaker_notes="The direction of influence determines which tactics work best. Upward we use reason; downward we can assert.",
        ),
        SlideSpec(
            number=5, type="content",
            title="Friendliness: fertile ground",
            body="Rapport is not manipulation. It is investment.",
            bullet_points=[
                "Trust — long-term asset",
                "Resistance — reduces future friction",
                "Foundation — platform for other tactics",
            ],
            visual_concept="Warm cream background with flat handshake icon in dark teal centered in upper third, subtle concentric circles in beige radiating outward — leave lower two-thirds clear for text",
            speaker_notes="Friendliness builds the relational foundation that makes sustainable influence possible.",
        ),
        SlideSpec(
            number=6, type="quote",
            title="Rules of the Effective Influencer",
            body="",
            checkbox_items=[
                "Diagnose before acting",
                "Adapt tactic to direction",
                "Build relationships first",
                "Never rely on one tactic",
            ],
            visual_concept="Warm cream background with flat clipboard icon in red at top-left, subtle checkmark pattern in light beige as background texture — leave right side and center clear for text",
            speaker_notes="These four rules summarize the essence of the influential manager.",
        ),
    ]

    content_slides = content_slides_es if is_spanish else content_slides_en

    # Adjust to requested slide count
    available = content_slides[:max(1, slide_count - 2)]
    slides.extend(available)

    # Conclusion slide
    slides.append(SlideSpec(
        number=len(slides) + 1,
        type="conclusion",
        title="Domina el repertorio completo" if is_spanish else "Master the full repertoire",
        body="Una táctica no basta. Adapta al contexto." if is_spanish else "One tactic is not enough. Adapt to context.",
        bullet_points=[
            "Diagnostica — luego actúa" if is_spanish else "Diagnose — then act",
            "Adapta — dirección importa" if is_spanish else "Adapt — direction matters",
            "Invierte — relaciones primero" if is_spanish else "Invest — relationships first",
        ],
        visual_concept="Warm cream background with flat compass rose icon in red and dark teal centered, subtle radiating lines in beige — leave bottom third clear for text",
        speaker_notes="Cierra enfatizando que la adaptabilidad es la habilidad clave de liderazgo." if is_spanish else "Close by emphasizing adaptability as the key leadership skill.",
    ))

    return PresentationSpec(
        title=slides[0].title,
        subtitle=slides[0].subtitle,
        language=language,
        source_document=filename,
        themes=["influence", "leadership", "management", "tactics"],
        slides=slides,
    )


class GeminiClient:
    """Client for generating presentation specs via Gemini API."""

    def __init__(self, api_key: str | None = None, model: str = "gemini-2.5-flash"):
        key = api_key or os.environ.get("GEMINI_API_KEY")
        # Reject placeholder values
        if key and ("PASTE" in key or "your" in key.lower() or len(key) < 10):
            key = None
        self.api_key = key
        self.model = model
        self.system_prompt = load_prompt("system_prompt.txt")

    @property
    def is_mock(self) -> bool:
        return not self.api_key

    def generate_slide_specs(
        self,
        content: str,
        filename: str = "document.pdf",
        language: str = "ES",
        objective: str = "Create an insightful executive presentation",
        slide_count: int = 8,
    ) -> PresentationSpec:
        """
        Generate NotebookLM-quality slide specifications from content.

        Args:
            content: Extracted document text
            filename: Source document filename
            language: "ES" or "EN"
            objective: Presentation objective
            slide_count: Target number of slides (6-15)

        Returns:
            PresentationSpec with all slide definitions
        """
        slide_count = max(4, min(15, slide_count))

        if self.is_mock:
            return generate_mock_specs(content, filename, language, slide_count)

        user_prompt = build_user_prompt(
            content=content,
            filename=filename,
            language=language,
            objective=objective,
            slide_count=slide_count,
        )

        raw_json = call_gemini(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            api_key=self.api_key,
            model=self.model,
        )

        spec = parse_slide_specs(raw_json)
        logger.info(
            "Generated %d slides for '%s' (%s)",
            spec.total_slides, spec.title, spec.language,
        )
        return spec

    def specs_to_json(self, spec: PresentationSpec) -> str:
        """Serialize PresentationSpec to JSON string."""
        data = {
            "metadata": {
                "title": spec.title,
                "subtitle": spec.subtitle,
                "language": spec.language,
                "source_document": spec.source_document,
                "total_slides": spec.total_slides,
                "themes": spec.themes,
            },
            "slides": [
                {
                    "number": s.number,
                    "type": s.type,
                    "title": s.title,
                    "subtitle": s.subtitle,
                    "body": s.body,
                    "bullet_points": s.bullet_points,
                    "visual_concept": s.visual_concept,
                    "speaker_notes": s.speaker_notes,
                    "source_reference": s.source_reference,
                    "left_column": s.left_column,
                    "right_column": s.right_column,
                    "left_header": s.left_header,
                    "right_header": s.right_header,
                    "checkbox_items": s.checkbox_items,
                }
                for s in spec.slides
            ]
        }
        return json.dumps(data, indent=2, ensure_ascii=False)


def main():
    """CLI entry point for testing Gemini client."""
    print("\n=== Gemini Client Test ===\n")

    client = GeminiClient()
    print(f"Mode: {'LIVE API' if not client.is_mock else 'MOCK'}")
    print(f"Model: {client.model}\n")

    # Generate test specs
    test_content = """
    Los directivos influyen de mil modos distintos a quienes les rodean.
    En una investigación se encontraron más de 1.400 técnicas distintas.
    Se agruparon en siete categorías: razón, coalición, cordialidad,
    negociación, imposición, recurso a autoridad superior y sanciones.
    """

    spec = client.generate_slide_specs(
        content=test_content,
        filename="test_document.pdf",
        language="ES",
        objective="Explain influence tactics for managers",
        slide_count=6,
    )

    print(f"Title: {spec.title}")
    print(f"Slides: {spec.total_slides}")
    print(f"Language: {spec.language}\n")

    for slide in spec.slides:
        print(f"  Slide {slide.number} [{slide.type}]: {slide.title}")
        if slide.bullet_points:
            for bp in slide.bullet_points:
                print(f"    - {bp}")
    print()

    # Save JSON
    output_path = Path(__file__).parent.parent / "output" / "test_specs.json"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(client.specs_to_json(spec), encoding="utf-8")
    print(f"Specs saved to: {output_path}")
    return spec


if __name__ == "__main__":
    main()

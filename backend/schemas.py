"""
Schemas — Pydantic models for API request/response validation.
"""

from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_serializer


# ─── Job Schemas ──────────────────────────────────────────────

class JobOptions(BaseModel):
    """Options sent with job creation (as JSON alongside file upload)."""
    mode: str = Field(default="editable", description="Generation mode")
    title: str | None = Field(default=None, description="Title override")
    language: str | None = Field(default=None, description="Source language (ES/EN/auto)")
    target_language: str | None = Field(default=None, description="Translation target")
    slide_count: int = Field(default=8, ge=4, le=20, description="Target slide count")
    prompt: str | None = Field(default=None, description="Design prompt")
    model: str = Field(default="gemini-2.5-flash", description="Gemini model")
    brand_kit_id: str | None = Field(default=None, description="Custom brand kit ID")
    pdnob_level: str = Field(default="full", description="PDNob level: ocr_only, remove_bg, full")


class JobSlideResponse(BaseModel):
    slide_number: int
    slide_type: str | None = None
    title: str | None = None
    thumbnail_url: str | None = None

    class Config:
        from_attributes = True


class JobResponse(BaseModel):
    id: str
    status: str
    mode: str
    title: str | None = None
    language: str | None = None
    target_language: str | None = None
    slide_count: int
    prompt: str | None = None
    brand_kit_id: str | None = None
    input_filename: str
    time_total: float | None = None
    error_message: str | None = None
    pinned: bool = False
    created_at: datetime
    updated_at: datetime
    slides: list[JobSlideResponse] = []

    class Config:
        from_attributes = True

    @field_serializer("created_at", "updated_at")
    @classmethod
    def serialize_dt(cls, v: datetime) -> str:
        """Ensure UTC timestamps always include Z suffix for correct JS parsing."""
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat().replace("+00:00", "Z")


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int


# ─── Brand Kit Schemas ────────────────────────────────────────

class BrandColors(BaseModel):
    primary: str = "#01262D"
    secondary: str = "#313131"
    accent: str = "#E84422"
    background: str = "#F5F0E8"
    text_dark: str = "#313131"
    text_light: str = "#FFFFFF"
    highlight: str = "#E84422"


class BrandFonts(BaseModel):
    title: str = "Poppins"
    body: str = "Poppins"
    accent: str = "Poppins Light"


class BrandKitCreate(BaseModel):
    name: str
    colors: BrandColors = Field(default_factory=BrandColors)
    fonts: BrandFonts = Field(default_factory=BrandFonts)
    logo_position: str = "title_and_footer"


class BrandKitUpdate(BaseModel):
    name: str | None = None
    colors: BrandColors | None = None
    fonts: BrandFonts | None = None
    logo_position: str | None = None


class BrandKitResponse(BaseModel):
    id: str
    name: str
    logo_path: str | None = None
    colors: BrandColors
    fonts: BrandFonts
    logo_position: str
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Progress Schema ──────────────────────────────────────────

class ProgressEvent(BaseModel):
    step: str
    progress: int = Field(ge=0, le=100)
    message: str

"""
Models — SQLAlchemy ORM models for The Presentator.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from backend.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class BrandKit(Base):
    __tablename__ = "brand_kits"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    logo_path = Column(String, nullable=True)
    colors_json = Column(Text, nullable=False)
    fonts_json = Column(Text, nullable=False)
    logo_position = Column(String, default="title_and_footer")
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_now)

    jobs = relationship("Job", back_populates="brand_kit")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=_uuid)
    status = Column(String, nullable=False, default="pending")
    mode = Column(String, nullable=False)
    title = Column(String, nullable=True)
    language = Column(String, nullable=True)
    target_language = Column(String, nullable=True)
    slide_count = Column(Integer, default=8)
    prompt = Column(Text, nullable=True)
    brand_kit_id = Column(String, ForeignKey("brand_kits.id"), nullable=True)
    input_filename = Column(String, nullable=False)
    input_path = Column(String, nullable=True)
    output_pptx_path = Column(String, nullable=True)
    output_specs_path = Column(String, nullable=True)
    time_total = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    brand_kit = relationship("BrandKit", back_populates="jobs")
    slides = relationship("JobSlide", back_populates="job", cascade="all, delete-orphan")


class JobSlide(Base):
    __tablename__ = "job_slides"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    slide_number = Column(Integer, nullable=False)
    slide_type = Column(String, nullable=True)
    title = Column(String, nullable=True)
    thumbnail_path = Column(String, nullable=True)

    job = relationship("Job", back_populates="slides")

"""
Brands — CRUD endpoints for brand kit management.
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.models import BrandKit
from backend.schemas import (
    BrandKitCreate,
    BrandKitUpdate,
    BrandKitResponse,
    BrandColors,
    BrandFonts,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _brand_to_response(brand: BrandKit) -> dict:
    """Convert BrandKit ORM model to response dict."""
    return {
        "id": brand.id,
        "name": brand.name,
        "logo_path": brand.logo_path,
        "colors": BrandColors(**json.loads(brand.colors_json)),
        "fonts": BrandFonts(**json.loads(brand.fonts_json)),
        "logo_position": brand.logo_position,
        "is_default": brand.is_default,
        "created_at": brand.created_at,
    }


@router.post("/brands", status_code=201)
async def create_brand(data: BrandKitCreate, db: AsyncSession = Depends(get_db)):
    """Create a new brand kit."""
    brand = BrandKit(
        name=data.name,
        colors_json=data.colors.model_dump_json(),
        fonts_json=data.fonts.model_dump_json(),
        logo_position=data.logo_position,
        is_default=False,
    )
    db.add(brand)
    await db.commit()
    await db.refresh(brand)

    # Save brand config JSON for the pipeline to use
    _save_brand_config(brand)

    return _brand_to_response(brand)


@router.get("/brands")
async def list_brands(db: AsyncSession = Depends(get_db)):
    """List all brand kits."""
    result = await db.execute(select(BrandKit).order_by(BrandKit.name))
    brands = result.scalars().all()
    return [_brand_to_response(b) for b in brands]


@router.get("/brands/{brand_id}")
async def get_brand(brand_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific brand kit."""
    result = await db.execute(select(BrandKit).where(BrandKit.id == brand_id))
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand kit not found")
    return _brand_to_response(brand)


@router.put("/brands/{brand_id}")
async def update_brand(
    brand_id: str,
    data: BrandKitUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a brand kit."""
    result = await db.execute(select(BrandKit).where(BrandKit.id == brand_id))
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand kit not found")

    if data.name is not None:
        brand.name = data.name
    if data.colors is not None:
        brand.colors_json = data.colors.model_dump_json()
    if data.fonts is not None:
        brand.fonts_json = data.fonts.model_dump_json()
    if data.logo_position is not None:
        brand.logo_position = data.logo_position

    await db.commit()
    await db.refresh(brand)

    # Update saved config file
    _save_brand_config(brand)

    return _brand_to_response(brand)


@router.delete("/brands/{brand_id}")
async def delete_brand(brand_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a brand kit (cannot delete default)."""
    result = await db.execute(select(BrandKit).where(BrandKit.id == brand_id))
    brand = result.scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand kit not found")

    if brand.is_default:
        raise HTTPException(status_code=409, detail="Cannot delete the default brand kit")

    # Remove config file
    config_path = settings.BRANDS_DIR / f"{brand_id}.json"
    if config_path.exists():
        config_path.unlink()

    await db.delete(brand)
    await db.commit()

    return {"detail": "Brand kit deleted"}


def _save_brand_config(brand: BrandKit):
    """Save brand kit as a JSON config file for the pipeline to consume."""
    settings.ensure_dirs()
    colors = json.loads(brand.colors_json)
    fonts = json.loads(brand.fonts_json)

    config = {
        "name": brand.name,
        "colors": {
            "primary": colors.get("primary", "#01262D"),
            "secondary": colors.get("secondary", "#313131"),
            "accent": colors.get("accent", "#E84422"),
            "background": colors.get("background", "#F5F0E8"),
            "text_dark": colors.get("text_dark", "#313131"),
            "text_light": colors.get("text_light", "#FFFFFF"),
            "highlight": colors.get("highlight", "#E84422"),
        },
        "fonts": {
            "title": fonts.get("title", "Poppins"),
            "body": fonts.get("body", "Poppins"),
            "accent": fonts.get("accent", "Poppins Light"),
        },
    }

    config_path = settings.BRANDS_DIR / f"{brand.id}.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    logger.info("Saved brand config: %s", config_path)

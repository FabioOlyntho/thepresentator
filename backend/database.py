"""
Database — SQLAlchemy async engine and session management.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from backend.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """FastAPI dependency for database sessions."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create all tables and seed default data."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed default Recodme brand kit
    from backend.models import BrandKit
    async with async_session() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(BrandKit).where(BrandKit.is_default == True)
        )
        if not result.scalar_one_or_none():
            default_brand = BrandKit(
                name="Recodme",
                colors_json='{"primary":"#01262D","secondary":"#313131","accent":"#E84422","background":"#F5F0E8","text_dark":"#313131","text_light":"#FFFFFF","highlight":"#E84422"}',
                fonts_json='{"title":"Poppins","body":"Poppins","accent":"Poppins Light"}',
                logo_position="title_and_footer",
                is_default=True,
            )
            session.add(default_brand)
            await session.commit()

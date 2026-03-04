"""
Configuration — Settings for The Presentator backend.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).parent.parent
_env_path = _project_root / ".env"
if _env_path.exists():
    load_dotenv(str(_env_path))


class Settings:
    """Application settings loaded from environment variables."""

    # Gemini API
    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    # Database
    DATABASE_URL: str = os.environ.get(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{_project_root / 'data' / 'presentator.db'}",
    )

    # File storage
    UPLOAD_DIR: Path = _project_root / "data" / "uploads"
    OUTPUT_DIR: Path = _project_root / "data" / "output"
    BRANDS_DIR: Path = _project_root / "data" / "brands"

    # Server
    HOST: str = os.environ.get("HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("PORT", "8001"))

    # Limits
    MAX_UPLOAD_SIZE_MB: int = 50
    MAX_CONCURRENT_JOBS: int = 2

    # Brand config path (Recodme default)
    DEFAULT_BRAND_PATH: str = str(_project_root / "config" / "brand.json")

    # CORS origins
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:8081",
        "https://presentator.humanaie.com",
    ]

    def ensure_dirs(self):
        """Create required directories if they don't exist."""
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.BRANDS_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()

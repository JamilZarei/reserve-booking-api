import os
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/reserve_db"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    timezone: str = "Asia/Tehran"
    max_nights: int = 30
    uploads_dir: str = "uploads"
    max_upload_mb: int = 5
    cors_origins: str = "*"

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, v: str) -> str:
        # Hosted Postgres (Neon / Vercel) hands out postgres:// or postgresql:// URLs; SQLAlchemy needs the driver name
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v.removeprefix(prefix)
        return v


settings = Settings()
# Running as a Vercel Function: read-only filesystem, short-lived instances
ON_VERCEL = bool(os.environ.get("VERCEL"))
TZ = ZoneInfo(settings.timezone)


def today() -> date:
    return datetime.now(TZ).date()


def uploads_path() -> Path:
    """Folder for uploaded photos; a relative setting is resolved against the project root."""
    path = Path(settings.uploads_dir)
    return path if path.is_absolute() else Path(__file__).resolve().parent.parent / path

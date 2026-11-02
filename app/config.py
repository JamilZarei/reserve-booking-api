from datetime import date, datetime
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/reserve_db"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    timezone: str = "Asia/Tehran"
    max_nights: int = 30


settings = Settings()
TZ = ZoneInfo(settings.timezone)


def today() -> date:
    return datetime.now(TZ).date()

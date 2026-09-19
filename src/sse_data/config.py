from datetime import date
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mongodb_uri: str = "mongodb://127.0.0.1:27017"
    mongodb_db: str = "sse_market"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    history_start: date = date(2010, 1, 1)
    yahoo_batch_size: int = 15
    yahoo_pause_seconds: float = 2.0


@lru_cache
def get_settings() -> Settings:
    return Settings()

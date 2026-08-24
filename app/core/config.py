from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ETL Import Engine"
    environment: str = "development"
    debug: bool = False
    database_url: str = "postgresql+asyncpg://etl:etl@localhost:5432/etl"
    import_batch_size: int = Field(default=1000, ge=1, le=50_000)
    api_request_timeout_seconds: float = Field(default=10, gt=0, le=120)
    max_upload_size_mb: int = Field(default=50, ge=1, le=1000)
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

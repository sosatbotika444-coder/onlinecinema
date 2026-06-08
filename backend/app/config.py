from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SexParty API"
    environment: str = "development"
    api_public_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    session_secret: str = "change-me"
    auto_create_tables: bool = True

    database_url: str = "sqlite+aiosqlite:///./sexparty.db"
    redis_url: str | None = None

    max_upload_size_mb: int = 2048
    s3_endpoint_url: str | None = None
    s3_region: str = "us-east-1"
    s3_bucket: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_public_base_url: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def is_test(self) -> bool:
        return self.environment.lower() == "test"


@lru_cache
def get_settings() -> Settings:
    return Settings()

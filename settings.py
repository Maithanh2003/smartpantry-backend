from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        enable_decoding=False,
    )

    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_timezone: str = "UTC"
    db_timezone: str = "UTC"
    database_url: str
    redis_url: str
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    pantry_list_cache_enabled: bool = True
    pantry_list_cache_ttl_seconds: int = 120
    pantry_list_cache_key_prefix: str = "smartpantry:pantry-list"
    object_storage_provider: str = "s3"
    object_storage_endpoint_url: str | None = None
    object_storage_region: str = "auto"
    object_storage_bucket: str = "smartpantry-assets"
    object_storage_access_key_id: str = ""
    object_storage_secret_access_key: str = ""
    object_storage_public_base_url: str | None = None
    pantry_image_max_size_bytes: int = 5 * 1024 * 1024
    pantry_image_allowed_mime_types: list[str] = ["image/jpeg", "image/png", "image/webp"]
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    cors_origin_regex: str = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    @field_validator("pantry_image_allowed_mime_types", mode="before")
    @classmethod
    def parse_pantry_image_allowed_mime_types(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        return [item.strip() for item in value.split(",") if item.strip()]

    @field_validator("object_storage_endpoint_url", "object_storage_public_base_url", mode="before")
    @classmethod
    def optional_non_empty_str(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            return None
        stripped = value.strip()
        return stripped if stripped else None


@lru_cache
def get_settings() -> Settings:
    return Settings()

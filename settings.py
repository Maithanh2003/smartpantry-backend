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
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    cors_origin_regex: str = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        return [origin.strip() for origin in value.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

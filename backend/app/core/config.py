from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime config for the scan API. All values overridable via env vars."""

    model_config = SettingsConfigDict(env_prefix="SKILLSPECTOR_WEB_", env_file=".env")

    cors_origins: list[str] = ["http://localhost:3000"]
    allowed_target_schemes: tuple[str, ...] = ("http://", "https://")
    max_concurrent_scans: int = 2
    job_ttl_seconds: int = 3600
    admin_token: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()

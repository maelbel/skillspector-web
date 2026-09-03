from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime config for the scan API. All values overridable via env vars."""

    model_config = SettingsConfigDict(env_prefix="SKILLSPECTOR_WEB_", env_file=".env")

    cors_origins: list[str] = ["http://localhost:3000"]
    # Scans hit a public LangGraph pipeline that clones/downloads arbitrary
    # remote content — restricting targets to http(s) keeps the API from being
    # used to make the backend container read its own local filesystem.
    allowed_target_schemes: tuple[str, ...] = ("http://", "https://")
    max_concurrent_scans: int = 2
    # A scan the client never polls for stays in memory forever otherwise.
    job_ttl_seconds: int = 3600


@lru_cache
def get_settings() -> Settings:
    return Settings()

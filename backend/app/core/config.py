from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.mode import Mode


class Settings(BaseSettings):
    """Runtime config for the scan API. All values overridable via env vars."""

    # .env.local is what `pnpm setup` writes; it overrides .env when both exist.
    model_config = SettingsConfigDict(env_prefix="SKILLSPECTOR_WEB_", env_file=(".env", ".env.local"))

    # Which deployment this is; see app/core/mode.py.
    mode: Mode = Mode.SELF_HOSTED
    # How scans are run; unset picks the mode's default (in_process, or vercel_queues when hosted).
    job_runner: Literal["in_process", "vercel_queues"] | None = None
    cors_origins: list[str] = ["http://localhost:3000"]
    allowed_target_schemes: tuple[str, ...] = ("http://", "https://")
    max_concurrent_scans: int = 2
    max_queued_scans: int = 20
    # SQLite file used when database_url is unset.
    db_path: str = "data/scans.db"
    # A postgres:// URL switches scan storage to Postgres. Required in hosted mode.
    database_url: str | None = None
    admin_token: str | None = None
    scan_rate_limit: int = 5
    scan_rate_limit_window_seconds: float = 60.0
    scan_retention_days: float | None = None
    admin_rate_limit: int = 10
    admin_rate_limit_window_seconds: float = 300.0


@lru_cache
def get_settings() -> Settings:
    return Settings()

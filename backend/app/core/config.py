from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.mode import Mode


class Settings(BaseSettings):
    """Runtime config for the scan API. All values overridable via env vars."""

    # .env.local is what `pnpm setup` writes; it overrides .env when both exist.
    # extra="ignore": settings files written by older versions (e.g. ADMIN_TOKEN) still load.
    # env_ignore_empty: an empty `NAME=` line (as in .env.example) means "use the default".
    model_config = SettingsConfigDict(
        env_prefix="SKILLSPECTOR_WEB_",
        env_file=(".env", ".env.local"),
        extra="ignore",
        env_ignore_empty=True,
    )

    # Which deployment this is; see app/core/mode.py.
    mode: Mode = Mode.SELF_HOSTED
    # How scans are run; unset picks the mode's default (in_process, or vercel_queues when hosted).
    job_runner: Literal["in_process", "vercel_queues"] | None = None
    # Where live scan logs and progress go; unset picks the mode's default (memory, or database when hosted).
    log_store: Literal["memory", "database"] | None = None
    # Where rate limits count hits; unset picks the mode's default (memory, or database when hosted).
    rate_limit_store: Literal["memory", "database"] | None = None
    # Where a scan's fetch and analysis happen: local (this process) or sandbox (a Vercel Sandbox
    # microVM); unset picks the mode's default (local, or sandbox when hosted).
    scan_executor: Literal["local", "sandbox"] | None = None
    # The snapshot sandboxed scans boot from; build it with `python -m app.sandbox_snapshot`.
    sandbox_snapshot_id: str | None = None
    sandbox_vcpus: int = 2
    # Longest a sandboxed scan may run before it's stopped and reported as timed out.
    sandbox_timeout_seconds: float = 240.0
    cors_origins: list[str] = ["http://localhost:3000"]
    allowed_target_schemes: tuple[str, ...] = ("http://", "https://")
    max_concurrent_scans: int = 2
    max_queued_scans: int = 20
    # SQLite file used when database_url is unset.
    db_path: str = "data/scans.db"
    # A postgres:// URL switches scan storage to Postgres. Required in hosted mode.
    database_url: str | None = None
    # none: no sign-in, every visitor has full access (including /admin). accounts: sign-in
    # required, scans belong to their user, and admins manage the server. Unset picks the mode's
    # default (none, or accounts when hosted).
    auth: Literal["none", "accounts"] | None = None
    # Whether visitors may create their own account (with accounts on). Unset allows it; admins can
    # also change it from the backoffice, which overrides this.
    allow_signup: bool | None = None
    session_days: float = 30.0
    # Email (app/mail.py): password reset emails switch on when SMTP_HOST, MAIL_FROM and
    # PUBLIC_URL are all set.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    # starttls (port 587), ssl (port 465) or none (a local relay only).
    smtp_security: Literal["starttls", "ssl", "none"] = "starttls"
    mail_from: str | None = None
    # This app's public address, e.g. https://skillspector.example.com, for links in emails.
    public_url: str | None = None
    # Encrypts stored API keys at rest (app/secrets_box.py); generate with `python -m app.secrets_box`.
    # Without it users can't save a Claude key. Required in hosted mode.
    secret_key: str | None = None
    # Scans allowed per signed-in user (or, without accounts, per client IP) within the window.
    scan_rate_limit: int = 5
    scan_rate_limit_window_seconds: float = 60.0
    # Scans allowed per client IP within the same window, across every account signed in from it.
    scan_ip_rate_limit: int = 20
    # Quotas for signed-in users other than admins (app/quotas.py): scans per rolling 24 hours, and
    # scans pending or running at once. 0 means no limit. Unset picks the mode's default (no limits,
    # or 10 a day and 2 at once when hosted). Admins can change them from the backoffice, which
    # overrides these.
    daily_scan_quota: int | None = Field(default=None, ge=0)
    concurrent_scan_quota: int | None = Field(default=None, ge=0)
    scan_retention_days: float | None = None
    # Vercel's own variable, without our prefix: Vercel Cron sends it as a bearer token, and
    # POST /internal/retention runs the sweep only for callers presenting it. Required in hosted mode.
    cron_secret: str | None = Field(default=None, validation_alias="CRON_SECRET")
    # Sign-in, first-run setup and sign-up attempts allowed per client IP within the window.
    login_rate_limit: int = 10
    login_rate_limit_window_seconds: float = 300.0
    # Following a skill's external references (skillspector's --transitive): the deepest a scan may
    # ask for, 0 to turn the option off; and URL prefixes to only follow, or never follow.
    transitive_max_depth: int = Field(default=2, ge=0, le=5)
    transitive_allow_prefixes: list[str] = []
    transitive_deny_prefixes: list[str] = []

    @model_validator(mode="after")
    def _canonical_transitive_prefixes(self) -> "Settings":
        """Stored as skillspector compares them; an invalid prefix refuses to start, not each scan."""
        from skillspector import transitive

        try:
            allow, deny = transitive.normalize_prefixes(self.transitive_allow_prefixes, self.transitive_deny_prefixes)
        except ValueError as exc:
            raise ValueError(f"invalid transitive prefix: {exc}") from exc
        self.transitive_allow_prefixes, self.transitive_deny_prefixes = list(allow), list(deny)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

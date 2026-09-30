from __future__ import annotations

import os

import pytest

from app.core.config import Settings, get_settings

# Tests never read the developer's .env / .env.local: those can hold real SMTP or API credentials,
# and a test must never send a real email or call a real provider with them.
Settings.model_config["env_file"] = ()
get_settings.cache_clear()

# Imported only now, so nothing has cached settings read from the real files.
from app import db

# Point this at a throwaway Postgres database to run every storage test on both engines.
# Its tables are dropped before each test.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


def _reset_postgres(url: str) -> None:
    import psycopg

    with psycopg.connect(url, autocommit=True) as conn:
        # Every table, including ones added by later migrations, without listing them here.
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")


@pytest.fixture(
    params=[
        "sqlite",
        pytest.param(
            "postgres",
            marks=pytest.mark.skipif(not TEST_DATABASE_URL, reason="set TEST_DATABASE_URL to test Postgres"),
        ),
    ]
)
def temp_db(request, tmp_path, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "scan_retention_days", None)
    if request.param == "postgres":
        _reset_postgres(TEST_DATABASE_URL)
        monkeypatch.setattr(settings, "database_url", TEST_DATABASE_URL)
    else:
        monkeypatch.setattr(settings, "database_url", None)
        monkeypatch.setattr(settings, "db_path", str(tmp_path / "test.db"))
    db.init_db()
    yield request.param
    db.close_db()


class FakeRunner:
    """A job runner that records submitted scans instead of running them."""

    def __init__(self) -> None:
        self.submitted = []
        self.full = False
        self.rejection: str | None = None

    def on_startup(self) -> None:
        return None

    def is_full(self) -> bool:
        return self.full

    def check(self, llm) -> None:
        if self.rejection:
            from app.jobs import JobRejectedError

            raise JobRejectedError(self.rejection)

    async def submit(self, job) -> None:
        self.submitted.append(job)


@pytest.fixture
def fake_runner(monkeypatch):
    from app.api.routes import scan as scan_routes

    runner = FakeRunner()
    monkeypatch.setattr(scan_routes, "get_runner", lambda: runner)
    return runner


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    """Every test starts with no hits counted, and the limiter re-reads the settings."""
    from app import rate_limit

    rate_limit.reset()
    yield
    rate_limit.reset()

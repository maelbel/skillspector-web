from __future__ import annotations

import os

import pytest

from app import db
from app.core.config import get_settings

# Point this at a throwaway Postgres database to run every storage test on both engines.
# Its tables are dropped before each test.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


def _reset_postgres(url: str) -> None:
    import psycopg

    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS scans, app_settings, schema_migrations, scan_log_lines, users, sessions, password_resets, audit_log")


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

from __future__ import annotations

import pytest

from app import db
from app.core.config import get_settings


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "test.db"))
    monkeypatch.setattr(settings, "scan_retention_days", None)
    db.init_db()
    yield
    db._connection.close()
    db._connection = None

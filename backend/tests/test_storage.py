from __future__ import annotations

import sqlite3

import pytest

from app import db
from app.core.config import Settings
from app.storage import create_store, is_postgres_url
from app.storage.sqlite import MIGRATIONS, SQLiteStore


def test_result_round_trips_as_a_dict(temp_db):
    report = {"risk_assessment": {"score": 42, "severity": "HIGH", "recommendation": "CAUTION"}, "issues": []}
    db.insert_scan(id="a", target="t", status="pending", created_at=1.0, provider="anthropic")

    db.update_scan(id="a", status="done", finished_at=2.0, result=report, error=None)

    scan = db.get_scan("a")
    assert scan["result"] == report
    assert scan["provider"] == "anthropic"
    assert (scan["risk_score"], scan["severity"], scan["recommendation"]) == (42, "HIGH", "CAUTION")


def test_list_scans_is_newest_first_with_a_total_and_no_report(temp_db):
    for index in range(3):
        db.insert_scan(id=f"s{index}", target="t", status="done", created_at=float(index), provider=None)

    rows, total = db.list_scans(limit=2, offset=0)

    assert total == 3
    assert [row["id"] for row in rows] == ["s2", "s1"]
    assert "result" not in rows[0]


def test_migrations_are_recorded_and_not_rerun(temp_db):
    db.init_db()  # A second startup against the same database.

    db.insert_scan(id="a", target="t", status="done", created_at=1.0, provider=None)
    assert db.get_scan("a") is not None


def test_a_database_from_before_migrations_is_adopted(tmp_path):
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.execute(MIGRATIONS[0][1][0])  # The scans table, as older versions created it.
    conn.execute("INSERT INTO scans (id, target, status, created_at) VALUES ('kept', 't', 'done', 1.0)")
    conn.commit()
    conn.close()

    store = SQLiteStore(str(path), default_retention_days=None)

    assert store.get_scan("kept")["status"] == "done"
    assert store.get_retention_days() is None
    store.close()


@pytest.mark.parametrize(
    ("url", "expected"),
    [("postgres://u@h/db", True), ("postgresql://u@h/db", True), ("sqlite:///x.db", False), ("mysql://h/db", False)],
)
def test_is_postgres_url(url, expected):
    assert is_postgres_url(url) is expected


def test_create_store_rejects_non_postgres_urls(tmp_path):
    settings = Settings(_env_file=None, database_url="mysql://host/db", db_path=str(tmp_path / "x.db"))

    with pytest.raises(ValueError, match="postgres"):
        create_store(settings)


def test_create_store_defaults_to_sqlite(tmp_path):
    store = create_store(Settings(_env_file=None, db_path=str(tmp_path / "x.db")))

    assert isinstance(store, SQLiteStore)
    store.close()

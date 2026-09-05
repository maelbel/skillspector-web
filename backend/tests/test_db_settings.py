from __future__ import annotations

from app import db


def test_retention_days_defaults_to_seeded_env_value(temp_db):
    assert db.get_retention_days() is None


def test_set_and_get_retention_days(temp_db):
    db.set_retention_days(30)
    assert db.get_retention_days() == 30


def test_set_retention_days_back_to_none(temp_db):
    db.set_retention_days(14)
    db.set_retention_days(None)
    assert db.get_retention_days() is None


def test_delete_scans_older_than_only_removes_matching_rows(temp_db):
    db.insert_scan(id="old", target="t1", status="done", created_at=1000.0, provider=None)
    db.insert_scan(id="new", target="t2", status="done", created_at=2000.0, provider=None)

    deleted = db.delete_scans_older_than(1500.0)

    assert deleted == 1
    assert db.get_scan("old") is None
    assert db.get_scan("new") is not None


def test_delete_scans_older_than_returns_zero_when_nothing_matches(temp_db):
    db.insert_scan(id="new", target="t", status="done", created_at=2000.0, provider=None)
    assert db.delete_scans_older_than(1000.0) == 0

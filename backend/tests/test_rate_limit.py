from __future__ import annotations

import pytest

from app import rate_limit


@pytest.fixture(autouse=True)
def _reset_state():
    rate_limit._hits.clear()
    yield
    rate_limit._hits.clear()


def _fake_clock(monkeypatch, start: float = 1000.0):
    now = {"t": start}
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: now["t"])
    return now


def test_allows_up_to_the_limit(monkeypatch):
    _fake_clock(monkeypatch)
    for _ in range(5):
        assert rate_limit.check("client-a", limit=5, window_seconds=60) is True


def test_rejects_once_over_the_limit(monkeypatch):
    _fake_clock(monkeypatch)
    for _ in range(5):
        rate_limit.check("client-a", limit=5, window_seconds=60)
    assert rate_limit.check("client-a", limit=5, window_seconds=60) is False


def test_different_keys_are_isolated(monkeypatch):
    _fake_clock(monkeypatch)
    for _ in range(5):
        rate_limit.check("client-a", limit=5, window_seconds=60)
    assert rate_limit.check("client-b", limit=5, window_seconds=60) is True


def test_hits_expire_after_the_window(monkeypatch):
    now = _fake_clock(monkeypatch)
    for _ in range(5):
        rate_limit.check("client-a", limit=5, window_seconds=60)
    assert rate_limit.check("client-a", limit=5, window_seconds=60) is False

    now["t"] += 61
    assert rate_limit.check("client-a", limit=5, window_seconds=60) is True


def test_evicts_oldest_client_past_the_tracked_cap(monkeypatch):
    _fake_clock(monkeypatch)
    for i in range(rate_limit._MAX_TRACKED_CLIENTS):
        rate_limit.check(f"client-{i}", limit=5, window_seconds=60)
    rate_limit.check("client-overflow", limit=5, window_seconds=60)

    assert "client-0" not in rate_limit._hits
    assert "client-overflow" in rate_limit._hits

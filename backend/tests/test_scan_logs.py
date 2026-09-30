from __future__ import annotations

import contextvars
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from app import db, scan_logs
from app.core.config import Settings, get_settings
from app.core.mode import Mode
from app.scan_logs import DatabaseLogStore, MemoryLogStore, log_store_kind

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


@pytest.fixture(
    params=[
        "memory",
        "sqlite",
        pytest.param(
            "postgres",
            marks=pytest.mark.skipif(not TEST_DATABASE_URL, reason="set TEST_DATABASE_URL to test Postgres"),
        ),
    ]
)
def store(request, tmp_path, monkeypatch):
    """Every test below runs against the memory store and the database store on each engine."""
    if request.param == "memory":
        log_store = MemoryLogStore()
    else:
        settings = get_settings()
        monkeypatch.setattr(settings, "scan_retention_days", None)
        if request.param == "postgres":
            import psycopg

            with psycopg.connect(TEST_DATABASE_URL, autocommit=True) as conn:
                conn.execute("DROP TABLE IF EXISTS scans, app_settings, schema_migrations, scan_log_lines, users, sessions, password_resets, audit_log")
            monkeypatch.setattr(settings, "database_url", TEST_DATABASE_URL)
        else:
            monkeypatch.setattr(settings, "database_url", None)
            monkeypatch.setattr(settings, "db_path", str(tmp_path / "test.db"))
        db.init_db()
        log_store = DatabaseLogStore()
    monkeypatch.setattr(scan_logs, "_store", log_store)
    yield log_store
    if request.param != "memory":
        db.close_db()


@pytest.fixture
def memory_store(monkeypatch):
    log_store = MemoryLogStore()
    monkeypatch.setattr(scan_logs, "_store", log_store)
    return log_store


def _scans(store, *ids: str) -> None:
    """Progress lives on the scan row in the database store, so those scans must exist."""
    if isinstance(store, DatabaseLogStore):
        for id in ids:
            db.insert_scan(id=id, target="t", status="running", created_at=1.0, provider=None)


def _make_record(message: str) -> logging.LogRecord:
    return logging.getLogger("skillspector.test").makeRecord(
        "skillspector.test", logging.INFO, __file__, 0, message, (), None
    )


def test_append_and_get_logs(store):
    scan_logs.append("job-1", "hello")
    scan_logs.append("job-1", "world")
    assert scan_logs.get_logs("job-1") == ["hello", "world"]


def test_get_logs_unknown_job_returns_empty(store):
    assert scan_logs.get_logs("does-not-exist") == []


def test_logs_for_different_jobs_stay_separate(store):
    scan_logs.append("job-a", "a1")
    scan_logs.append("job-b", "b1")
    scan_logs.append("job-a", "a2")
    assert scan_logs.get_logs("job-a") == ["a1", "a2"]
    assert scan_logs.get_logs("job-b") == ["b1"]


def test_progress_increments_and_is_scoped_per_job(store):
    _scans(store, "job-a", "job-b")
    scan_logs.increment_progress("job-a")
    scan_logs.increment_progress("job-a")
    scan_logs.increment_progress("job-b")
    assert scan_logs.get_progress("job-a") == 2
    assert scan_logs.get_progress("job-b") == 1


def test_progress_for_unknown_job_is_zero(store):
    assert scan_logs.get_progress("does-not-exist") == 0


def test_log_buffer_caps_lines_per_scan(store):
    total = scan_logs._MAX_LINES_PER_SCAN + 50
    for i in range(total):
        scan_logs.append("job-a", f"line-{i}")
    lines = scan_logs.get_logs("job-a")
    assert len(lines) == scan_logs._MAX_LINES_PER_SCAN
    assert lines[-1] == f"line-{total - 1}"
    assert lines[0] == f"line-{total - scan_logs._MAX_LINES_PER_SCAN}"


def test_oldest_scan_evicted_past_tracked_cap(memory_store):
    for i in range(scan_logs._MAX_TRACKED_SCANS):
        scan_logs.append(f"job-{i}", "line")
    # All 50 tracked slots are full; one more distinct job should evict the oldest (job-0).
    scan_logs.append("job-overflow", "line")
    assert scan_logs.get_logs("job-0") == []
    assert scan_logs.get_logs("job-overflow") == ["line"]


def test_evicting_a_scan_also_drops_its_progress(memory_store):
    for i in range(scan_logs._MAX_TRACKED_SCANS):
        scan_logs.increment_progress(f"job-{i}")
    scan_logs.increment_progress("job-overflow")
    assert scan_logs.get_progress("job-0") == 0


def test_touching_a_job_moves_it_to_the_front_of_eviction_order(memory_store):
    for i in range(scan_logs._MAX_TRACKED_SCANS):
        scan_logs.append(f"job-{i}", "line")
    # Re-touch job-0 so it's no longer the least-recently-used entry.
    scan_logs.append("job-0", "line-again")
    scan_logs.append("job-overflow", "line")
    # job-1 (not job-0) should now be the one evicted.
    assert scan_logs.get_logs("job-0") == ["line", "line-again"]
    assert scan_logs.get_logs("job-1") == []


def test_capture_scopes_log_handler_records_to_the_current_thread(store):
    scan_logs.start_capture("job-a")
    try:
        scan_logs._JobLogHandler().emit(_make_record("hello"))
    finally:
        scan_logs.stop_capture()
    assert scan_logs.get_logs("job-a") == ["hello"]


def test_capture_follows_context_into_worker_threads(store):
    # LangGraph runs parallel nodes on a thread pool with a copy of the caller's context.
    scan_logs.start_capture("job-a")
    try:
        context = contextvars.copy_context()
        with ThreadPoolExecutor(max_workers=2) as pool:
            pool.submit(context.run, scan_logs._JobLogHandler().emit, _make_record("from worker")).result()
    finally:
        scan_logs.stop_capture()
    assert scan_logs.get_logs("job-a") == ["from worker"]


def test_concurrent_captures_stay_isolated_per_thread(store):
    barrier = threading.Barrier(2)

    def scan(job_id: str) -> None:
        scan_logs.start_capture(job_id)
        barrier.wait()
        try:
            scan_logs._JobLogHandler().emit(_make_record(job_id))
        finally:
            scan_logs.stop_capture()

    threads = [threading.Thread(target=scan, args=(job_id,)) for job_id in ("job-a", "job-b")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert scan_logs.get_logs("job-a") == ["job-a"]
    assert scan_logs.get_logs("job-b") == ["job-b"]


def test_uncaptured_thread_drops_log_records(store):
    scan_logs._JobLogHandler().emit(_make_record("uncaptured"))
    assert scan_logs.get_logs("job-a") == []


def test_concurrent_appends_stay_isolated_per_job(store):
    def worker(job_id: str, count: int) -> None:
        for i in range(count):
            scan_logs.append(job_id, f"{job_id}-{i}")
            scan_logs.increment_progress(job_id)

    job_ids = [f"concurrent-job-{i}" for i in range(20)]
    _scans(store, *job_ids)
    threads = [threading.Thread(target=worker, args=(job_id, 100)) for job_id in job_ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    for job_id in job_ids:
        lines = scan_logs.get_logs(job_id)
        assert len(lines) == 100
        assert all(line.startswith(job_id) for line in lines)
        assert scan_logs.get_progress(job_id) == 100


def test_forget_clears_lines_and_progress(store):
    _scans(store, "job-a")
    scan_logs.append("job-a", "line")
    scan_logs.increment_progress("job-a")

    scan_logs.forget("job-a")

    assert scan_logs.get_logs("job-a") == []
    assert scan_logs.get_progress("job-a") == 0


def test_a_failing_store_never_breaks_the_scan(memory_store, monkeypatch):
    def broken(job_id, message):
        raise ConnectionError("database unreachable")

    monkeypatch.setattr(memory_store, "append", broken)
    monkeypatch.setattr(logging, "raiseExceptions", False)
    scan_logs.start_capture("job-a")
    try:
        scan_logs._JobLogHandler().emit(_make_record("hello"))  # Must not raise.
    finally:
        scan_logs.stop_capture()


@pytest.mark.parametrize(
    ("mode", "override", "expected"),
    [
        (Mode.SELF_HOSTED, None, "memory"),
        (Mode.HOSTED, None, "database"),
        (Mode.SELF_HOSTED, "database", "database"),
    ],
)
def test_log_store_follows_the_mode_unless_overridden(mode, override, expected):
    assert log_store_kind(Settings(_env_file=None, mode=mode, log_store=override)) == expected

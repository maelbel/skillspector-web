from __future__ import annotations

import logging
import threading

import pytest

from app import scan_logs


@pytest.fixture(autouse=True)
def _reset_state():
    scan_logs._buffers.clear()
    scan_logs._progress.clear()
    yield
    scan_logs._buffers.clear()
    scan_logs._progress.clear()


def _make_record(message: str) -> logging.LogRecord:
    return logging.getLogger("skillspector.test").makeRecord(
        "skillspector.test", logging.INFO, __file__, 0, message, (), None
    )


def test_append_and_get_logs():
    scan_logs.append("job-1", "hello")
    scan_logs.append("job-1", "world")
    assert scan_logs.get_logs("job-1") == ["hello", "world"]


def test_get_logs_unknown_job_returns_empty():
    assert scan_logs.get_logs("does-not-exist") == []


def test_logs_for_different_jobs_stay_separate():
    scan_logs.append("job-a", "a1")
    scan_logs.append("job-b", "b1")
    scan_logs.append("job-a", "a2")
    assert scan_logs.get_logs("job-a") == ["a1", "a2"]
    assert scan_logs.get_logs("job-b") == ["b1"]


def test_progress_increments_and_is_scoped_per_job():
    scan_logs.increment_progress("job-a")
    scan_logs.increment_progress("job-a")
    scan_logs.increment_progress("job-b")
    assert scan_logs.get_progress("job-a") == 2
    assert scan_logs.get_progress("job-b") == 1


def test_progress_for_unknown_job_is_zero():
    assert scan_logs.get_progress("does-not-exist") == 0


def test_log_buffer_caps_lines_per_scan():
    total = scan_logs._MAX_LINES_PER_SCAN + 50
    for i in range(total):
        scan_logs.append("job-a", f"line-{i}")
    lines = scan_logs.get_logs("job-a")
    assert len(lines) == scan_logs._MAX_LINES_PER_SCAN
    assert lines[-1] == f"line-{total - 1}"
    assert lines[0] == f"line-{total - scan_logs._MAX_LINES_PER_SCAN}"


def test_oldest_scan_evicted_past_tracked_cap():
    for i in range(scan_logs._MAX_TRACKED_SCANS):
        scan_logs.append(f"job-{i}", "line")
    # All 50 tracked slots are full; one more distinct job should evict the oldest (job-0).
    scan_logs.append("job-overflow", "line")
    assert scan_logs.get_logs("job-0") == []
    assert scan_logs.get_logs("job-overflow") == ["line"]


def test_evicting_a_scan_also_drops_its_progress():
    for i in range(scan_logs._MAX_TRACKED_SCANS):
        scan_logs.increment_progress(f"job-{i}")
    scan_logs.increment_progress("job-overflow")
    assert scan_logs.get_progress("job-0") == 0


def test_touching_a_job_moves_it_to_the_front_of_eviction_order():
    for i in range(scan_logs._MAX_TRACKED_SCANS):
        scan_logs.append(f"job-{i}", "line")
    # Re-touch job-0 so it's no longer the least-recently-used entry.
    scan_logs.append("job-0", "line-again")
    scan_logs.append("job-overflow", "line")
    # job-1 (not job-0) should now be the one evicted.
    assert scan_logs.get_logs("job-0") == ["line", "line-again"]
    assert scan_logs.get_logs("job-1") == []


def test_capture_scopes_log_handler_records_to_the_current_thread():
    scan_logs.start_capture("job-a")
    try:
        scan_logs._JobLogHandler().emit(_make_record("hello"))
    finally:
        scan_logs.stop_capture()
    assert scan_logs.get_logs("job-a") == ["hello"]


def test_uncaptured_thread_drops_log_records():
    scan_logs._JobLogHandler().emit(_make_record("uncaptured"))
    assert scan_logs.get_logs("job-a") == []


def test_concurrent_appends_stay_isolated_per_job():
    def worker(job_id: str, count: int) -> None:
        for i in range(count):
            scan_logs.append(job_id, f"{job_id}-{i}")
            scan_logs.increment_progress(job_id)

    job_ids = [f"concurrent-job-{i}" for i in range(20)]
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

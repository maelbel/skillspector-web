from __future__ import annotations

import sys

import pytest

from app import sandbox_snapshot
from app.core.config import Settings

REQUIREMENT = "skillspector @ git+https://github.com/NVIDIA/skillspector.git@abc123"


@pytest.fixture
def record(tmp_path, monkeypatch):
    path = tmp_path / "sandbox_snapshot_record.py"
    monkeypatch.setattr(sandbox_snapshot, "RECORD", path)
    monkeypatch.setattr(sandbox_snapshot, "skillspector_requirement", lambda: REQUIREMENT)
    return path


def _run_main(monkeypatch, *args: str) -> None:
    monkeypatch.setattr(sys, "argv", ["sandbox_snapshot", *args])
    sandbox_snapshot.main()


def test_the_committed_record_is_valid_python():
    record = sandbox_snapshot.recorded_snapshot()
    assert record["skillspector"].startswith("skillspector @ git+https://github.com/NVIDIA/skillspector.git@")
    assert record["snapshot_id"].startswith("snap_")
    compile(sandbox_snapshot.RECORD.read_text(), "record", "exec")


def test_a_record_round_trips(record):
    sandbox_snapshot.write_record(REQUIREMENT, "snap_new")

    assert sandbox_snapshot.recorded_snapshot() == {"skillspector": REQUIREMENT, "snapshot_id": "snap_new"}
    assert not sandbox_snapshot.is_stale()


def test_a_record_for_another_pin_is_stale(record):
    sandbox_snapshot.write_record("skillspector @ git+https://github.com/NVIDIA/skillspector.git@old", "snap_old")
    assert sandbox_snapshot.is_stale()


def test_no_record_is_stale(record):
    assert sandbox_snapshot.is_stale()


def test_the_record_wins_over_the_setting(record):
    settings = Settings(_env_file=None, sandbox_snapshot_id="snap_env")
    assert sandbox_snapshot.snapshot_id_for(settings) == "snap_env"

    sandbox_snapshot.write_record(REQUIREMENT, "snap_recorded")
    assert sandbox_snapshot.snapshot_id_for(settings) == "snap_recorded"


def test_a_build_records_the_new_snapshot(record, monkeypatch, capsys):
    async def build():
        return "snap_built"

    monkeypatch.setattr(sandbox_snapshot, "build", build)
    _run_main(monkeypatch)

    assert sandbox_snapshot.recorded_snapshot() == {"skillspector": REQUIREMENT, "snapshot_id": "snap_built"}
    assert capsys.readouterr().out.strip() == "snap_built"


def test_if_stale_skips_the_build_for_an_up_to_date_record(record, monkeypatch):
    sandbox_snapshot.write_record(REQUIREMENT, "snap_current")

    async def build():
        raise AssertionError("shouldn't build")

    monkeypatch.setattr(sandbox_snapshot, "build", build)
    _run_main(monkeypatch, "--if-stale")

    assert sandbox_snapshot.recorded_snapshot()["snapshot_id"] == "snap_current"


def test_a_failed_build_leaves_the_record_alone(record, monkeypatch):
    sandbox_snapshot.write_record("skillspector @ git+https://github.com/NVIDIA/skillspector.git@old", "snap_old")

    async def build():
        raise RuntimeError("pip install failed")

    monkeypatch.setattr(sandbox_snapshot, "build", build)
    with pytest.raises(RuntimeError):
        _run_main(monkeypatch, "--if-stale")

    assert sandbox_snapshot.recorded_snapshot()["snapshot_id"] == "snap_old"

"""Build the Vercel Sandbox snapshot hosted scans boot from.

    uv run python -m app.sandbox_snapshot [--if-stale]

Installs the exact skillspector version pinned in pyproject.toml into a fresh sandbox, checks it
imports, snapshots the filesystem, and records the snapshot ID next to the pin it was built from
in sandbox_snapshot_record.py. Every deployment boots scans from the snapshot recorded in its own code,
so it always matches its pin, rollbacks included. The Sandbox snapshot workflow runs this with
--if-stale whenever a pull request changes the pin, and commits the record. Needs Vercel
credentials (VERCEL_OIDC_TOKEN from `vercel env pull`, or VERCEL_TOKEN, VERCEL_TEAM_ID and
VERCEL_PROJECT_ID).

Installing needs PyPI and GitHub, so the build sandbox keeps the default open network. Scans
themselves boot from the snapshot with the restricted policy in app.sandbox_executor.
"""

from __future__ import annotations

import argparse
import ast
import asyncio
import json
import sys
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config import Settings

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"
# A Python module rather than data, so the hosted API's bundle always includes it.
RECORD = Path(__file__).with_name("sandbox_snapshot_record.py")


def skillspector_requirement() -> str:
    dependencies = tomllib.loads(PYPROJECT.read_text())["project"]["dependencies"]
    return next(dep for dep in dependencies if dep.replace(" ", "").startswith("skillspector@"))


def recorded_snapshot() -> dict[str, str] | None:
    """The last snapshot built, and the skillspector requirement it was built from."""
    try:
        source = RECORD.read_text()
    except FileNotFoundError:
        return None
    return {
        node.targets[0].id.lower(): ast.literal_eval(node.value)
        for node in ast.parse(source).body
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
    }


def write_record(requirement: str, snapshot_id: str) -> None:
    RECORD.write_text(
        "# Written by `python -m app.sandbox_snapshot`: the snapshot scans boot from, and the\n"
        "# skillspector requirement it was built from. Don't edit by hand.\n"
        # json.dumps: a double-quoted Python string literal, as ruff formats them.
        f"SKILLSPECTOR = {json.dumps(requirement)}\n"
        f"SNAPSHOT_ID = {json.dumps(snapshot_id)}\n"
    )


def is_stale() -> bool:
    record = recorded_snapshot()
    return record is None or record.get("skillspector") != skillspector_requirement()


def snapshot_id_for(settings: Settings) -> str | None:
    """The recorded snapshot; SKILLSPECTOR_WEB_SANDBOX_SNAPSHOT_ID when there's none."""
    record = recorded_snapshot()
    return (record or {}).get("snapshot_id") or settings.sandbox_snapshot_id


async def build() -> str:
    from vercel.sandbox import create_sandbox

    requirement = skillspector_requirement()
    print(f"Installing {requirement}", file=sys.stderr)
    # destroy=False: the SDK's cleanup would delete the snapshot along with this sandbox, its only
    # user. The sandbox is destroyed once the snapshot exists, keeping the snapshot.
    async with create_sandbox(execution_time_limit=15 * 60, persistent=False, destroy=False) as box:
        # Some dependencies (yara-python) have no wheel for the image's Python and build from source.
        await box.run_process(
            "sh",
            ["-c", "apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq gcc python3-dev"],
            sudo=True,
            stdout=sys.stderr,
            stderr=sys.stderr,
            check=True,
        )
        await box.run_process(
            "python3",
            ["-m", "pip", "install", "--user", "--break-system-packages", requirement],
            stdout=sys.stderr,
            stderr=sys.stderr,
            check=True,
        )
        check = await box.run_process(
            "python3",
            ["-c", "import skillspector, skillspector.graph; print(skillspector.__version__)"],
            capture_output=True,
            check=True,
        )
        print(f"skillspector {check.stdout.strip()} installed", file=sys.stderr)
        snapshot = await box.snapshot(expiration=0)  # Kept until rebuilt; scans depend on it.
    await box.destroy()
    return snapshot.id


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.sandbox_snapshot", description=__doc__.splitlines()[0])
    parser.add_argument("--if-stale", action="store_true", help="only build when the recorded snapshot isn't for the current pin")
    args = parser.parse_args()
    if args.if_stale and not is_stale():
        print(f"{RECORD.name} is up to date for {skillspector_requirement()}", file=sys.stderr)
        return
    requirement = skillspector_requirement()
    snapshot_id = asyncio.run(build())
    # Written only once the snapshot exists: a failed build leaves the record as it was.
    write_record(requirement, snapshot_id)
    print(snapshot_id)


if __name__ == "__main__":
    main()

"""Build the Vercel Sandbox snapshot hosted scans boot from.

    uv run python -m app.sandbox_snapshot

Installs the exact skillspector version pinned in pyproject.toml into a fresh sandbox, checks it
imports, snapshots the filesystem, and prints the snapshot ID to set as
SKILLSPECTOR_WEB_SANDBOX_SNAPSHOT_ID. Rebuild it whenever the skillspector pin changes; scans log a
warning when the versions differ. Needs Vercel credentials (VERCEL_OIDC_TOKEN from `vercel env
pull`, or VERCEL_TOKEN, VERCEL_TEAM_ID and VERCEL_PROJECT_ID).

Installing needs PyPI and GitHub, so the build sandbox keeps the default open network. Scans
themselves boot from the snapshot with the restricted policy in app.sandbox_executor.
"""

from __future__ import annotations

import asyncio
import sys
import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def skillspector_requirement() -> str:
    dependencies = tomllib.loads(PYPROJECT.read_text())["project"]["dependencies"]
    return next(dep for dep in dependencies if dep.replace(" ", "").startswith("skillspector@"))


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
    print(asyncio.run(build()))


if __name__ == "__main__":
    main()
